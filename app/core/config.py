from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and a .env file.
    """
    # JWT Settings
    SECRET_KEY: str = "PlaceholderSecretKey"
    ALGORITHM: str = "HS256" # HMAC SHA256 algorithm for signing JWTs
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Access token validity period in minutes

    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24 # Email verification token validity period in hours
    BASE_URL: str = "http://127.0.0.1:8000" # Base URL for the application, used in email links

    EMAIL_FROM_ADDRESS: str = "danieligboke669@gmail.com"
    EMAIL_FROM_NAME: str = "Task Manager API"


    # Pydantic v2 configuration for loading from .env file
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore other environment variables not defined here
    )

settings = Settings()