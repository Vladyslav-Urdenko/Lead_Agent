import httpx
from app.core.config import settings

async def send_telegram_alert(message: str):
    """
    Sends a message to the configured Telegram chat.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        # Silently fail or log warning if not configured, to not break flow
        print("⚠️ Telegram config missing. Alert skipped.")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"❌ Telegram Send Error: {e}")
