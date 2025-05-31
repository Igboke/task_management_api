from httpx import AsyncClient
import pytest
from app.schemas import UserCreate, UserUpdate
import app.crud as crud
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

@pytest.mark.anyio
async def test_login_success(client: AsyncClient, db, mocker):
    """
    Test successful user login and token generation.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)

    # First, create a user and manually verify them in DB for login test
    password="loginpassword"
    user_data = UserCreate(email="login@example.com", password=password)
    db_user = await crud.create_user(db, user_data)
    db_user.is_verified = True # Manually verify for login test
    await db.commit()
    await db.refresh(db_user)

    login_form_data = {
        "username": user_data.email, # OAuth2PasswordRequestForm expects 'username'
        "password": password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = await client.post("/api/v1/auth/token", data=login_form_data,headers=headers)

    assert response.status_code == 200
    token_response = response.json()
    assert "access_token" in token_response
    assert token_response["token_type"] == "bearer"

@pytest.mark.anyio
async def test_login_invalid_credentials(client: AsyncClient, db, mocker):
    """
    Test user login with incorrect email or password.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)

    # Setup: Create a verified user for later tests of wrong password on existing user
    plain_password_correct = "CorrectPassword123" # Store plain password
    user_data = UserCreate(email="existing_login@example.com", password=plain_password_correct)
    db_user = await crud.create_user(db, user_data)
    db_user.is_verified = True
    await db.commit()
    await db.refresh(db_user)

    # Test 1: Non-existent email
    login_form_data_nonexistent = {
        "username": "nonexistent@example.com",
        "password": "wrongpassword",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = await client.post("/api/v1/auth/token", data=login_form_data_nonexistent, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

    # Test 2: Existing email, but wrong password
    login_form_data_wrong_pass = {
        "username": user_data.email, # Use the existing user's email
        "password": "wrongpassword", # Intentionally wrong password
    }
    response = await client.post("/api/v1/auth/token", data=login_form_data_wrong_pass, headers=headers)
    assert response.status_code == 418

