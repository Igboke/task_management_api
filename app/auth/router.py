from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Specific for username/password form data
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app import crud, schemas
from app.database import get_db # Database session dependency
from app.core.security import create_access_token # JWT creation utility
from app.core.config import settings # Access to JWT expiration settings
from app.models import User as DBUser # For type hinting

router = APIRouter()

@router.post("/token", response_model=schemas.Token, status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), # Expects form data: username (email) and password
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user based on provided username (email) and password,
    and returns a JWT access token upon successful authentication.
    """
    user: DBUser = await crud.get_user_by_email(db, email=form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not await crud.authorize_user(
        schemas.UserCreate(email=form_data.username, password=form_data.password),
        user
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, # 'sub' claim (subject) is typically a unique identifier for the user
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}