"""VK collector — public group walls via the official API (wall.get)."""
import os
from datetime import datetime, timezone

import requests

VK_API = "https://api.vk.com/method"
VK_VERSION = "5.199"


def _domain(identifier: str) -> str:
    # accepts "https://vk.com/xxx", "vk.com/xxx" or bare "xxx"
    return identifier.rstrip("/").split("/")[-1]


def fetch_vk_posts(identifier: str, token: str | None = None, count: int = 50) -> list[dict]:
    token = token or os.getenv("VK_SERVICE_TOKEN")
    resp = requests.get(
        f"{VK_API}/wall.get",
        params={
            "domain": _domain(identifier),
            "count": count,
            "access_token": token,
            "v": VK_VERSION,
        },
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API error: {data['error'].get('error_msg')}")

    posts = []
    for it in data.get("response", {}).get("items", []):
        posts.append(
            {
                "external_id": str(it["id"]),
                "text": it.get("text", ""),
                "published_at": datetime.fromtimestamp(it["date"], tz=timezone.utc),
                "url": f"https://vk.com/wall{it['owner_id']}_{it['id']}",
                "raw": {
                    "likes": it.get("likes", {}).get("count"),
                    "views": it.get("views", {}).get("count"),
                },
            }
        )
    return posts
