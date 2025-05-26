from fastapi import APIRouter,Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.core.security import get_current_user
from app import crud, schemas
from app.database import get_db
from app.models import Task as DBTask , User as DBUser 

router = APIRouter()

@router.post("/{user_id}/", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(
    task_data: schemas.TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Create a new task.
    - :param task_data: The Pydantic model containing task creation data.
    - :param db: The database session to use for the operation.
    - :param current_user: The authenticated user object (injected by dependency).
    - :return: The created task as a SQLAlchemy model instance, serialized to TaskResponse schema.
    """
    try:
        # Check if the user exists
        existing_user = await crud.get_user(db,  current_user.id)
        if not existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        task = await crud.create_task(db, task_data, current_user.id)
        return task
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create task due to a database integrity constraint violation:{e}\n. Check input data."
        )
@router.get("/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
async def read_task_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) # PROTECTED: Requires a valid JWT
):
    """
    Retrieve a task by ID.
    - :param task_id: The ID of the task to retrieve.
    - :param db: The database session to use for the operation.
    - :param current_user: The authenticated user object (injected by dependency).
    - :return: The task as a SQLAlchemy model instance, serialized to TaskResponse schema.
    """
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this task")
    return task

@router.get("/user/{user_id}/", response_model=list[schemas.TaskResponse], status_code=status.HTTP_200_OK)
async def read_user_tasks_endpoint(
    user_id: int,
    status_: Optional[schemas.TaskStatus] = None,
    sort_by: Optional[str] = None,              
    order: Optional[str] = "asc",               
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve tasks for a specific user with pagination, filtering, and sorting.
    - :param user_id: The ID of the user whose tasks to retrieve.
    - :param status: Optional filter for task status (PENDING, IN_PROGRESS, COMPLETED).
    - :param sort_by: Optional field to sort tasks by (e.g., 'created_at', 'due_date', 'title').
    - :param order: Optional sort order ('asc' for ascending, 'desc' for descending). Default is 'asc'.
    - :param skip: The number of records to skip (for pagination).
    - :param limit: The maximum number of records to return.
    - :param db: The database session to use for the operation.
    - :return: A list of tasks as SQLAlchemy model instances, serialized to TaskResponse schema.
    """
    saved_user = await crud.get_user(db, user_id)
    if not saved_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    tasks = await crud.get_user_tasks(
        db, 
        user_id, 
        status_filter=status_,
        sort_by=sort_by, 
        order=order, 
        skip=skip, 
        limit=limit
    )
    return tasks


@router.put("{user_id}/{task_id}/", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
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
        db_task = await crud.get_task(db,task_id)
        if not db_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if not db_task.user_id == user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="User not authorized to update Task")

        updated_task = await crud.update_task(db,task_id, task_update)

        return updated_task
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not update task due to a database integrity constraint violation:{e}\n. Check input data."
        )
    
@router.delete("/{user_id}/{task_id}/delete/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(
    user_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db)
)->None:
    """
    Delete a task by ID.
    - :param user_id: The ID of the user to whom the task belongs (for validation).
    - :param task_id: The ID of the task to delete.
    - :param db: The database session to use for the operation.
    """
    db_task = await crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if db_task.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authorized to delete Task")
    await crud.delete_task(db, task_id)    
    return None
    
    
    

#how can i send prompts when a task reaches the due date