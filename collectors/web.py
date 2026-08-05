from __future__ import annotations

"""Website collector — RSS when available, otherwise page change-detection.

For pages without RSS we hash the visible text; a new hash means the page
changed, which surfaces as a new "post". Set config {"rss": true} to force RSS.
"""
import hashlib
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CompetitorMonitor/1.0)"}


def fetch_web_posts(identifier: str, config: dict | None = None) -> list[dict]:
    config = config or {}
    is_rss = config.get("rss") or identifier.rstrip("/").endswith(("rss", ".xml", "/feed"))
    return _fetch_rss(identifier) if is_rss else _fetch_page_snapshot(identifier)


def _fetch_rss(url: str) -> list[dict]:
    # Fetch ourselves: feedparser's own User-Agent is blocked by many sites,
    # which would silently yield zero entries.
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    posts = []
    for e in feed.entries:
        published = None
        if getattr(e, "published_parsed", None):
            published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        summary = _strip_html(e.get("summary", ""))
        posts.append(
            {
                "external_id": e.get("id") or e.get("link") or e.get("title"),
                "text": f"{e.get('title', '')}\n{summary}".strip(),
                "published_at": published,
                "url": e.get("link"),
                "raw": {},
            }
        )
    return posts


def _strip_html(html: str) -> str:
    """RSS summaries often embed markup; the LLM only needs the prose."""
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    return " ".join(text.split())


def _fetch_page_snapshot(url: str) -> list[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return [
        {
            "external_id": digest,  # stable until the page content changes
            "text": text[:5000],
            "published_at": datetime.now(timezone.utc),
            "url": url,
            "raw": {"hash": digest},
        }
    ]
