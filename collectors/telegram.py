from __future__ import annotations

"""Telegram collector — public channels via the t.me web preview.

No credentials and no session file: t.me/s/<channel> renders recent posts as
plain HTML. That keeps the collector serverless-friendly (Telethon needs a
persistent session file, which ephemeral filesystems cannot provide).

Limitation: public channels only, and history is walked backwards page by page.
"""
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CompetitorMonitor/1.0)"}
PAGE_SIZE_GUESS = 20  # t.me renders ~20 messages per page


def _channel(identifier: str) -> str:
    name = identifier.rstrip("/").split("/")[-1].replace("@", "")
    return name.replace("s/", "")


def fetch_telegram_posts(
    identifier: str, limit: int = 60, since: datetime | None = None
) -> list[dict]:
    """Walk back through the channel until `limit` posts or `since` is passed."""
    channel = _channel(identifier)
    posts: list[dict] = []
    seen: set[str] = set()
    before: str | None = None

    while len(posts) < limit:
        url = f"https://t.me/s/{channel}"
        params = {"before": before} if before else None
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        bubbles = soup.select("div.tgme_widget_message")
        if not bubbles:
            break

        oldest_id = None
        page_new = 0
        for node in bubbles:
            post = _parse_message(node, channel)
            if not post or post["external_id"] in seen:
                continue
            seen.add(post["external_id"])
            posts.append(post)
            page_new += 1
            msg_id = post["raw"].get("msg_id")
            if msg_id and (oldest_id is None or msg_id < oldest_id):
                oldest_id = msg_id

        # Stop once we've walked past the requested time window.
        if since:
            dated = [p["published_at"] for p in posts if p["published_at"]]
            if dated and min(dated) < since:
                break
        if not oldest_id or page_new == 0:
            break
        before = str(oldest_id)

    posts.sort(key=lambda p: p["published_at"] or datetime.min.replace(tzinfo=timezone.utc),
               reverse=True)
    return posts[:limit]


def _parse_message(node, channel: str) -> dict | None:
    data_post = node.get("data-post")  # "channel/123"
    if not data_post:
        return None
    msg_id = data_post.split("/")[-1]

    text_node = node.select_one("div.tgme_widget_message_text")
    text = " ".join(text_node.get_text(" ").split()) if text_node else ""
    if not text:
        return None  # media-only post, nothing to summarize

    time_node = node.select_one("time[datetime]")
    published = None
    if time_node:
        try:
            published = datetime.fromisoformat(time_node["datetime"]).astimezone(timezone.utc)
        except ValueError:
            published = None

    views_node = node.select_one("span.tgme_widget_message_views")
    return {
        "external_id": msg_id,
        "text": text,
        "published_at": published,
        "url": f"https://t.me/{channel}/{msg_id}",
        "raw": {
            "msg_id": int(msg_id) if msg_id.isdigit() else None,
            "views": views_node.get_text(strip=True) if views_node else None,
        },
    }
