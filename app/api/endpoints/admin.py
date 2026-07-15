from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import (
    BedStatus,
    Complaint,
    ComplaintStatus,
    FeeInvoice,
    HostelBed,
    LeaveRequest,
    RequestStatus,
    Student,
    StudentStatus,
    User,
    UserRole,
    VisitorLog,
)
from app.schemas.api import DashboardRead

router = APIRouter(prefix="/admin", tags=["Dashboard & Analytics"])
admin_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.WARDEN)


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*admin_roles)),
):
    total_students = db.scalar(select(func.count(Student.id))) or 0
    active_students = db.scalar(select(func.count(Student.id)).where(Student.status == StudentStatus.ACTIVE)) or 0
    capacity = db.scalar(select(func.count(HostelBed.id))) or 0
    occupied = db.scalar(select(func.count(HostelBed.id)).where(HostelBed.status == BedStatus.OCCUPIED)) or 0
    available = db.scalar(select(func.count(HostelBed.id)).where(HostelBed.status == BedStatus.AVAILABLE)) or 0
    billed = db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount), 0))) or Decimal("0")
    paid = db.scalar(select(func.coalesce(func.sum(FeeInvoice.paid_amount), 0))) or Decimal("0")
    pending_leave = db.scalar(select(func.count(LeaveRequest.id)).where(LeaveRequest.status == RequestStatus.PENDING)) or 0
    open_complaints = db.scalar(
        select(func.count(Complaint.id)).where(Complaint.status.in_([ComplaintStatus.OPEN, ComplaintStatus.IN_PROGRESS]))
    ) or 0
    active_visitors = db.scalar(select(func.count(VisitorLog.id)).where(VisitorLog.check_out.is_(None))) or 0
    return DashboardRead(
        total_students=total_students,
        active_students=active_students,
        hostel_capacity=capacity,
        occupied_beds=occupied,
        available_beds=available,
        occupancy_rate=round(occupied / capacity * 100, 2) if capacity else 0,
        pending_fee_amount=billed - paid,
        pending_leave_requests=pending_leave,
        open_complaints=open_complaints,
        active_visitors=active_visitors,
    )
