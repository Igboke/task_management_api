from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and a .env file.
    """
    # JWT Settings
    SECRET_KEY: str = "PlaceholderSecretKey"
    ALGORITHM: str = "HS256" 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 

    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24 
    BASE_URL: str = "http://127.0.0.1:8000" 

    EMAIL_FROM_ADDRESS: str = "test134@gmail.com"
    EMAIL_FROM_NAME: str = "Task Manager API"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587 
    SMTP_USERNAME: str 
    SMTP_PASSWORD: str
    SMTP_USE_TLS: bool = True


    # Pydantic v2 configuration for loading from .env file
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore other environment variables not defined here
    )

settings = Settings()