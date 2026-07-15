from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.entities import FeeInvoice, InvoiceStatus, Payment, Student, User, UserRole
from app.schemas.api import InvoiceCreate, InvoiceRead, PaymentCreate, PaymentRead
from app.services.audit import write_audit

router = APIRouter(prefix="/fees", tags=["Fees & Payments"])
finance_roles = (UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.ACCOUNTANT)
read_roles = finance_roles + (UserRole.WARDEN, UserRole.PARENT, UserRole.STUDENT)


def calculate_invoice_status(invoice: FeeInvoice) -> InvoiceStatus:
    if invoice.paid_amount >= invoice.amount:
        return InvoiceStatus.PAID
    if invoice.paid_amount > 0:
        return InvoiceStatus.PARTIAL
    if invoice.due_date < date.today():
        return InvoiceStatus.OVERDUE
    return InvoiceStatus.PENDING


@router.post("/invoices", response_model=InvoiceRead, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*finance_roles)),
):
    if not db.get(Student, payload.student_id):
        raise HTTPException(status_code=404, detail="Student not found")
    invoice = FeeInvoice(
        **payload.model_dump(),
        invoice_no=f"INV-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:8].upper()}",
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.PENDING,
    )
    db.add(invoice)
    db.flush()
    write_audit(db, actor.id, "invoice.created", "fee_invoice", invoice.id, {"amount": str(invoice.amount)})
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(
    student_id: int | None = None,
    status: InvoiceStatus | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*read_roles)),
):
    stmt = select(FeeInvoice)
    if student_id:
        stmt = stmt.where(FeeInvoice.student_id == student_id)
    if status:
        stmt = stmt.where(FeeInvoice.status == status)
    invoices = list(db.scalars(stmt.order_by(FeeInvoice.due_date.desc()).limit(limit)))
    changed = False
    for invoice in invoices:
        computed = calculate_invoice_status(invoice)
        if invoice.status not in (InvoiceStatus.CANCELLED, InvoiceStatus.PAID) and computed != invoice.status:
            invoice.status = computed
            changed = True
    if changed:
        db.commit()
    return invoices


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentRead, status_code=201)
def pay_invoice(
    invoice_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*finance_roles)),
):
    invoice = db.get(FeeInvoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Cancelled invoice cannot be paid")
    outstanding = invoice.amount - invoice.paid_amount
    if payload.amount > outstanding:
        raise HTTPException(status_code=422, detail=f"Payment exceeds outstanding amount {outstanding}")
    payment = Payment(
        invoice_id=invoice.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        transaction_ref=payload.transaction_ref,
        received_by=actor.id,
        paid_at=datetime.now(UTC),
    )
    invoice.paid_amount += payload.amount
    invoice.status = calculate_invoice_status(invoice)
    db.add(payment)
    try:
        db.flush()
        write_audit(db, actor.id, "payment.received", "payment", payment.id, {"invoice_id": invoice.id})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Transaction reference already used")
    db.refresh(payment)
    return payment


@router.get("/summary")
def fee_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*finance_roles)),
):
    total_billed = db.scalar(select(func.coalesce(func.sum(FeeInvoice.amount), 0))) or 0
    total_collected = db.scalar(select(func.coalesce(func.sum(FeeInvoice.paid_amount), 0))) or 0
    return {
        "total_billed": total_billed,
        "total_collected": total_collected,
        "outstanding": total_billed - total_collected,
        "collection_rate": round(float(total_collected / total_billed * 100), 2) if total_billed else 0,
    }
