from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import Grade, Student, StudentStatus, User, UserRole
from app.schemas.api import StudentCreate, StudentRead, StudentUpdate
from app.schemas.common import PaginatedResponse
from app.services.audit import write_audit

router = APIRouter(prefix="/students", tags=["Students"])
manage_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.WARDEN)
read_roles = manage_roles + (UserRole.TEACHER, UserRole.ACCOUNTANT, UserRole.GUARD, UserRole.MESS_MANAGER)


@router.post("", response_model=StudentRead, status_code=201)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    if payload.grade_id and not db.get(Grade, payload.grade_id):
        raise HTTPException(status_code=404, detail="Grade not found")
    student = Student(**payload.model_dump())
    db.add(student)
    try:
        db.flush()
        write_audit(db, actor.id, "student.created", "student", student.id, {"admission_no": student.admission_no})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admission number or user mapping already exists")
    db.refresh(student)
    return student


@router.get("", response_model=PaginatedResponse[StudentRead])
def list_students(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    grade_id: int | None = None,
    status: StudentStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    filters = []
    if search:
        term = f"%{search}%"
        filters.append(or_(Student.admission_no.ilike(term), Student.first_name.ilike(term), Student.last_name.ilike(term)))
    if grade_id:
        filters.append(Student.grade_id == grade_id)
    if status:
        filters.append(Student.status == status)
    stmt = select(Student).where(*filters)
    total = db.scalar(select(func.count(Student.id)).where(*filters)) or 0
    items = list(db.scalars(stmt.order_by(Student.id.desc()).offset((page - 1) * size).limit(size)))
    return PaginatedResponse(items=items, total=total, page=page, size=size)


@router.get("/{student_id}", response_model=StudentRead)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("grade_id") and not db.get(Grade, data["grade_id"]):
        raise HTTPException(status_code=404, detail="Grade not found")
    for key, value in data.items():
        setattr(student, key, value)
    write_audit(db, actor.id, "student.updated", "student", student.id, {"fields": list(data)})
    db.commit()
    db.refresh(student)
    return student
