import smtplib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import HTTPException, status
from app.core.config import settings
from app.models import User as DBUser
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def send_verification_email(user: DBUser, db: AsyncSession):
    """
    Sends a verification email to the user with a verification link.
    The link includes a token that is valid for a limited time.
    """
    try:
        #generate a verification token
        token = secrets.token_urlsafe(32)
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
        user.verification_token = token
        user.verification_token_expires_at = expires_at 

        # Update the user in the database
        await db.commit()
        await db.refresh(user)



        # Construct the verification link
        verification_url = f"{settings.BASE_URL}/api/v1/verify-email?token={token}"

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

        # Gmail uses STARTTLS on port 587
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls() # Establish a secure encrypted connection

            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD) # Authenticate
            server.send_message(msg) # Send the constructed email message

        logger.info(f"Email verification link sent successfully to {user.email}")
        print(f"\n[DEV INFO] Verification link for {user.email}: {verification_url}\n")

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