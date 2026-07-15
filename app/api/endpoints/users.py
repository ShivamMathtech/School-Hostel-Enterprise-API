from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.entities import User, UserRole
from app.schemas.api import UserCreate, UserRead
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["Users & RBAC"])
admin_roles = (UserRole.ADMIN, UserRole.PRINCIPAL)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*admin_roles)),
):
    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
    )
    db.add(user)
    try:
        db.flush()
        write_audit(db, actor.id, "user.created", "user", user.id, {"role": user.role.value})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    db.refresh(user)
    return user


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*admin_roles)),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if role:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * size).limit(size)))
    return PaginatedResponse(items=items, total=total, page=page, size=size)


@router.patch("/{user_id}/activation", response_model=MessageResponse)
def set_activation(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*admin_roles)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id and not is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    user.is_active = is_active
    write_audit(db, actor.id, "user.activation_changed", "user", user.id, {"is_active": is_active})
    db.commit()
    return MessageResponse(message="User activation updated")
