from pydantic import BaseModel, Field

class User(BaseModel):
    id: int = Field(..., description="The unique identifier of the user")
    email: str = Field(..., description="The email address of the user")
    is_active: bool = Field(..., description="Indicates if the user is active")
    created_at: str = Field(..., description="The timestamp when the user was created")
    updated_at: str = Field(..., description="The timestamp when the user was last updated")
    tasks: list[int] = Field(..., description="List of task IDs associated with the user")

class Task(BaseModel):
    id: int = Field(..., description="The unique identifier of the task")
    title: str = Field(..., description="The title of the task")
    description: str = Field(None, description="A brief description of the task")
    status: str = Field(..., description="The current status of the task (e.g., PENDING, IN_PROGRESS, COMPLETED)")
    due_date: str = Field(None, description="The due date for the task")
    created_at: str = Field(..., description="The timestamp when the task was created")
    updated_at: str = Field(..., description="The timestamp when the task was last updated")
    user_id: int = Field(..., description="The ID of the user associated with the task")

class UserCreate(User):
    password: str = Field(..., description="The password for the user")

