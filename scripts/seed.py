from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.entities import (
    BedStatus,
    FeeInvoice,
    Gender,
    Grade,
    HostelBed,
    HostelBuilding,
    HostelRoom,
    InvoiceStatus,
    MessPlan,
    Student,
    User,
    UserRole,
)


def upsert_user(db, email: str, full_name: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=hash_password("Password@123"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = upsert_user(db, settings.initial_admin_email, "System Administrator", UserRole.ADMIN)
        warden = upsert_user(db, "warden@school.local", "Hostel Warden", UserRole.WARDEN)
        accountant = upsert_user(db, "accounts@school.local", "School Accountant", UserRole.ACCOUNTANT)
        student_user = upsert_user(db, "student@school.local", "Aarav Sharma", UserRole.STUDENT)

        grade = db.scalar(select(Grade).where(Grade.name == "10", Grade.section == "A"))
        if not grade:
            grade = Grade(name="10", section="A", academic_year="2026-27")
            db.add(grade)
            db.flush()

        student = db.scalar(select(Student).where(Student.admission_no == "ADM-2026-001"))
        if not student:
            student = Student(
                user_id=student_user.id,
                admission_no="ADM-2026-001",
                first_name="Aarav",
                last_name="Sharma",
                date_of_birth=date(2011, 5, 18),
                gender=Gender.MALE,
                grade_id=grade.id,
                guardian_name="Rajesh Sharma",
                guardian_phone="+91-9000000001",
                guardian_email="parent@school.local",
                address="Dehradun, Uttarakhand",
            )
            db.add(student)
            db.flush()

        building = db.scalar(select(HostelBuilding).where(HostelBuilding.name == "Boys Hostel A"))
        if not building:
            building = HostelBuilding(name="Boys Hostel A", gender_type=Gender.MALE, address="North Campus")
            db.add(building)
            db.flush()

        room = db.scalar(select(HostelRoom).where(HostelRoom.building_id == building.id, HostelRoom.room_no == "101"))
        if not room:
            room = HostelRoom(
                building_id=building.id,
                room_no="101",
                floor=1,
                capacity=3,
                monthly_fee=Decimal("4500.00"),
            )
            db.add(room)
            db.flush()
            for index in range(1, 4):
                db.add(HostelBed(room_id=room.id, bed_no=f"B{index:02d}", status=BedStatus.AVAILABLE))

        if not db.scalar(select(MessPlan).where(MessPlan.name == "Standard Vegetarian")):
            db.add(
                MessPlan(
                    name="Standard Vegetarian",
                    description="Breakfast, lunch, evening snack and dinner",
                    monthly_fee=Decimal("3200.00"),
                    meal_schedule={
                        "breakfast": "07:30-08:30",
                        "lunch": "12:30-13:30",
                        "dinner": "19:30-20:30",
                    },
                )
            )

        if not db.scalar(select(FeeInvoice).where(FeeInvoice.invoice_no == "INV-DEMO-001")):
            db.add(
                FeeInvoice(
                    invoice_no="INV-DEMO-001",
                    student_id=student.id,
                    fee_type="Hostel Fee",
                    billing_period="July 2026",
                    amount=Decimal("4500.00"),
                    paid_amount=Decimal("0.00"),
                    due_date=date.today() + timedelta(days=10),
                    status=InvoiceStatus.PENDING,
                )
            )

        db.commit()
        print("Seed completed.")
        print("Admin: admin@school.local / Password@123")
        print("Warden: warden@school.local / Password@123")
        print("Accountant: accounts@school.local / Password@123")
        print("Student: student@school.local / Password@123")


if __name__ == "__main__":
    seed()
