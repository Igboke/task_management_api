# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import users

api_router = APIRouter()

# Include the books router under the /users prefix
api_router.include_router(users.router, prefix="/users", tags=["Users"])