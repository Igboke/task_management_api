from dotenv import load_dotenv
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

#create asynchronous engine
#echo=True enables logging of all the SQL statements for debugging purposes
#pool_pre_ping=True ensures that connections are checked before being used, which is useful for long-lived connections
engine = create_async_engine(SQLALCHEMY_DATABASE_URL,echo=True,pool_pre_ping=True)

#sessionmaker is a factory for creating new Session objects
#this is the conversation space/room for interating with database before committing changes. this is like the waiting room where commands happen
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

#similar to django models.Model, the Base class will be inherited by all Models(tables)
Base = declarative_base()

#dependency to get the session
async def get_db():
    """
    This is is a dependency that will be used by endpoints to get a database session.
    It will be used in the FastAPI endpoints to get a session for each request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()



