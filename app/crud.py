from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc
from typing import List, Optional
from utils import hash_password, verify_password
import asyncio
from app.models import User as DBUser, Task as DBTask
from app import schemas


async def create_user(db: AsyncSession, user_create: schemas.UserCreate) -> DBUser:
    """
    Create a new user in the database.
    This function takes a Pydantic model for user creation, hashes the password,
    and saves the user to the database.
    - :param db: The database session to use for the operation.
    - :param user_create: The Pydantic model containing user creation data.
    - :return: The created user as a SQLAlchemy model instance.
    """
    user_create.password = hash_password(user_create.password)
    
    
    new_user = DBUser(**user_create.model_dump(exclude_unset=True))
    new_user.is_verified = False # Explicitly ensure new users are not verified

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user) # Refresh to get auto-generated ID, timestamps etc.
    return new_user

async def verify_user_email(db: AsyncSession, email: str) -> Optional[DBUser]:
    """
    Updates a user's is_verified status to True.
    - :param db: The database session.
    - :param email: The email of the user to verify.
    - :return: The updated user, or None if not found.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    
    if user.is_verified: # Already verified
        return user

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[DBUser]:
    """
    Retrieve a user by their email address.
    - :param db : The database session to use for the operation.
    - :param email: The email address of the user to retrieve.
    - :return: The user as a SQLAlchemy model instance, or None if not found.
    """
    result = await db.execute(select(DBUser).where(DBUser.email == email))
    user = result.scalar_one_or_none()
    return user

async def get_user(db: AsyncSession, user_id: int) -> Optional[DBUser]:
    """
    Retrieve a user by their ID.
    - :param db: The database session to use for the operation.
    - :param user_id: The ID of the user to retrieve.
    - :return: The user as a SQLAlchemy model instance, or None if not found.
    """
    result = await db.execute(select(DBUser).where(DBUser.id == user_id))
    user = result.scalar_one_or_none()
    return user

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[DBUser]:
    """
    Retrieve a list of users with pagination.
    - :param db: The database session to use for the operation.
    - :param skip: The number of records to skip (for pagination).
    - :param limit: The maximum number of records to return.
    - :return: A list of users as SQLAlchemy model instances.
    """
    result = await db.execute(select(DBUser).offset(skip).limit(limit))
    return result.scalars().all()

async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate) -> Optional[DBUser]:
    """
    Update an existing user in the database.
    This function takes a Pydantic model for user updates, retrieves the user by ID,
    and applies the updates to the user model.
    - :param db: The database session to use for the operation.
    - :param user_id: The ID of the user to update.
    - :param user_update: The Pydantic model containing user update data.
    - :return: The updated user as a SQLAlchemy model instance, or None if not found.
    """
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    # Update fields from the Pydantic schema that were actually set
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        # Handle password hashing here
        if key == "password":
           setattr(db_user, key, hash_password(value))
        else:
            setattr(db_user, key, value)

    await db.commit()
    await db.refresh(db_user)
    return db_user

async def delete_user(db: AsyncSession, user_id: int) -> Optional[DBUser]:
    """
    Delete a user from the database by their ID.
    - :param db: The database session to use for the operation.
    - :param user_id: The ID of the user to delete.
    - :return: The deleted user as a SQLAlchemy model instance, or None if not found.
    """
     # First, check if the user exists
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    await db.delete(db_user)
    await db.commit()
    return db_user

async def authorize_user(user_data:schemas.UserCreate,validated_mail_user:DBUser) -> bool:
    """
    Authorizes a user by verifying their plain password against the stored hashed password.
    This function runs the synchronous password verification in a separate thread
    to prevent blocking the main event loop.

    - :param user_data: The Pydantic model (schemas.UserCreate) containing the plain text password from the request.
    - :param validated_mail_user: The SQLAlchemy model instance (DBUser) retrieved from the database,
                                  containing the hashed password.
    - :return: True if the passwords match, False otherwise.
    """

    #compare passwords
    is_password_correct = await asyncio.to_thread(
        verify_password,
        user_data.password, # Direct access to plain password from Pydantic model
        validated_mail_user.password # Hashed password from DBUser model
    )
    return is_password_correct

async def get_user_by_verification_token(db: AsyncSession, token: str) -> Optional[DBUser]:
    """
    Retrieves a user by their unique verification token.
    This function checks if the token matches a user in the database and ensures that the token
    has not expired and the user is not already verified.
    - :param db: The database session to use for the operation.
    - :param token: The verification token to search for.
    - :return: The user as a SQLAlchemy model instance if found, or None if not found or expired.
    """
    now = datetime.now(timezone.utc)
    # Check for matching token and ensuring it's not expired
    result = await db.execute(
        select(DBUser).where(
            DBUser.verification_token == token,
            DBUser.is_verified == False, # Only consider unverified users
            DBUser.verification_token_expires_at > now # Ensure token is not expired
        )
    )
    user = result.scalar_one_or_none()
    return user

async def mark_user_as_verified(db: AsyncSession, user: DBUser) -> DBUser:
    """
    Marks a user's email as verified and clears the verification token.
    This function updates the user's verification status in the database.
    - :param db: The database session to use for the operation.
    - :param user: The user model instance to update.
    - :return: The updated user as a SQLAlchemy model instance.
    """
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.commit()
    await db.refresh(user)
    return user


# Task CRUD Operations
async def create_task(db: AsyncSession, task_create: schemas.TaskCreate, user_id: int) -> DBTask:
    """
    Create a new task in the database.
    This function takes a Pydantic model for task creation and saves the task to the database.
    - :param db: The database session to use for the operation.
    - :param task_create: The Pydantic model containing task creation data.
    - :param user_id: The ID of the user to whom the task belongs.
    - :return: The created task as a SQLAlchemy model instance.
    """
    new_task = DBTask(**task_create.model_dump(), user_id=user_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

async def get_task(db: AsyncSession, task_id: int) -> Optional[DBTask]:
    """
    Retrieve a task by its ID.
    - :param db: The database session to use for the operation.
    - :param task_id: The ID of the task to retrieve.
    - :return: The task as a SQLAlchemy model instance, or None if not found.
    """
    result = await db.execute(select(DBTask).where(DBTask.id == task_id))
    task = result.scalar_one_or_none()
    return task

async def get_user_tasks(
    db: AsyncSession,
    user_id: int,
    status_filter: Optional[schemas.TaskStatus] = None,
    sort_by: Optional[str] = None,
    order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 100
) -> List[DBTask]:
    """
    Retrieves a list of tasks for a specific user with pagination, filtering, and sorting.
    - db: Datebase session
    - user_id: id of the user
    - status_filter: (in progress, pending, completed)
    - sort_by:  key terms 'created_at', 'due_date', 'title'
    - order: asc- ascending, desc- descending, default is ascending
    - skip:
    - limit:
    """
    query = select(DBTask).where(DBTask.user_id == user_id)

    if status_filter:
        query = query.where(DBTask.status == status_filter)

    if sort_by:
        # Define allowed sortable fields to prevent SQL injection
        allowed_sort_fields = ['id', 'title', 'created_at', 'updated_at', 'due_date', 'status']
        if sort_by not in allowed_sort_fields:
            sort_by = None # Ignore invalid sort_by
        else:
            # Apply sorting
            if order and order.lower() == "desc":
                query = query.order_by(desc(getattr(DBTask, sort_by)))
            else: # Default to ascending
                query = query.order_by(asc(getattr(DBTask, sort_by)))

    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_task(db: AsyncSession, task_id: int, task_update: schemas.TaskUpdate) -> None | DBTask | str:
    """
    Update an existing task in the database.
    This function takes a Pydantic model for task updates, retrieves the task by ID,
    and applies the updates to the task model.
    - :param db: The database session to use for the operation.
    - :param task_id: The ID of the task to update.
    - :param task_update: The Pydantic model containing task update data.
    - :return: The updated task as a SQLAlchemy model instance, or None if not found.
    """
    db_task = await get_task(db, task_id)
    if not db_task:
        return None
    # Update fields from the Pydantic schema that were actually set
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    await db.commit()
    await db.refresh(db_task)
    return db_task
    
async def delete_task(db: AsyncSession, task_id: int) -> Optional[DBTask]:
    """
    Delete a task from the database by its ID.
    - :param db: The database session to use for the operation.
    - :param task_id: The ID of the task to delete.
    - :return: The deleted task as a SQLAlchemy model instance, or None if not found.
    """
    db_task = await get_task(db, task_id)
    if not db_task:
        return None
    # If the task exists, delete it
    await db.delete(db_task)
    await db.commit()
    return db_task