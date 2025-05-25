from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app import crud, schemas
from app.database import get_db
from app.models import User as DBUser # Alias SQLAlchemy User to avoid confusion

router = APIRouter()

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    This endpoint allows the creation of a new user in the system.
    It checks if a user with the provided email already exists, and if not, it creates a new user with the provided details.
    - :param user_create: The Pydantic model containing user creation data.
    - :param db: The database session to use for the operation.
    - :return: The created user as a SQLAlchemy model instance, serialized to UserResponse schema.\n
    **FastAPI will automatically convert the DBUser object to schemas.UserResponse and from_attributes = True (in the Pydantic schema helps fast API to read the attributes from the SQLAlchemy model**
    """
    existing_user = await crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    user = await crud.create_user(db, user_data)
    return user 

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a user by ID.
    - :param user_id: The ID of the user to retrieve.
    - :param db: The database session to use for the operation.
    - :return: The user as a SQLAlchemy model instance, serialized to UserResponse schema.
    """
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/", response_model=list[schemas.UserResponse])
async def read_users_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a list of users.
    - :param skip: The number of records to skip (for pagination).
    - :param limit: The maximum number of records to return.
    - :param db: The database session to use for the operation.
    - :return: A list of users as SQLAlchemy model instances, serialized to UserResponse schema.
    """
    users = await crud.get_users(db, skip=skip, limit=limit)
    return users

@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user_endpoint(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing user.
    - :param user_id: The ID of the user to update.
    - :param user_update: The Pydantic model containing user update data.
    - :param db: The database session to use for the operation.
    - :return: The updated user as a SQLAlchemy model instance, serialized to UserResponse schema.
    """
    try:
        updated_user = await crud.update_user(db, user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated_user
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists or invalid data provided"
        ) from e

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user.
    - :param user_id: The ID of the user to delete.
    - :param db: The database session to use for the operation.
    - :return: None (204 No Content response).
    """
    deleted_user = await crud.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None