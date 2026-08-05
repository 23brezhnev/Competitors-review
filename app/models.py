import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SourceType(str, enum.Enum):
    vk = "vk"
    telegram = "telegram"
    website = "website"
    appstore = "appstore"      # Apple App Store
    googleplay = "googleplay"  # Google Play


# --------------------------------------------------------------------------- #
#  Access control (simple, DB-managed)
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __str__(self) -> str:
        return self.email


# --------------------------------------------------------------------------- #
#  Configuration hierarchy:  Product -> Competitor -> Source
# --------------------------------------------------------------------------- #
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Per-product Telegram bot for delivery. If empty, the global TG_BOT_TOKEN /
    # TG_CHAT_ID from .env are used as a fallback.
    tg_bot_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tg_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="competitors")
    sources: Mapped[list["Source"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    # identifier meaning depends on type:
    #   vk         -> group short name or wall url
    #   telegram   -> channel @name or t.me url
    #   website    -> page or RSS url
    #   appstore   -> numeric app id
    #   googleplay -> package name (com.example.app)
    identifier: Mapped[str] = mapped_column(String(500))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # per-source overrides: {"rss": true, "country": "ru", "lang": "ru", ...}
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitor: Mapped["Competitor"] = relationship(back_populates="sources")

    def __str__(self) -> str:
        return f"{self.type.value}: {self.title or self.identifier}"


# --------------------------------------------------------------------------- #
#  Collected data
# --------------------------------------------------------------------------- #
class Post(Base):
    """A post/news item from VK, Telegram or a website (dedup by source+external_id)."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_post_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Review(Base):
    """A single app-store review (dedup by source+external_id)."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_review_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppSnapshot(Base):
    """Point-in-time app metrics — the basis for review *dynamics* over weeks."""

    __tablename__ = "app_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    histogram: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"1": n, ... "5": n}


class Report(Base):
    """A generated weekly digest (kept for history)."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
