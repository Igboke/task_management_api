from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.security import get_current_user, create_email_verification_access_token
from app import crud, schemas
from app.database import get_db
from app.models import User as DBUser
from utils import send_verification_mail

router = APIRouter()

@router.post("/login", status_code=status.HTTP_200_OK)
async def user_login(user_data:schemas.UserCreate,
                     db: AsyncSession=Depends(get_db)) -> dict[str,str]:
    #check if email exists
    existing_user = await crud.get_user_by_email(db=db,email=user_data.email)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid credentials")
    #compare and verify password
    valiation_request = await crud.authorize_user(user_data,existing_user)
    if not valiation_request:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid credentials")
    return {"Message":"Welcome"}

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    request: Request = Depends() 
):
    """
    This endpoint allows the creation of a new user in the system.
    It checks if a user with the provided email already exists, and if not, it creates a new user with the provided details.
    - :param user_data: The Pydantic model containing user creation data.
    - :param db: The database session to use for the operation.
    - :return: The created user as a SQLAlchemy model instance, serialized to UserResponse schema.\n
    **FastAPI automatically converts the SQLAlchemy model instance (`DBUser`) into the `UserResponse` Pydantic schema.\nThe `from_attributes = True` in `UserResponse.Config` allows Pydantic to read attributes directly from the SQLAlchemy model object.**

    """
    existing_user = await crud.get_user_by_email(db, user_data.email)
    if existing_user:
        if not existing_user.is_verified:
            # Resend verification email if user exists but isn't verified to be fixed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists but is not verified. Please check your inbox for a verification link.")
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    user = await crud.create_user(db, user_data)

    verification_token = await create_email_verification_access_token(user.email)
    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create verification token"
        )
    
    #construct the verification link
    # scheme = request.url.scheme  # 'http' or 'https'
    # netloc = request.url.netloc  # e.g., 'example.com'
    # verification_url = f"{scheme}://{netloc}/api/v1/verify-email?token={verification_token}"
    #request.base_url/api/v1/verify-email?token={verification_token} also works
    verification_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/verify_email?token={verification_token}"

    await send_verification_mail(user,verification_url)

    # Return the created user as a Pydantic model
    # FastAPI will automatically convert the SQLAlchemy model instance to the Pydantic schema
    # using the `from_attributes=True` in the UserResponse schema's Config
    # This allows Pydantic to read attributes directly from the SQLAlchemy model object. 
    return schemas.UserResponse.model_validate(user, from_attributes=True, context={"detail": "User created successfully. Please check your email for a verification link."})


@router.get("/me", response_model=schemas.UserResponse)
async def read_current_user_endpoint(
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Retrieves the details of the currently authenticated user.
    - :param current_user: The authenticated user object (injected by `get_current_user` dependency).
    - :return: The current user's details.
    """
    return current_user

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user_by_id_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Retrieve a user by ID.
    - :param user_id: The ID of the user to retrieve.
    - :param db: The database session to use for the operation.
    - :param current_user: The authenticated user (injected by dependency).
    - :return: The user as a SQLAlchemy model instance, serialized to UserResponse schema.
    """
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this user's profile")
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
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Update an existing user.
    - :param user_id: The ID of the user to update.
    - :param user_update: The Pydantic model containing user update data.
    - :param db: The database session to use for the operation.
    - :param current_user: The authenticated user (injected by dependency).

    - :return: The updated user as a SQLAlchemy model instance, serialized to UserResponse schema.
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")
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
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Delete a user.
    - :param user_id: The ID of the user to delete.
    - :param db: The database session to use for the operation.
    - :param current_user: The authenticated user (injected by dependency).
    - :return: None (204 No Content response).
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")
    deleted_user = await crud.delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None