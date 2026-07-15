from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import Attendance, Student, User, UserRole
from app.schemas.api import AttendanceBulkCreate, AttendanceRead
from app.services.audit import write_audit

router = APIRouter(prefix="/attendance", tags=["Attendance"])
mark_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.TEACHER, UserRole.WARDEN)
read_roles = mark_roles + (UserRole.PARENT, UserRole.STUDENT)


@router.post("/bulk", response_model=list[AttendanceRead])
def mark_bulk_attendance(
    payload: AttendanceBulkCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*mark_roles)),
):
    saved: list[Attendance] = []
    for record in payload.records:
        if not db.get(Student, record.student_id):
            continue
        existing = db.scalar(
            select(Attendance).where(
                Attendance.student_id == record.student_id,
                Attendance.attendance_date == record.attendance_date,
            )
        )
        if existing:
            existing.status = record.status
            existing.remarks = record.remarks
            existing.marked_by = actor.id
            saved.append(existing)
        else:
            item = Attendance(**record.model_dump(), marked_by=actor.id)
            db.add(item)
            saved.append(item)
    db.flush()
    write_audit(db, actor.id, "attendance.bulk_marked", "attendance", metadata={"records": len(saved)})
    db.commit()
    for item in saved:
        db.refresh(item)
    return saved


@router.get("", response_model=list[AttendanceRead])
def list_attendance(
    student_id: int | None = None,
    grade_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(Attendance).join(Student)
    if student_id:
        stmt = stmt.where(Attendance.student_id == student_id)
    if grade_id:
        stmt = stmt.where(Student.grade_id == grade_id)
    if date_from:
        stmt = stmt.where(Attendance.attendance_date >= date_from)
    if date_to:
        stmt = stmt.where(Attendance.attendance_date <= date_to)
    return list(db.scalars(stmt.order_by(Attendance.attendance_date.desc()).limit(limit)))
