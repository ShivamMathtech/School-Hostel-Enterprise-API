from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.entities import (
    AllocationStatus,
    AttendanceStatus,
    BedStatus,
    ComplaintStatus,
    Gender,
    InvoiceStatus,
    Priority,
    RequestStatus,
    RoomStatus,
    StudentStatus,
    UserRole,
)
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole
    phone: str | None = None


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    phone: str | None
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class GradeCreate(BaseModel):
    name: str
    section: str
    academic_year: str
    class_teacher_id: int | None = None


class GradeRead(ORMModel):
    id: int
    name: str
    section: str
    academic_year: str
    class_teacher_id: int | None


class StudentCreate(BaseModel):
    admission_no: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    grade_id: int | None = None
    guardian_name: str
    guardian_phone: str
    guardian_email: EmailStr | None = None
    address: str | None = None
    medical_notes: str | None = None
    user_id: int | None = None


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    grade_id: int | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_email: EmailStr | None = None
    address: str | None = None
    medical_notes: str | None = None
    status: StudentStatus | None = None


class StudentRead(ORMModel):
    id: int
    user_id: int | None
    admission_no: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    grade_id: int | None
    guardian_name: str
    guardian_phone: str
    guardian_email: EmailStr | None
    address: str | None
    medical_notes: str | None
    status: StudentStatus
    created_at: datetime


class AttendanceCreate(BaseModel):
    student_id: int
    attendance_date: date
    status: AttendanceStatus
    remarks: str | None = None


class AttendanceBulkCreate(BaseModel):
    records: list[AttendanceCreate] = Field(min_length=1, max_length=500)


class AttendanceRead(ORMModel):
    id: int
    student_id: int
    attendance_date: date
    status: AttendanceStatus
    remarks: str | None
    marked_by: int


class InvoiceCreate(BaseModel):
    student_id: int
    fee_type: str
    billing_period: str
    amount: Decimal = Field(gt=0)
    due_date: date
    notes: str | None = None


class InvoiceRead(ORMModel):
    id: int
    invoice_no: str
    student_id: int
    fee_type: str
    billing_period: str
    amount: Decimal
    paid_amount: Decimal
    due_date: date
    status: InvoiceStatus
    notes: str | None


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: str
    transaction_ref: str = Field(min_length=3, max_length=100)


class PaymentRead(ORMModel):
    id: int
    invoice_id: int
    amount: Decimal
    payment_method: str
    transaction_ref: str
    received_by: int
    paid_at: datetime


class BuildingCreate(BaseModel):
    name: str
    gender_type: Gender
    address: str | None = None
    warden_staff_id: int | None = None


class BuildingRead(ORMModel):
    id: int
    name: str
    gender_type: Gender
    address: str | None
    warden_staff_id: int | None
    is_active: bool


class RoomCreate(BaseModel):
    building_id: int
    room_no: str
    floor: int = 0
    capacity: int = Field(ge=1, le=20)
    monthly_fee: Decimal = Field(ge=0)
    status: RoomStatus = RoomStatus.ACTIVE


class RoomRead(ORMModel):
    id: int
    building_id: int
    room_no: str
    floor: int
    capacity: int
    monthly_fee: Decimal
    status: RoomStatus


class BedRead(ORMModel):
    id: int
    room_id: int
    bed_no: str
    status: BedStatus


class AllocationCreate(BaseModel):
    student_id: int
    bed_id: int
    start_date: date
    deposit_amount: Decimal = Field(ge=0, default=Decimal("0.00"))


class CheckoutRequest(BaseModel):
    end_date: date
    checkout_notes: str | None = None


class AllocationRead(ORMModel):
    id: int
    student_id: int
    bed_id: int
    start_date: date
    end_date: date | None
    deposit_amount: Decimal
    status: AllocationStatus
    allocated_by: int
    checkout_notes: str | None


class MessPlanCreate(BaseModel):
    name: str
    description: str | None = None
    monthly_fee: Decimal = Field(gt=0)
    meal_schedule: dict[str, Any] | None = None


class MessPlanRead(ORMModel):
    id: int
    name: str
    description: str | None
    monthly_fee: Decimal
    meal_schedule: dict[str, Any] | None
    is_active: bool


class MessSubscriptionCreate(BaseModel):
    student_id: int
    plan_id: int
    start_date: date
    end_date: date | None = None


class MessSubscriptionRead(ORMModel):
    id: int
    student_id: int
    plan_id: int
    start_date: date
    end_date: date | None
    is_active: bool


class VisitorCheckIn(BaseModel):
    student_id: int
    visitor_name: str
    relation: str
    phone: str
    purpose: str | None = None
    identity_reference: str | None = None


class VisitorRead(ORMModel):
    id: int
    student_id: int
    visitor_name: str
    relation: str
    phone: str
    purpose: str | None
    identity_reference: str | None
    check_in: datetime
    check_out: datetime | None
    approved_by: int


class LeaveCreate(BaseModel):
    student_id: int
    from_date: date
    to_date: date
    reason: str
    destination: str | None = None
    contact_during_leave: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.to_date < self.from_date:
            raise ValueError("to_date must be on or after from_date")
        return self


class LeaveDecision(BaseModel):
    status: RequestStatus
    review_notes: str | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == RequestStatus.PENDING:
            raise ValueError("Decision must be approved or rejected")
        return self


class LeaveRead(ORMModel):
    id: int
    student_id: int
    from_date: date
    to_date: date
    reason: str
    destination: str | None
    contact_during_leave: str | None
    status: RequestStatus
    reviewed_by: int | None
    review_notes: str | None


class ComplaintCreate(BaseModel):
    student_id: int
    category: str
    description: str
    priority: Priority = Priority.MEDIUM


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus | None = None
    assigned_to: int | None = None
    resolution: str | None = None
    priority: Priority | None = None


class ComplaintRead(ORMModel):
    id: int
    student_id: int
    category: str
    description: str
    priority: Priority
    status: ComplaintStatus
    assigned_to: int | None
    resolution: str | None
    created_at: datetime


class DashboardRead(BaseModel):
    total_students: int
    active_students: int
    hostel_capacity: int
    occupied_beds: int
    available_beds: int
    occupancy_rate: float
    pending_fee_amount: Decimal
    pending_leave_requests: int
    open_complaints: int
    active_visitors: int
