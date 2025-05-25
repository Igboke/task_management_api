# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import users, tasks

api_router = APIRouter()

api_router.include_router(tasks.router,prefix="/tasks", tags=["Tasks"])
# Include the users router under the /users prefix
api_router.include_router(users.router, prefix="/users", tags=["Users"])