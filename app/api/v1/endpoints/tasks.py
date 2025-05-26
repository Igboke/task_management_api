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

@router.get("/{user_id}/tasks/", response_model=list[schemas.TaskResponse], status_code=status.HTTP_200_OK)
async def read_user_tasks_endpoint(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve tasks for a specific user with pagination.
    - :param user_id: The ID of the user whose tasks to retrieve.
    - :param skip: The number of records to skip (for pagination).
    - :param limit: The maximum number of records to return.
    - :param db: The database session to use for the operation.
    - :return: A list of tasks as SQLAlchemy model instances, serialized to TaskResponse schema.
    """
    saved_user = await crud.get_user(db, user_id)
    if not saved_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    tasks = await crud.get_user_tasks(db, user_id, skip, limit)
    return tasks

@router.put("{user_id}/{task_id}/update/", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
async def update_task_endpoint(
    user_id:int,
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing task.
    - :param user_id: The ID of the user to whom the task belongs (for validation).
    - :param task_id: The ID of the task to update.
    - :param task_update: The Pydantic model containing task update data.
    - :param db: The database session to use for the operation.
    - :return: The updated task as a SQLAlchemy model instance, serialized to TaskResponse schema.
    """
    try:
        updated_task = await crud.update_task(db,user_id,task_id, task_update)
        if updated_task == "restricted":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not authorized to update Task")
        elif not updated_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return updated_task
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not update task due to a database integrity constraint violation:{e}\n. Check input data."
        )
    
@router.delete("/{user_id}/{task_id}/delete/", status_code=status.HTTP_200_OK)
async def delete_task_endpoint(
    user_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db)
)->dict[str, str]:
    """
    Delete a task by ID.
    - :param user_id: The ID of the user to whom the task belongs (for validation).
    - :param task_id: The ID of the task to delete.
    - :param db: The database session to use for the operation.
    """
    result = await crud.delete_task(db,user_id, task_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    elif result == "restricted":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to delete Task")
    return {"message": "Task deleted successfully"}
    
    
    

#how can i send prompts when a task reaches the due date
#sorting tasks according the task.status