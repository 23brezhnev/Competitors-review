from __future__ import annotations

"""Telegram collector — reads public channels via Telethon (MTProto).

First run is interactive: it asks for the phone code to create the session file
(TG_SESSION). Do this once locally, then copy the .session file to the server.
"""
import os
from datetime import datetime, timezone


def _channel(identifier: str) -> str:
    return identifier.rstrip("/").split("/")[-1].replace("@", "")


def fetch_telegram_posts(identifier: str, limit: int = 50) -> list[dict]:
    # Imported lazily and env read at call time: installations without any
    # Telegram source must not need telethon, and .env must already be loaded.
    from telethon.sync import TelegramClient

    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    session = os.getenv("TG_SESSION", "tg_session")
    if not api_id or not api_hash:
        raise RuntimeError("TG_API_ID / TG_API_HASH не заданы в .env")

    channel = _channel(identifier)
    posts: list[dict] = []
    with TelegramClient(session, api_id, api_hash) as client:
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
