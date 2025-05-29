from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
import smtplib
from fastapi import HTTPException, status
from app.core.config import settings
from app.models import User as DbUser
from email.message import EmailMessage
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    - :param password: The plain text password to hash.
    - :return: The hashed password as a string.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    - :param plain_password: The plain text password to verify.
    - :param hashed_password: The hashed password to verify against.
    - :return: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

async def send_verification_mail(user:DbUser,verification_url:str) -> None:
    """
    Sends a verification email to the user with a verification link.
    The link includes a token that is valid for a limited time.
    """
    try:

        # Create the email message
        msg = EmailMessage()
        msg['Subject'] = "Verify your Task Manager Account"
        msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg['To'] = user.email
        
        email_body = f"""
        Hello {user.email},

        Thank you for registering with Task Manager API!
        Please click on the link below to verify your email address:

        {verification_url}

        This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

        If you did not register for this account, please ignore this email.

        Best regards,
        The Task Manager Team
        """
        msg.set_content(email_body)

        # Send the email using SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls() 
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

    except smtplib.SMTPAuthenticationError:
        logger.error(f"Failed to authenticate with SMTP server for {user.email}. Check SMTP_USERNAME and SMTP_PASSWORD in .env. Ensure App Password is enabled if using Gmail.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email due to SMTP authentication error."
        )
    except smtplib.SMTPConnectError as e:
        logger.error(f"Failed to connect to SMTP server: {e}. Check SMTP_HOST and SMTP_PORT.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to email server."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email to {user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending verification email."
        )
    