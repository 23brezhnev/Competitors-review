"""App-store collectors — Google Play and Apple App Store reviews + metrics.

Each returns (snapshot, reviews):
    snapshot: dict of current metrics -> stored as AppSnapshot (for dynamics)
    reviews:  list of individual reviews -> deduped into Review
"""
from datetime import timezone

import requests


def fetch_googleplay(app_id: str, lang: str = "ru", country: str = "ru", count: int = 100):
    from google_play_scraper import Sort, app as gp_app, reviews as gp_reviews

    info = gp_app(app_id, lang=lang, country=country)
    result, _ = gp_reviews(app_id, lang=lang, country=country, count=count, sort=Sort.NEWEST)

    revs = [
        {
            "external_id": r["reviewId"],
            "author": r.get("userName"),
            "rating": r.get("score"),
            "title": None,
            "text": r.get("content"),
            "published_at": r["at"].replace(tzinfo=timezone.utc) if r.get("at") else None,
        }
        for r in result
    ]
    hist = info.get("histogram") or []
    snapshot = {
        "avg_rating": info.get("score"),
        "ratings_count": info.get("ratings"),
        "reviews_count": info.get("reviews"),
        "histogram": {str(i + 1): hist[i] for i in range(len(hist))} if hist else None,
    }
    return snapshot, revs


def fetch_appstore(app_id: str, country: str = "ru", pages: int = 3):
    """Apple RSS reviews feed (most recent). No key required; ~500 recent max."""
    revs = []
    for page in range(1, pages + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={app_id}/sortby=mostrecent/json"
        )
        data = requests.get(url, timeout=30).json()
        for e in data.get("feed", {}).get("entry", []):
            if "im:rating" not in e:  # the first entry is app metadata, skip it
                continue
            revs.append(
                {
                    "external_id": e["id"]["label"],
                    "author": e.get("author", {}).get("name", {}).get("label"),
                    "rating": int(e["im:rating"]["label"]),
                    "title": e.get("title", {}).get("label"),
                    "text": e.get("content", {}).get("label"),
                    "published_at": None,
                }
            )
    snapshot = {
        "avg_rating": None,       # Apple RSS doesn't expose the aggregate score
        "ratings_count": None,
        "reviews_count": len(revs),
        "histogram": None,
    }
    return snapshot, revs
