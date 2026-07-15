from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PRINCIPAL = "principal"
    WARDEN = "warden"
    ACCOUNTANT = "accountant"
    TEACHER = "teacher"
    GUARD = "guard"
    STUDENT = "student"
    PARENT = "parent"
    MESS_MANAGER = "mess_manager"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class StudentStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    GRADUATED = "graduated"
    WITHDRAWN = "withdrawn"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class RoomStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class BedStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AllocationStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(512))
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    student_profile: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    staff_profile: Mapped[Staff | None] = relationship(back_populates="user", uselist=False)


class Grade(Base, TimestampMixin):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("name", "section", "academic_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    section: Mapped[str] = mapped_column(String(20))
    academic_year: Mapped[str] = mapped_column(String(20), index=True)
    class_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"))

    students: Mapped[list[Student]] = relationship(back_populates="grade")


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    employee_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    designation: Mapped[str] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    joining_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="staff_profile")


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    admission_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    date_of_birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[Gender] = mapped_column(Enum(Gender))
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"), index=True)
    guardian_name: Mapped[str] = mapped_column(String(150))
    guardian_phone: Mapped[str] = mapped_column(String(30))
    guardian_email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[StudentStatus] = mapped_column(Enum(StudentStatus), default=StudentStatus.ACTIVE, index=True)

    user: Mapped[User | None] = relationship(back_populates="student_profile")
    grade: Mapped[Grade | None] = relationship(back_populates="students")
    attendances: Mapped[list[Attendance]] = relationship(back_populates="student", cascade="all, delete-orphan")
    fee_invoices: Mapped[list[FeeInvoice]] = relationship(back_populates="student", cascade="all, delete-orphan")
    allocations: Mapped[list[HostelAllocation]] = relationship(back_populates="student")


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "attendance_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), index=True)
    remarks: Mapped[str | None] = mapped_column(String(255))
    marked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    student: Mapped[Student] = relationship(back_populates="attendances")


class FeeInvoice(Base, TimestampMixin):
    __tablename__ = "fee_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    fee_type: Mapped[str] = mapped_column(String(80), index=True)
    billing_period: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="fee_invoices")
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("fee_invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(50))
    transaction_ref: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    invoice: Mapped[FeeInvoice] = relationship(back_populates="payments")


class HostelBuilding(Base, TimestampMixin):
    __tablename__ = "hostel_buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    gender_type: Mapped[Gender] = mapped_column(Enum(Gender))
    address: Mapped[str | None] = mapped_column(Text)
    warden_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    rooms: Mapped[list[HostelRoom]] = relationship(back_populates="building", cascade="all, delete-orphan")


class HostelRoom(Base, TimestampMixin):
    __tablename__ = "hostel_rooms"
    __table_args__ = (UniqueConstraint("building_id", "room_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("hostel_buildings.id"), index=True)
    room_no: Mapped[str] = mapped_column(String(30), index=True)
    floor: Mapped[int] = mapped_column(Integer, default=0)
    capacity: Mapped[int] = mapped_column(Integer)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[RoomStatus] = mapped_column(Enum(RoomStatus), default=RoomStatus.ACTIVE)

    building: Mapped[HostelBuilding] = relationship(back_populates="rooms")
    beds: Mapped[list[HostelBed]] = relationship(back_populates="room", cascade="all, delete-orphan")


class HostelBed(Base, TimestampMixin):
    __tablename__ = "hostel_beds"
    __table_args__ = (UniqueConstraint("room_id", "bed_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("hostel_rooms.id"), index=True)
    bed_no: Mapped[str] = mapped_column(String(30))
    status: Mapped[BedStatus] = mapped_column(Enum(BedStatus), default=BedStatus.AVAILABLE, index=True)

    room: Mapped[HostelRoom] = relationship(back_populates="beds")
    allocations: Mapped[list[HostelAllocation]] = relationship(back_populates="bed")


class HostelAllocation(Base, TimestampMixin):
    __tablename__ = "hostel_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("hostel_beds.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[AllocationStatus] = mapped_column(Enum(AllocationStatus), default=AllocationStatus.ACTIVE, index=True)
    allocated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    checkout_notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(back_populates="allocations")
    bed: Mapped[HostelBed] = relationship(back_populates="allocations")


class MessPlan(Base, TimestampMixin):
    __tablename__ = "mess_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    meal_schedule: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MessSubscription(Base, TimestampMixin):
    __tablename__ = "mess_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("mess_plans.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class VisitorLog(Base, TimestampMixin):
    __tablename__ = "visitor_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    visitor_name: Mapped[str] = mapped_column(String(150))
    relation: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(30))
    purpose: Mapped[str | None] = mapped_column(String(255))
    identity_reference: Mapped[str | None] = mapped_column(String(100))
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    destination: Mapped[str | None] = mapped_column(String(255))
    contact_during_leave: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.PENDING, index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_notes: Mapped[str | None] = mapped_column(Text)


class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM, index=True)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus), default=ComplaintStatus.OPEN, index=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolution: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
