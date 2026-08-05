from __future__ import annotations

"""App-store collectors — Google Play and Apple App Store reviews + metrics.

Each returns (snapshot, reviews):
    snapshot: dict of current metrics -> stored as AppSnapshot (for dynamics)
    reviews:  list of individual reviews -> deduped into Review
"""
from datetime import datetime, timezone

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
    """Apple App Store: aggregate metrics via the Lookup API, reviews via the RSS feed.

    The RSS feed carries only recent reviews (~500 max) and no aggregate score,
    so the average rating comes from the Lookup API — that is what makes the
    week-over-week rating delta possible.
    """
    revs = []
    for page in range(1, pages + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={app_id}/sortby=mostrecent/json"
        )
        data = requests.get(url, timeout=30).json()
        entries = data.get("feed", {}).get("entry") or []
        if not entries:
            break  # no reviews in this store, or no more pages
        for e in entries:
            if "im:rating" not in e:  # the first entry can be app metadata
                continue
            revs.append(
                {
                    "external_id": e["id"]["label"],
                    "author": e.get("author", {}).get("name", {}).get("label"),
                    "rating": int(e["im:rating"]["label"]),
                    "title": e.get("title", {}).get("label"),
                    "text": e.get("content", {}).get("label"),
                    "published_at": _parse_apple_date(e.get("updated", {}).get("label")),
                }
            )

    snapshot = {
        "avg_rating": None,
        "ratings_count": None,
        "reviews_count": len(revs),
        "histogram": None,
    }
    try:
        lookup = requests.get(
            "https://itunes.apple.com/lookup",
            params={"id": app_id, "country": country},
            timeout=30,
        ).json()
        results = lookup.get("results") or []
        if results:
            info = results[0]
            rating = info.get("averageUserRating")
            snapshot["avg_rating"] = round(rating, 2) if rating is not None else None
            snapshot["ratings_count"] = info.get("userRatingCount")
    except Exception:
        pass  # metrics are best-effort; reviews already collected

    return snapshot, revs


def _parse_apple_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None
