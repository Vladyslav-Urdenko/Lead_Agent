import os
import aiosmtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
GO_LIVE = os.getenv("GO_LIVE", "false").lower() == "true"

async def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using aiosmtplib if GO_LIVE is True.
    Otherwise, prints to console (Safety Mode).
    """
    if not GO_LIVE:
        print("\n[SAFETY MODE] Email not sent. Here is the preview:")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("-" * 20)
        print(body)
        print("-" * 20)
        return True

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        print(f"🚀 Connecting to SMTP: {SMTP_HOST}:{SMTP_PORT}...")
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
        )
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
