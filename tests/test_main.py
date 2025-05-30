from httpx import AsyncClient
import pytest

# The 'client' fixture is automatically provided by conftest.py
# It sets up a TestClient for your FastAPI application using the test database.

@pytest.mark.anyio # Mark the test as an AnyIO test
async def test_root_endpoint(client: AsyncClient):
    """
    Test the root health check endpoint to ensure it returns the expected message.
    """
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI TaskManager API! Go to /docs for API documentation."}