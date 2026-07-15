from fastapi import APIRouter

from app.api.endpoints import academics, admin, attendance, auth, fees, hostel, mess, operations, students, system, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(academics.router)
api_router.include_router(students.router)
api_router.include_router(attendance.router)
api_router.include_router(fees.router)
api_router.include_router(hostel.router)
api_router.include_router(mess.router)
api_router.include_router(operations.router)
api_router.include_router(admin.router)
api_router.include_router(system.router)
