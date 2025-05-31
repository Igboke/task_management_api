import asyncio
from httpx import AsyncClient
import pytest
from datetime import datetime, timezone, timedelta
from app.schemas import TaskCreate, TaskStatus
from app.models import Task as DBTask
from app.crud import get_task as crud_get_task, create_task as crud_create_task
from app.schemas import UserCreate
from app.crud import create_user as crud_create_user

@pytest.mark.anyio
async def test_create_task(client: AsyncClient, authenticated_user_and_headers):
    """
    Test creating a task for an authenticated user.
    This test checks if a user can successfully create a task with valid data.
    It verifies that the task is created with the correct attributes and returns a 201 status code.
    """
    user, headers = authenticated_user_and_headers
    task_data = {
        "title": "Buy food",
        "description": "Milk, Eggs, Bread",
        "status": "pending",
        "due_date": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)

    assert response.status_code == 201
    created_task = response.json()
    assert created_task["title"] == task_data["title"]
    assert created_task["user_id"] == user.id
    assert created_task["status"] == TaskStatus.PENDING.value
    assert "id" in created_task

@pytest.mark.anyio
async def test_create_task_unauthenticated(client: AsyncClient):
    """
    Test creating a task without authentication.
    """
    task_data = {
        "title": "Unauthorized Task",
        "description": "This Should fail",
        "status": "pending",
        "due_date": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == 401 # Unauthorized

@pytest.mark.anyio
async def test_read_task_by_id_success(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving a task by ID for the owner.
    """
    user, headers = authenticated_user_and_headers
    task_data = {
        "title": "My specific task",
        "description": "Details for my task",
        "status": "in progress",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    create_response = await client.post("/api/v1/tasks/", json=task_data, headers=headers)
    assert create_response.status_code == 201
    created_task_id = create_response.json()["id"]

    read_response = await client.get(f"/api/v1/tasks/{created_task_id}", headers=headers)
    assert read_response.status_code == 200
    read_task = read_response.json()
    assert read_task["id"] == created_task_id
    assert read_task["title"] == task_data["title"]
    assert read_task["user_id"] == user.id

@pytest.mark.anyio
async def test_read_task_by_id_not_found(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving a non-existent task.
    """
    _, headers = authenticated_user_and_headers
    response = await client.get("/api/v1/tasks/99999", headers=headers) # Non-existent ID
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

@pytest.mark.anyio
async def test_read_task_by_id_forbidden(client: AsyncClient, authenticated_user_and_headers, db):
    """
    Test attempting to retrieve another user's task.
    """
    _, headers_owner = authenticated_user_and_headers

    # Create a second user
    other_user_data = UserCreate(email="other@example.com", password="OtherUserPass")
    other_db_user = await crud_create_user(db, other_user_data)
    other_db_user.is_verified = True
    await db.commit()
    await db.refresh(other_db_user)

    # Create a task for the other user
    task_for_other_user_data = {
        "title": "Other user's private task",
        "description": "Don't touch!",
        "status": "pending",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
    }
    # Simulate other user creating a task by directly calling crud
    other_task = await crud_create_task(db, TaskCreate(**task_for_other_user_data), other_db_user.id)

    # Now, the user with token tries to access 'other_task'
    response = await client.get(f"/api/v1/tasks/{other_task.id}", headers=headers_owner)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this task"

@pytest.mark.anyio
async def test_read_user_tasks_no_filter(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving all tasks for the authenticated user without filters.
    """
    user, headers = authenticated_user_and_headers
    # Create multiple tasks for the user
    for i in range(3):
        task_data = {
            "title": f"Task {i}",
            "description": f"Description for task {i}",
            "status": "pending" if i % 2 == 0 else "completed",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=i)).isoformat(),
        }
        await client.post("/api/v1/tasks/", json=task_data, headers=headers)

    response = await client.get("/api/v1/tasks/", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3
    assert all(task["user_id"] == user.id for task in tasks)

@pytest.mark.anyio
async def test_read_user_tasks_with_status_filter(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving tasks filtered by status.
    """
    _, headers = authenticated_user_and_headers
    # Create tasks with different statuses
    await client.post("/api/v1/tasks/", json={"title": "Pending Task 1", "status": "pending"}, headers=headers)
    await client.post("/api/v1/tasks/", json={"title": "Completed Task 1", "status": "completed"}, headers=headers)
    await client.post("/api/v1/tasks/", json={"title": "Pending Task 2", "status": "pending"}, headers=headers)

    response = await client.get("/api/v1/tasks/?status_=pending", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert all(task["status"] == "pending" for task in tasks)

@pytest.mark.anyio
async def test_read_user_tasks_with_sorting(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving tasks with sorting by 'created_at' in descending order.
    """
    _, headers = authenticated_user_and_headers
    
    # Create tasks with delays to ensure different created_at timestamps
    task1_data = {"title": "Task A", "description": "Desc A"}
    await client.post("/api/v1/tasks/", json=task1_data, headers=headers)
    await asyncio.sleep(0.01) # Small delay
    task2_data = {"title": "Task B", "description": "Desc B"}
    await client.post("/api/v1/tasks/", json=task2_data, headers=headers)

    # Retrieve tasks sorted by created_at descending
    response = await client.get("/api/v1/tasks/?sort_by=created_at&order=desc", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    # Task B should be first due to 'desc' order and later creation
    assert tasks[0]["title"] == "Task B"
    assert tasks[1]["title"] == "Task A"

@pytest.mark.anyio
async def test_update_task_success(client: AsyncClient, authenticated_user_and_headers):
    """
    Test updating an existing task owned by the authenticated user.
    This test checks if a user can successfully update a task with valid data.
    It verifies that the task is updated with the new attributes and returns a 200 status code.
    """
    _, headers = authenticated_user_and_headers
    create_task_data = {
        "title": "Task to Update",
        "description": "Initial description",
        "status": "pending",
        "due_date": datetime.now(timezone.utc).isoformat(),
    }
    create_response = await client.post("/api/v1/tasks/", json=create_task_data, headers=headers)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    update_task_data = {
        "title": "Updated Task Title",
        "description": "New description",
        "status": "completed",
    }
    update_response = await client.put(f"/api/v1/tasks/{task_id}", json=update_task_data, headers=headers)
    assert update_response.status_code == 200
    updated_task = update_response.json()
    assert updated_task["id"] == task_id
    assert updated_task["title"] == update_task_data["title"]
    assert updated_task["description"] == update_task_data["description"]
    assert updated_task["status"] == update_task_data["status"]
    assert updated_task["updated_at"] > updated_task["created_at"] # Updated timestamp should be newer