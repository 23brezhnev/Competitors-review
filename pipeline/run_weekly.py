from __future__ import annotations

"""Weekly job: collect -> store (dedup) -> summarize (DeepSeek) -> send (Telegram).

Run by cron once a week, e.g.:
    0 9 * * 1  cd /opt/competitor-monitor && .venv/bin/python -m pipeline.run_weekly
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AppSnapshot, Post, Review, Source, SourceType, Product, Report
from collectors import stores, telegram, vk, web
from pipeline import bot
from pipeline.summarize import summarize_competitor

WINDOW_DAYS = 7


def _collect_posts(source: Source) -> list[dict]:
    if source.type == SourceType.vk:
        return vk.fetch_vk_posts(source.identifier)
    if source.type == SourceType.telegram:
        return telegram.fetch_telegram_posts(source.identifier)
    if source.type == SourceType.website:
        return web.fetch_web_posts(source.identifier, source.config)
    return []


def _store_posts(db, source: Source, posts: list[dict]) -> int:
    existing = set(db.scalars(select(Post.external_id).where(Post.source_id == source.id)))
    new = 0
    for p in posts:
        if not p.get("external_id") or p["external_id"] in existing:
            continue
        db.add(Post(source_id=source.id, **{k: p.get(k) for k in
                    ("external_id", "url", "text", "published_at", "raw")}))
        new += 1
    return new


def _handle_app_source(db, source: Source) -> str:
    """Store snapshot + reviews, return a human note about the weekly dynamics."""
    cfg = source.config or {}
    country = cfg.get("country", "ru")
    if source.type == SourceType.googleplay:
        snapshot, reviews = stores.fetch_googleplay(
            source.identifier, lang=cfg.get("lang", "ru"), country=country
        )
    else:
        snapshot, reviews = stores.fetch_appstore(source.identifier, country=country)

    prev = db.scalar(
        select(AppSnapshot).where(AppSnapshot.source_id == source.id)
        .order_by(AppSnapshot.taken_at.desc())
    )
    db.add(AppSnapshot(source_id=source.id, **snapshot))

    existing = set(db.scalars(select(Review.external_id).where(Review.source_id == source.id)))
    new_reviews = [r for r in reviews if r.get("external_id") and r["external_id"] not in existing]
    for r in new_reviews:
        db.add(Review(source_id=source.id, **r))

    negatives = [r for r in new_reviews if (r.get("rating") or 5) <= 2]
    note = f"{source.title or source.identifier}: {len(new_reviews)} новых отзывов"
    if snapshot.get("avg_rating") is not None:
        note += f", рейтинг {snapshot['avg_rating']}"
        if prev and prev.avg_rating is not None:
            delta = round(snapshot["avg_rating"] - prev.avg_rating, 2)
            note += f" ({'+' if delta >= 0 else ''}{delta} за неделю)"
    if negatives:
        note += f", из них {len(negatives)} негативных"
    return note


def run() -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=WINDOW_DAYS)

    with SessionLocal() as db:
        products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
        for product in products:
            blocks: list[str] = []
            for competitor in product.competitors:
                if not competitor.is_active:
                    continue
                recent_posts: list[dict] = []
                review_notes: list[str] = []

                for source in competitor.sources:
                    if not source.is_active:
                        continue
                    try:
                        if source.type in (SourceType.googleplay, SourceType.appstore):
                            review_notes.append(_handle_app_source(db, source))
                        else:
                            posts = _collect_posts(source)
                            _store_posts(db, source, posts)
                            for p in posts:
                                pub = p.get("published_at")
                                if pub and pub >= since:
                                    recent_posts.append(
                                        {"source": source.type.value,
                                         "published_at": pub.strftime("%Y-%m-%d"),
                                         "text": p.get("text", "")}
                                    )
                    except Exception as exc:  # one bad source shouldn't kill the run
                        review_notes.append(f"⚠️ {source}: ошибка сбора ({exc})")
                db.commit()

                blocks.append(
                    summarize_competitor(competitor.name, recent_posts, "\n".join(review_notes))
                )

            if not blocks:
                continue

            header = (
                f"📊 *Еженедельный отчёт: {product.name}*\n"
                f"_период: {since.strftime('%d.%m')} — {now.strftime('%d.%m.%Y')}_\n"
            )
            content = header + "\n\n".join(blocks)

            report = Report(
                product_id=product.id, period_start=since, period_end=now, content=content
            )
            db.add(report)
            db.commit()

            # Deliver to the product's own bot; fall back to the global bot (.env).
            bot.send_telegram(content, token=product.tg_bot_token, chat_id=product.tg_chat_id)
            report.sent_at = datetime.now(timezone.utc)
            db.commit()


if __name__ == "__main__":
    run()
