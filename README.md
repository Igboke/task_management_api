# FastAPI Task Management API

A simple yet robust CRUD (Create, Read, Update, Delete) API for managing user tasks. This project is built using FastAPI, SQLAlchemy 2.0 with asynchronous capabilities, and MySQL, following a standard and scalable project structure. It allows users to register, log in (authentication to be added), and manage their tasks efficiently.

---

## 🚀 Features

* **User Management:** Create, retrieve, update, and delete user accounts.
* **Task Management:** Create, retrieve, update, and delete tasks associated with users.
* **Task Status Tracking:** Tasks can have statuses like "Pending", "In Progress", and "Completed" (implemented as a Python `str` enum).
* **Secure Passwords:** User passwords are hashed using `bcrypt` for security.
* **Database Migrations:** Manage schema changes seamlessly with Alembic.
* **Asynchronous Operations:** Leverages Python's `async/await` for high-performance I/O operations (database interactions).
* **Data Validation & Serialization:** Utilizes Pydantic for robust request body validation and response serialization.
* **Interactive API Documentation:** Automatically generated OpenAPI (Swagger UI) documentation at `/docs`.
* **Structured Project:** Clean, modular, and scalable folder structure.

---

## 🛠️ Technologies Used

* **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Database:** [MySQL](https://www.mysql.com/)
* **Object-Relational Mapper (ORM):** [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
* **Asynchronous MySQL Driver:** [asyncmy](https://github.com/long2ice/asyncmy)
* **Data Validation:** [Pydantic](https://pydantic.dev/)
* **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/en/latest/)
* **Password Hashing:** [Passlib](https://passlib.readthedocs.io/en/stable/) (with bcrypt)
* **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)
* **Environment Variables:** [python-dotenv](https://pypi.org/project/python-dotenv/)
* **Dependency Management:** [`uv`](https://github.com/astral-sh/uv)
* **Testing Framework:** [Pytest](https://pytest.org/)

---

## ⚙️ Setup Instructions

Follow these steps to get the project up and running on your local machine.

### Prerequisites

* **Python 3.12+**
* **XAMPP** (Recommended for running MySQL locally)
* **Git:** (For cloning the repository)

### 1. Clone the Repository

```bash
git clone https://github.com/igboke/task_management_api.git
cd task_management_api
```

---

### 2. Set Up a Virtual Environment

It's crucial to use a virtual environment to manage project dependencies.

`Using uv`

```bash
uv venv
source .venv/bin/activate
```

`Or using standard venv`

```bash
python -m venv .venv
source .venv/bin/activate
```

---

### 3. Install dependcies

`using uv`

```bash
uv sync
```

`alternatively using pip`

```bash
uv pip freeze > requirements.txt
pip install -r requirements.txt
```

```bash
pip install -e . # Installs your project and its dependencies from pyproject.toml
```

---

### 4. Configure Environment Variables

Create a .env file in the root of your project (task_management_api/.env) and add your MySQL database connection details:

```env
# .env
DB_USER=root
DB_PASSWORD=your_root_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=task_manager         # Ensure this matches the database name you use
```

**Make sure your MySQL server is running and the database specified in DB_NAME exists.**

---

### 5. Run Database Migrations (using Alembic)

#### Generate migration script

```bash
alembic revision --autogenerate -m "Create user and task tables"
```

#### Apply migration

```bash
alembic upgrade head
```

### 6. Start the FastAPI Application

```bash
uvicorn app.main:main --reload
```

The API will now be running locally. The --reload flag will automatically restart the server when you make changes to your code (useful during development).

The API will be accessible at [local](http://127.0.0.1:8000).

### 7. Access API Documentation

[Swagger UI](http://127.0.0.1:8000/docs)
[ReDoc](http://127.0.0.1:8000/redoc)

### 8. Endpoints

#### Users

* Create User: POST /api/v1/users/
  -Request Body:

    ```json
    {
      "email": "example@email.com",
      "password": "password",
    }
    ```

  -Response:

    ```json
    {
      "id": 1,
      "email": "example@email.com",
      "is_active": true,
      "created_at": "2025-05-25T18:49:46.112Z",
      "updated_at": "2025-05-25T18:49:46.112Z"
    }
    ```

* Get User by ID: GET /api/v1/users/{user_id}
    -Response:

    ```json
        {
        "email": "user@example.com",
        "id": 0,
        "is_active": true,
        "created_at": "2025-05-25T18:58:43.352Z",
        "updated_at": "2025-05-25T18:58:43.353Z"
        }
    ```

* Get All Users: GET /api/v1/users/
    -Response:

    ```json
        [
        {
        "email": "user@example.com",
        "id": 0,
        "is_active": true,
        "created_at": "2025-05-25T19:00:55.294Z",
        "updated_at": "2025-05-25T19:00:55.294Z"
        },
        ]
    ```

* Update User: PUT /api/v1/users/{user_id}
    -Request Body:

    ```json
    {
    "email": "user@example.com",
    "password": "stringst",
    "is_active": true
    }
    ```

    -Response:

    ```json
    {
    "email": "user@example.com",
    "id": 0,
    "is_active": true,
    "created_at": "2025-05-25T19:04:58.122Z",
    "updated_at": "2025-05-25T19:04:58.122Z"
    }
    ```

* Delete User: DELETE /api/v1/users/{user_id}
    -Response: 204 No Content

#### Tasks

* Create Task: POST /api/v1/tasks/{user_id}/create/
    -Request Body:

    ```json
        {
        "title": "string",
        "description": "string",
        "status": "pending",
        "due_date": "2025-05-25T18:49:42.371Z"
        }
    ```

    -Response:

    ```json
        {
        "title": "string",
        "description": "string",
        "status": "pending",
        "due_date": "2025-05-25T19:08:42.805Z",
        "id": 0,
        "created_at": "2025-05-25T19:08:42.805Z",
        "updated_at": "2025-05-25T19:08:42.805Z",
        "user_id": 0
        }
    ```

*(Planned) Get Task by ID: GET /api/v1/tasks/{task_id}
*(Planned) Get User Tasks: GET /api/v1/users/{user_id}/tasks/
*(Planned) Update Task: PUT /api/v1/tasks/{task_id}
*(Planned) Delete Task: DELETE /api/v1/tasks/{task_id}
