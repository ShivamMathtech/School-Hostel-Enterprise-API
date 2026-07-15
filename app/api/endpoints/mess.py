from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import MessPlan, MessSubscription, Student, User, UserRole
from app.schemas.api import MessPlanCreate, MessPlanRead, MessSubscriptionCreate, MessSubscriptionRead
from app.services.audit import write_audit

router = APIRouter(prefix="/mess", tags=["Mess Management"])
manage_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.WARDEN, UserRole.MESS_MANAGER)
read_roles = manage_roles + (UserRole.ACCOUNTANT, UserRole.STUDENT, UserRole.PARENT)


@router.post("/plans", response_model=MessPlanRead, status_code=201)
def create_plan(
    payload: MessPlanCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    plan = MessPlan(**payload.model_dump())
    db.add(plan)
    try:
        db.flush()
        write_audit(db, actor.id, "mess_plan.created", "mess_plan", plan.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mess plan name already exists")
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=list[MessPlanRead])
def list_plans(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(MessPlan)
    if active_only:
        stmt = stmt.where(MessPlan.is_active.is_(True))
    return list(db.scalars(stmt.order_by(MessPlan.name)))


@router.post("/subscriptions", response_model=MessSubscriptionRead, status_code=201)
def subscribe(
    payload: MessSubscriptionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*manage_roles)),
):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Student not found")
    plan = db.get(MessPlan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Active mess plan not found")
    active = db.scalar(
        select(MessSubscription).where(
            MessSubscription.student_id == payload.student_id,
            MessSubscription.is_active.is_(True),
        )
    )
    if active:
        raise HTTPException(status_code=409, detail="Student already has an active mess subscription")
    item = MessSubscription(**payload.model_dump(), is_active=True)
    db.add(item)
    db.flush()
    write_audit(db, actor.id, "mess_subscription.created", "mess_subscription", item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/subscriptions", response_model=list[MessSubscriptionRead])
def list_subscriptions(
    student_id: int | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(MessSubscription)
    if student_id:
        stmt = stmt.where(MessSubscription.student_id == student_id)
    if active_only:
        stmt = stmt.where(MessSubscription.is_active.is_(True))
    return list(db.scalars(stmt.order_by(MessSubscription.id.desc())))
