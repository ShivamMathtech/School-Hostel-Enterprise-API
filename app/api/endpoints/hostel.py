from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import (
    AllocationStatus,
    BedStatus,
    Gender,
    HostelAllocation,
    HostelBed,
    HostelBuilding,
    HostelRoom,
    Student,
    User,
    UserRole,
)
from app.schemas.api import (
    AllocationCreate,
    AllocationRead,
    BedRead,
    BuildingCreate,
    BuildingRead,
    CheckoutRequest,
    RoomCreate,
    RoomRead,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/hostel", tags=["Hostel Management"])
manage_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.WARDEN)
read_roles = manage_roles + (UserRole.ACCOUNTANT, UserRole.GUARD, UserRole.MESS_MANAGER)


@router.post("/buildings", response_model=BuildingRead, status_code=201)
def create_building(
    payload: BuildingCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    building = HostelBuilding(**payload.model_dump())
    db.add(building)
    try:
        db.flush()
        write_audit(db, actor.id, "hostel_building.created", "hostel_building", building.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Building name already exists")
    db.refresh(building)
    return building


@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    return list(db.scalars(select(HostelBuilding).order_by(HostelBuilding.name)))


@router.post("/rooms", response_model=RoomRead, status_code=201)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    if not db.get(HostelBuilding, payload.building_id):
        raise HTTPException(status_code=404, detail="Building not found")
    room = HostelRoom(**payload.model_dump())
    db.add(room)
    try:
        db.flush()
        for index in range(1, payload.capacity + 1):
            db.add(HostelBed(room_id=room.id, bed_no=f"B{index:02d}", status=BedStatus.AVAILABLE))
        write_audit(db, actor.id, "hostel_room.created", "hostel_room", room.id, {"capacity": room.capacity})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Room already exists in this building")
    db.refresh(room)
    return room


@router.get("/rooms", response_model=list[RoomRead])
def list_rooms(
    building_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(HostelRoom)
    if building_id:
        stmt = stmt.where(HostelRoom.building_id == building_id)
    return list(db.scalars(stmt.order_by(HostelRoom.building_id, HostelRoom.room_no)))


@router.get("/beds", response_model=list[BedRead])
def list_beds(
    room_id: int | None = None,
    status: BedStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(HostelBed)
    if room_id:
        stmt = stmt.where(HostelBed.room_id == room_id)
    if status:
        stmt = stmt.where(HostelBed.status == status)
    return list(db.scalars(stmt.order_by(HostelBed.room_id, HostelBed.bed_no)))


@router.post("/allocations", response_model=AllocationRead, status_code=201)
def allocate_bed(
    payload: AllocationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    student = db.get(Student, payload.student_id)
    bed = db.get(HostelBed, payload.bed_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    if bed.status != BedStatus.AVAILABLE:
        raise HTTPException(status_code=409, detail="Bed is not available")
    existing = db.scalar(
        select(HostelAllocation).where(
            HostelAllocation.student_id == student.id,
            HostelAllocation.status == AllocationStatus.ACTIVE,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Student already has an active hostel allocation")
    building = bed.room.building
    if building.gender_type != Gender.OTHER and building.gender_type != student.gender:
        raise HTTPException(status_code=422, detail="Student gender does not match hostel building policy")
    allocation = HostelAllocation(**payload.model_dump(), status=AllocationStatus.ACTIVE, allocated_by=actor.id)
    bed.status = BedStatus.OCCUPIED
    db.add(allocation)
    db.flush()
    write_audit(db, actor.id, "hostel_bed.allocated", "hostel_allocation", allocation.id, {"student_id": student.id, "bed_id": bed.id})
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get("/allocations", response_model=list[AllocationRead])
def list_allocations(
    student_id: int | None = None,
    status: AllocationStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(HostelAllocation)
    if student_id:
        stmt = stmt.where(HostelAllocation.student_id == student_id)
    if status:
        stmt = stmt.where(HostelAllocation.status == status)
    return list(db.scalars(stmt.order_by(HostelAllocation.id.desc())))


@router.post("/allocations/{allocation_id}/checkout", response_model=AllocationRead)
def checkout_student(
    allocation_id: int,
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    allocation = db.get(HostelAllocation, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if allocation.status != AllocationStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Allocation is not active")
    if payload.end_date < allocation.start_date:
        raise HTTPException(status_code=422, detail="Checkout date cannot precede start date")
    allocation.status = AllocationStatus.COMPLETED
    allocation.end_date = payload.end_date
    allocation.checkout_notes = payload.checkout_notes
    allocation.bed.status = BedStatus.AVAILABLE
    write_audit(db, actor.id, "hostel_bed.checked_out", "hostel_allocation", allocation.id)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get("/occupancy")
def occupancy_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    total = db.scalar(select(func.count(HostelBed.id))) or 0
    occupied = db.scalar(select(func.count(HostelBed.id)).where(HostelBed.status == BedStatus.OCCUPIED)) or 0
    available = db.scalar(select(func.count(HostelBed.id)).where(HostelBed.status == BedStatus.AVAILABLE)) or 0
    return {
        "total_beds": total,
        "occupied_beds": occupied,
        "available_beds": available,
        "occupancy_rate": round(occupied / total * 100, 2) if total else 0,
    }
