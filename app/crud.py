from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from utils import hash_password, verify_password
import asyncio
from app.models import User as DBUser, Task as DBTask # Alias models to avoid confusion with Pydantic schemas named similarly
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
    
    # Instantiate the SQLAlchemy model using the Pydantic model's data
    new_user = DBUser(**user_create.model_dump()) # model_dump() gives a dict compatible with DBUser
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user) # Refresh to get auto-generated ID, timestamps etc.
    return new_user

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

async def get_user_tasks(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[DBTask]:
    """
    Retrieve tasks for a specific user with pagination.
    - :param db: The database session to use for the operation.
    - :param user_id: The ID of the user whose tasks to retrieve.
    - :param skip: The number of records to skip (for pagination).
    - :param limit: The maximum number of records to return.
    - :return: A list of tasks as SQLAlchemy model instances.
    """
    result = await db.execute(
        select(DBTask).where(DBTask.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()

async def update_task(db: AsyncSession,user_id:int, task_id: int, task_update: schemas.TaskUpdate) -> None | DBTask | str:
    """
    Update an existing task in the database.
    This function takes a Pydantic model for task updates, retrieves the task by ID,
    and applies the updates to the task model.
    - :param db: The database session to use for the operation.
    - :user_id: The ID of the User.
    - :param task_id: The ID of the task to update.
    - :param task_update: The Pydantic model containing task update data.
    - :return: The updated task as a SQLAlchemy model instance, or None if not found.
    """
    db_task = await get_task(db, task_id)
    if not db_task:
        return None
    if not db_task.user_id == user_id:
        return "restricted"
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
    await db.delete(db_task)
    await db.commit()
    return db_task