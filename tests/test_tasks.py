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