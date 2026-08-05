"""Send the report to a Telegram chat via the Bot API."""
import os

import requests

TG_LIMIT = 4000  # Telegram hard limit is 4096; leave headroom


def _split(text: str, limit: int = TG_LIMIT) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    return chunks


def send_telegram(text: str, token: str | None = None, chat_id: str | None = None) -> None:
    token = token or os.getenv("TG_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TG_CHAT_ID")
    for chunk in _split(text):
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
            timeout=30,
        )
        resp.raise_for_status()
