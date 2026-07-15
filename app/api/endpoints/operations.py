from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import (
    Complaint,
    LeaveRequest,
    RequestStatus,
    Student,
    User,
    UserRole,
    VisitorLog,
)
from app.schemas.api import (
    ComplaintCreate,
    ComplaintRead,
    ComplaintUpdate,
    LeaveCreate,
    LeaveDecision,
    LeaveRead,
    VisitorCheckIn,
    VisitorRead,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/operations", tags=["Hostel Operations"])
warden_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.WARDEN)
guard_roles = warden_roles + (UserRole.GUARD,)
student_roles = warden_roles + (UserRole.STUDENT, UserRole.PARENT)


@router.post("/visitors/check-in", response_model=VisitorRead, status_code=201)
def visitor_check_in(
    payload: VisitorCheckIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*guard_roles)),
):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Student not found")
    log = VisitorLog(**payload.model_dump(), check_in=datetime.now(UTC), approved_by=actor.id)
    db.add(log)
    db.flush()
    write_audit(db, actor.id, "visitor.checked_in", "visitor_log", log.id, {"student_id": log.student_id})
    db.commit()
    db.refresh(log)
    return log


@router.post("/visitors/{visitor_id}/check-out", response_model=VisitorRead)
def visitor_check_out(
    visitor_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*guard_roles)),
):
    log = db.get(VisitorLog, visitor_id)
    if not log:
        raise HTTPException(status_code=404, detail="Visitor record not found")
    if log.check_out:
        raise HTTPException(status_code=409, detail="Visitor already checked out")
    log.check_out = datetime.now(UTC)
    write_audit(db, actor.id, "visitor.checked_out", "visitor_log", log.id)
    db.commit()
    db.refresh(log)
    return log


@router.get("/visitors", response_model=list[VisitorRead])
def list_visitors(
    student_id: int | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*guard_roles)),
):
    stmt = select(VisitorLog)
    if student_id:
        stmt = stmt.where(VisitorLog.student_id == student_id)
    if active_only:
        stmt = stmt.where(VisitorLog.check_out.is_(None))
    return list(db.scalars(stmt.order_by(VisitorLog.check_in.desc()).limit(500)))


@router.post("/leave-requests", response_model=LeaveRead, status_code=201)
def create_leave_request(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*student_roles)),
):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if actor.role == UserRole.STUDENT and student.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Students may create leave requests only for themselves")
    request = LeaveRequest(**payload.model_dump(), status=RequestStatus.PENDING)
    db.add(request)
    db.flush()
    write_audit(db, actor.id, "leave_request.created", "leave_request", request.id)
    db.commit()
    db.refresh(request)
    return request


@router.get("/leave-requests", response_model=list[LeaveRead])
def list_leave_requests(
    student_id: int | None = None,
    status: RequestStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*student_roles)),
):
    stmt = select(LeaveRequest)
    if student_id:
        stmt = stmt.where(LeaveRequest.student_id == student_id)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    return list(db.scalars(stmt.order_by(LeaveRequest.id.desc()).limit(500)))


@router.patch("/leave-requests/{request_id}/decision", response_model=LeaveRead)
def decide_leave_request(
    request_id: int,
    payload: LeaveDecision,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*warden_roles)),
):
    request = db.get(LeaveRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="Leave request has already been reviewed")
    request.status = payload.status
    request.review_notes = payload.review_notes
    request.reviewed_by = actor.id
    write_audit(db, actor.id, "leave_request.reviewed", "leave_request", request.id, {"status": payload.status.value})
    db.commit()
    db.refresh(request)
    return request


@router.post("/complaints", response_model=ComplaintRead, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*student_roles)),
):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if actor.role == UserRole.STUDENT and student.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Students may create complaints only for themselves")
    complaint = Complaint(**payload.model_dump())
    db.add(complaint)
    db.flush()
    write_audit(db, actor.id, "complaint.created", "complaint", complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/complaints", response_model=list[ComplaintRead])
def list_complaints(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*student_roles)),
):
    stmt = select(Complaint)
    if student_id:
        stmt = stmt.where(Complaint.student_id == student_id)
    return list(db.scalars(stmt.order_by(Complaint.id.desc()).limit(500)))


@router.patch("/complaints/{complaint_id}", response_model=ComplaintRead)
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*warden_roles)),
):
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(complaint, key, value)
    write_audit(db, actor.id, "complaint.updated", "complaint", complaint.id, {"fields": list(data)})
    db.commit()
    db.refresh(complaint)
    return complaint
