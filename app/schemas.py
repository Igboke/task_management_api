from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import enum 

# Define an enumeration for task status
class TaskStatus(str,enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"

class UserBase(BaseModel):
    """
    Base schema for user attributes
    - email: required field with validation as an email address
    """
    email: EmailStr = Field(..., description="The email address of the user")

class UserCreate(UserBase):
    """
    Schema for creating a new user (request body)
    inherits from UserBase and adds password field
    - UserBase: email field is required and validated as an email address
    - password: required field with a minimum length of 8 characters
    """
    password: str = Field(..., min_length=8, description="The password for the user")


class UserUpdate(UserBase):
    """
    Schema for updating an existing user (request body)
    This schema allows partial updates to user information.
    - UserBase: inherits email field which is optional here
    - password: optional field with a minimum length of 8 characters
    - is_active: optional boolean field to indicate if the user account is active
    """
    email: Optional[EmailStr] = Field(None, description="The updated email address of the user")
    password: Optional[str] = Field(None, min_length=8, description="The updated password for the user")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")


# Schema for returning a user (response model) This MUST match the fields in your app.models.User that you want to expose
class UserResponse(UserBase):
    """
    Schema for returning a user (response model)
    This MUST match the fields in your app.models.User that you want to expose
    because we are returning the entire user after creating it in curd
    This schema is used to serialize user data for API responses.
    - UserBase: inherits email field which is required
    - id: unique identifier of the user
    - is_active: boolean indicating if the user account is active
    - created_at: timestamp when the user was created
    - updated_at: timestamp when the user was last updated
    """
    id: int = Field(..., description="The unique identifier of the user")
    is_active: bool = Field(True, description="Whether the user account is active")
    is_verified: bool = Field(False, description="Whether the user's email address has been verified")
    created_at: datetime = Field(..., description="The timestamp when the user was created")
    updated_at: datetime = Field(..., description="The timestamp when the user was last updated")

    # This configuration tells Pydantic to read data from ORM model attributes, rather than expecting a dict, allowing it to work with SQLAlchemy model instances.
    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    """
    This is the base schema for task attributes.
    It defines the common fields that will be used in both creating and updating tasks.
    - title: required field with a minimum length of 1 character
    - description: optional field for a brief description of the task
    - status: optional field with a default value of TaskStatus.PENDING
    - due_date: optional field for the due date of the task
    """
    title: str = Field(..., description="The title of the task", min_length=1)
    description: Optional[str] = Field(None, description="A brief description of the task")
    status: TaskStatus = Field(TaskStatus.PENDING, description="The current status of the task")
    due_date: Optional[datetime] = Field(None, description="The due date for the task")

class TaskCreate(TaskBase):
    """
    Schema for creating a new task (request body)
    This schema inherits from TaskBase and does not add any new fields.
    It is used to validate the data when creating a new task.
    - title: required field with a minimum length of 1 character
    - description: optional field for a brief description of the task
    - status: optional field with a default value of TaskStatus.PENDING
    - due_date: optional field for the due date of the task
    """
    pass

class TaskUpdate(TaskBase):
    """
    Schema for updating an existing task (request body)
    This schema inherits from TaskBase and allows partial updates to task information.
    - title: optional field with a minimum length of 1 character
    - description: optional field for a brief description of the task
    - status: optional field to update the current status of the task
    - due_date: optional field to update the due date for the task
    """
    title: Optional[str] = Field(None, description="The updated title of the task", min_length=1)
    description: Optional[str] = Field(None, description="The updated description of the task")
    status: Optional[TaskStatus] = Field(None, description="The updated status of the task")
    due_date: Optional[datetime] = Field(None, description="The updated due date for the task")


class TaskResponse(TaskBase):
    """
    Schema for returning a task (response model) Schema for returning a task (response model) This MUST match the fields in your app.models.Task that you want to expose
    This schema is used to serialize task data for API responses.
    **TaskBase <inherits all fields from TaskBase>**:
    - id: unique identifier of the task
    - created_at: timestamp when the task was created
    - updated_at: timestamp when the task was last updated
    - user_id: ID of the user to whom the task belongs
    """
    id: int = Field(..., description="The unique identifier of the task")
    created_at: datetime = Field(..., description="The timestamp when the task was created")
    updated_at: datetime = Field(..., description="The timestamp when the task was last updated")
    user_id: int = Field(..., description="The ID of the user to whom the task belongs")

    class Config:
        from_attributes = True

#JWT Token Schemas
class Token(BaseModel):
    """
    Schema for the response model when a user successfully logs in.
    Contains the generated access token and its type.
    """
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field("bearer", description="The type of token, typically 'bearer'")

class TokenData(BaseModel):
    """
    Schema for the data payload expected within the JWT itself.
    The 'sub' (subject) claim typically holds a unique identifier for the user.
    """
    email: Optional[EmailStr] = Field(None, description="The email address (subject) extracted from the token")