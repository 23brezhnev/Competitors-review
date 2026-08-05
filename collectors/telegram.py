"""Telegram collector — reads public channels via Telethon (MTProto).

First run is interactive: it asks for the phone code to create the session file
(TG_SESSION). Do this once locally, then copy the .session file to the server.
"""
import os
from datetime import datetime, timezone

from telethon.sync import TelegramClient

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION = os.getenv("TG_SESSION", "tg_session")


def _channel(identifier: str) -> str:
    return identifier.rstrip("/").split("/")[-1].replace("@", "")


def fetch_telegram_posts(identifier: str, limit: int = 50) -> list[dict]:
    channel = _channel(identifier)
    posts: list[dict] = []
    with TelegramClient(SESSION, API_ID, API_HASH) as client:
        for msg in client.iter_messages(channel, limit=limit):
            if not msg.message:
                continue  # skip pure media / service messages
            posts.append(
                {
                    "external_id": str(msg.id),
                    "text": msg.message,
                    "published_at": msg.date.astimezone(timezone.utc),
                    "url": f"https://t.me/{channel}/{msg.id}",
                    "raw": {"views": msg.views, "forwards": msg.forwards},
                }
            )
    return posts
