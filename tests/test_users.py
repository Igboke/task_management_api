from httpx import AsyncClient
import pytest
from app.schemas import UserCreate, UserUpdate
import app.crud as crud
import utils
from app.core.security import create_email_verification_access_token
from app.crud import get_user_by_email

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

@pytest.mark.anyio
async def test_login_unverified_email(client: AsyncClient, db, mocker):
    """
    Test user login with an unverified email.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)

    # Create a user but do NOT verify them
    unverified_password:str = "unverifiedpassword"
    user_data = UserCreate(email="unverified@example.com", password=unverified_password)
    await crud.create_user(db, user_data) # This user will remain unverified

    login_form_data = {
        "username": user_data.email,
        "password": unverified_password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = await client.post("/api/v1/auth/token", data=login_form_data, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified. Please check your inbox for a verification link."

@pytest.mark.anyio
async def test_verify_email_success(client: AsyncClient, db, mocker):
    """
    Test email verification endpoint with a valid token.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)

    #Create a user (will be unverified)
    user_data = {"email": "verify@example.com", "password": "VerificationPassword123"}
    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    created_user = response.json()
    
    #Directly generate a valid verification token for the created user In a real scenario, this token would come from the email sent by the /users/ endpoint.
    
    db_user = await get_user_by_email(db, created_user["email"])
    verification_token = await create_email_verification_access_token(db_user)

    #Call the verification endpoint with the token
    response = await client.get(f"/api/v1/auth/verify_email/{verification_token}")
    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully! You can now log in."

    #Verify user status in the database
    updated_user = await get_user_by_email(db, created_user["email"])
    assert updated_user.is_verified is True

@pytest.mark.anyio
async def test_verify_email_invalid_token(client: AsyncClient):
    """
    Test email verification with an invalid token.
    """
    response = await client.get("/api/v1/auth/verify_email/invalidtoken")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification link."

@pytest.mark.anyio
async def test_read_current_user(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving the currently authenticated user's profile.
    """
    user, headers = authenticated_user_and_headers
    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    current_user_data = response.json()
    assert current_user_data["email"] == user.email
    assert current_user_data["id"] == user.id
    assert current_user_data["is_verified"] is True

@pytest.mark.anyio
async def test_read_user_by_id_self(client: AsyncClient, authenticated_user_and_headers):
    """
    Test retrieving a user's profile by ID for the authenticated user themselves.
    """
    user, headers = authenticated_user_and_headers
    response = await client.get(f"/api/v1/users/{user.id}", headers=headers)

    assert response.status_code == 200
    retrieved_user_data = response.json()
    assert retrieved_user_data["email"] == user.email
    assert retrieved_user_data["id"] == user.id

@pytest.mark.anyio
async def test_read_user_by_id_unauthorized(client: AsyncClient, authenticated_user_and_headers, db, mocker):
    """
    Test attempting to retrieve another user's profile by ID.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)
    #header with bearer token
    _, headers = authenticated_user_and_headers

    # Create a second user
    second_user_data = UserCreate(email="another@example.com", password="AnotherPassword")
    second_db_user = await crud.create_user(db, second_user_data)
    second_db_user.is_verified = True
    await db.commit()
    await db.refresh(second_db_user)

    response = await client.get(f"/api/v1/users/{second_db_user.id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view this user's profile"

@pytest.mark.anyio
async def test_read_all_users(client: AsyncClient, db, authenticated_user_and_headers, mocker):
    """
    Test retrieving a list of all users.
    API allows any authenticated user to list all users.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)
    #header with bearer token contains the creation of the first user
    _, headers = authenticated_user_and_headers

    # Create a second user
    second_user_data = UserCreate(email="second@example.com", password="SecondPassword")
    second_db_user = await crud.create_user(db, second_user_data)
    second_db_user.is_verified = True
    await db.commit()
    await db.refresh(second_db_user)

    response = await client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2

    emails = {u["email"] for u in users}
    assert "authenticated@example.com" in emails
    assert "second@example.com" in emails

    #no authentication headers are required for this endpoint
    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2

    emails = {u["email"] for u in users}
    assert "authenticated@example.com" in emails
    assert "second@example.com" in emails

@pytest.mark.anyio
async def test_update_user_success(client: AsyncClient, authenticated_user_and_headers):
    """
    Test successful update of the authenticated user's profile.
    """
    user, headers = authenticated_user_and_headers
    update_data = {
        "email": "updated@example.com",
        "is_active": False,
    }
    response = await client.put(f"/api/v1/users/{user.id}", json=update_data, headers=headers)

    assert response.status_code == 200
    updated_user_data = response.json()
    assert updated_user_data["email"] == update_data["email"]
    assert updated_user_data["is_active"] == update_data["is_active"]
    assert updated_user_data["id"] == user.id

@pytest.mark.anyio
async def test_update_user_unauthorized(client: AsyncClient, authenticated_user_and_headers, db, mocker):
    """
    Test attempting to update another user's profile.
    """
    mocker.patch("utils.send_verification_mail", return_value=None)
    _, headers = authenticated_user_and_headers

    # Create a second user
    second_user_data = UserCreate(email="another_to_update@example.com", password="UpdatePassword")
    second_db_user = await crud.create_user(db, second_user_data)
    second_db_user.is_verified = True
    await db.commit()
    await db.refresh(second_db_user)

    update_data = {"email": "malicious_update@example.com"}
    response = await client.put(f"/api/v1/users/{second_db_user.id}", json=update_data, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this user"


