from fastapi import APIRouter,Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app import crud, schemas
from app.database import get_db
from app.models import Task as DBTask  

router = APIRouter()

@router.post("/{user_id}/create/", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(
    user_id: int,
    task_data: schemas.TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task.
    - :param task_data: The Pydantic model containing task creation data.
    - :param db: The database session to use for the operation.
    - :return: The created task as a SQLAlchemy model instance, serialized to TaskResponse schema.
    """
    try:
        # Check if the user exists
        existing_user = await crud.get_user(db, user_id)
        if not existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        task = await crud.create_task(db, task_data, user_id)
        return task
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create task due to a database integrity constraint violation:{e}\n. Check input data."
        )
@router.get("/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
async def read_task_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a task by ID.
    - :param task_id: The ID of the task to retrieve.
    - :param db: The database session to use for the operation.
    - :return: The task as a SQLAlchemy model instance, serialized to TaskResponse schema.
    """
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task