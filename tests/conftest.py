import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.schemas import UserCreate
from app.core.security import create_access_token
from app.crud import create_user as crud_create_user

# Define a test database URL using SQLite in-memory for speed and isolation
# Using `sqlite+aiosqlite:///:memory:` means the database exists only in RAM
# and is reset for each test session, providing a clean slate.
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# This fixture is required by pytest-asyncio to enable running async tests
@pytest.fixture(scope="session")
def anyio_backend():
    """
    Specifies the AnyIO backend for pytest-asyncio.
    Using "asyncio" is standard for FastAPI applications.
    """
    return "asyncio"

@pytest.fixture(scope="session")
async def test_engine():
    """
    Creates an asynchronous SQLAlchemy engine for the test database.
    The `echo=False` prevents logging SQL statements during tests for cleaner output.
    """
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    yield engine
    # Dispose of the engine after all tests in the session are done
    await engine.dispose()

@pytest.fixture(scope="session")
async def test_session_maker(test_engine):
    """
    Creates a sessionmaker factory for producing AsyncSession objects.
    `expire_on_commit=False` is important for allowing access to attributes
    on ORM objects after they've been committed, which is common in tests.
    """
    session_maker = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    return session_maker

@pytest.fixture(scope="function", autouse=True)
async def db(test_engine, test_session_maker):
    """
    Provides a clean, isolated database session for each test function.
    This fixture ensures:
    1.  Tables are dropped and recreated before each test, ensuring a clean slate.
    2.  A new AsyncSession is yielded for the test to interact with the database.
    3.  The session is rolled back after each test completes, undoing any changes.
    This isolation prevents tests from affecting each other's data.
    """
    async with test_engine.begin() as conn:
        # Drop all tables and recreate them for each test function
        # This ensures a clean slate for every test.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_maker() as session:
        yield session
        # Rollback the session after each test to ensure isolation
        await session.rollback()

@pytest.fixture(scope="function")
async def client(db: AsyncSession):
    """
    Provides a FastAPI TestClient that overrides the get_db dependency
    to use the test database session. This allows tests to interact with
    the FastAPI application using the test database.
    """
    async def override_get_db():
        """
        Override the default get_db dependency to use an in-memory SQLite database for testing.
        This function provides an AsyncSession that can be used in tests.
        """
        yield db
    # Override the get_db dependency to use the test session provided by the `db` fixture
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Clean up the dependency override after the test finishes
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def authenticated_user_and_headers(db: AsyncSession):
    """
    Fixture to quickly create a user, mark them as verified, and return their
    database object along with authentication headers. This is useful for tests
    that require an authenticated user without going through the full registration
    and verification flow.
    """
    user_data = UserCreate(email="authenticated@example.com", password="SecurePassword123")

    # Directly create user via CRUD function and mark as verified
    # This bypasses the email sending part for test setup
    db_user = await crud_create_user(db, user_data)
    
    # Mark user as verified directly in the database for simplicity in test setup
    db_user.is_verified = True
    await db.commit()
    await db.refresh(db_user) # Refresh to ensure the object reflects the committed changes

    # Create an access token for this user
    token = create_access_token(data={"sub": db_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    return db_user, headers