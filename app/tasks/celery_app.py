from celery import Celery

from app.core.config import settings

celery_app = Celery("school_hostel", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, timezone="UTC")


@celery_app.task(name="notifications.send_fee_reminder")
def send_fee_reminder(student_id: int, invoice_id: int) -> dict[str, int | str]:
    # Replace with email/SMS provider adapter in production.
    return {"status": "queued", "student_id": student_id, "invoice_id": invoice_id}


@celery_app.task(name="reports.generate_occupancy_report")
def generate_occupancy_report() -> dict[str, str]:
    # Replace with a reporting service and object-storage upload.
    return {"status": "generated"}
