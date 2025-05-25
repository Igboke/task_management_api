# app/main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.api.v1.api import api_router

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Task Manager API",
    description="A simple Task Manager API built with FastAPI",
    version="0.1.0",
    docs_url="/docs",      
    redoc_url="/redoc"      
)


# Include the API router with a prefix for versioning
app.include_router(api_router, prefix="/api/v1")

# health check endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI TaskManager API! Go to /docs for API documentation."}