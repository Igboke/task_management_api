from httpx import AsyncClient
import pytest
from datetime import datetime, timezone, timedelta
from app.schemas import TaskCreate, TaskStatus, TaskUpdate
from app.models import Task as DBTask
from app.crud import get_task as crud_get_task

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