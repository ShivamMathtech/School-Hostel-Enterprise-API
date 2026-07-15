# Architecture Notes

## Why a modular monolith

The domain has strongly related transactions: student admission, room allocation, fees, leave, and visitor controls. A modular monolith keeps these transactions reliable and makes local development straightforward. Modules can later be extracted behind events or APIs when independent scaling is justified.

## Suggested future service boundaries

- Identity and access service
- Student information service
- Academic and attendance service
- Finance and payment service
- Hostel inventory and allocation service
- Mess service
- Campus security and visitor service
- Notification service
- Reporting and analytics service

## Data consistency

Critical state changes are committed through SQLAlchemy transactions. Production deployments should use PostgreSQL row locks for high-contention bed allocation and payment settlement workflows. Unique constraints protect identity, room, attendance, and transaction-reference invariants.

## Asynchronous processing

Celery tasks are included as adapter examples for fee reminders and report generation. Typical asynchronous jobs include email/SMS notifications, PDF receipts, scheduled overdue processing, exports, and analytics refreshes.
