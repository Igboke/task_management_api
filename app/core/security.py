from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import get_user_by_email # Needed to retrieve user from DB
from app.database import get_db # Needed for the dependency
from app.models import User as DBUser # Needed for type hinting and database operations
from app.schemas import TokenData # Pydantic schema for token payload validation

# OAuth2PasswordBearer is a FastAPI utility that helps implement OAuth2 password flow.
# It expects the access token in the "Authorization" header as "Bearer <token>".
# The `tokenUrl` tells FastAPI where to find the endpoint that issues tokens (our login endpoint). Documentation purposes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Encodes a payload into a JWT access token.
    The payload typically contains a 'sub' (subject) field, which is usually the user's identifier (e.g., email).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def verify_access_token(token: str, db_session: AsyncSession) -> DBUser:
    """
    Decodes and verifies a JWT access token, then fetches the corresponding user from the database.
    Raises HTTPException if the token is invalid, expired, or the user is not found/active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token using the secret key and algorithm
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Validate 'sub' (subject) claim, which should be the user's email
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # Optionally, validate the payload structure with Pydantic (good practice)
        token_data = TokenData(email=email) # Validates email format

    except JWTError:
        # Catch any JWT-related errors
        raise credentials_exception

    # Retrieve the user from the database based on the email extracted from the token
    user = await get_user_by_email(db_session, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> DBUser:
    """
    FastAPI dependency function to get the current authenticated user.
    This function will be used in path operations to protect endpoints.
    It automatically extracts the token, verifies it, and returns the DBUser object.
    """
    return await verify_access_token(token, db)

async def create_verification_access_token(user: DBUser) -> str:
    """
    Creates a verification token for the user.
    This token can be used to verify the user's email address.
    the payload typically includes the user's email and expiration timestamp.
    """
    data = {"sub": user.email, "type": 'email verification'}

    # Set the expiration time for the verification token
    # The token will expire after a specified number of hours defined in settings
    expires_delta = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    # Update the payload with the expiration time
    data.update({"exp": expires_delta})
    # Encode the payload into a JWT token using the secret key and algorithm
    encoded_jwt = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt