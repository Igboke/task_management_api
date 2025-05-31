from httpx import AsyncClient
import pytest
from app.schemas import UserCreate, UserUpdate
import utils

@pytest.mark.anyio
async def test_create_user(client: AsyncClient, mocker):
    """
    Test user creation endpoint.
    Mocks the email sending functionality.
    """
    mock_send=mocker.patch("utils.send_verification_mail", return_value=None)

    user_data = {
        "email": "newuser@example.com",
        "password": "StrongPassword123",
    }
    response = await client.post("/api/v1/users/", json=user_data)

    assert response.status_code == 201
    created_user = response.json()
    assert created_user["email"] == user_data["email"]
    assert "id" in created_user
    assert "created_at" in created_user
    assert created_user["is_active"] is True
    assert created_user["is_verified"] is False # New users are not verified initially

    # Ensure email verification mail was attempted to be sent
    mock_send.assert_called_once()

@pytest.mark.anyio
async def test_create_user_email_already_exists(client: AsyncClient, mocker):
    """
    Test user creation with an email that already exists.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)
    
    user_data = {
        "email": "existinguser@example.com",
        "password": "Password123",
    }
    # Create the user first
    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201

    # Attempt to create with the same email again
    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists but is not verified. Please check your inbox for a verification link."