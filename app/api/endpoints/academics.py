from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import Grade, User, UserRole
from app.schemas.api import GradeCreate, GradeRead
from app.services.audit import write_audit

router = APIRouter(prefix="/academics", tags=["Academics"])
manage_roles = (UserRole.ADMIN, UserRole.PRINCIPAL)
read_roles = manage_roles + (UserRole.TEACHER, UserRole.WARDEN, UserRole.ACCOUNTANT)


@router.post("/grades", response_model=GradeRead, status_code=201)
def create_grade(
    payload: GradeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    grade = Grade(**payload.model_dump())
    db.add(grade)
    try:
        db.flush()
        write_audit(db, actor.id, "grade.created", "grade", grade.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Grade, section and academic year already exist")
    db.refresh(grade)
    return grade


@router.get("/grades", response_model=list[GradeRead])
def list_grades(
    academic_year: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(Grade)
    if academic_year:
        stmt = stmt.where(Grade.academic_year == academic_year)
    return list(db.scalars(stmt.order_by(Grade.name, Grade.section)))
