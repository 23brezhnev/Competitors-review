from sqladmin import ModelView

from app.models import (
    AppSnapshot,
    Competitor,
    Post,
    Product,
    Report,
    Review,
    Source,
    User,
)


# ----- Configuration views (the editable hierarchy) ------------------------ #
class ProductAdmin(ModelView, model=Product):
    name = "Продукт"
    name_plural = "Продукты"
    icon = "fa-solid fa-box"
    category = "Конфигурация"
    column_list = [Product.id, Product.name, Product.tg_chat_id, Product.is_active, Product.created_at]
    column_searchable_list = [Product.name]
    form_columns = [
        Product.name,
        Product.description,
        Product.tg_bot_token,
        Product.tg_chat_id,
        Product.is_active,
    ]


class CompetitorAdmin(ModelView, model=Competitor):
    name = "Конкурент"
    name_plural = "Конкуренты"
    icon = "fa-solid fa-user-secret"
    category = "Конфигурация"
    column_list = [Competitor.id, Competitor.name, Competitor.product, Competitor.is_active]
    column_searchable_list = [Competitor.name]
    form_columns = [Competitor.product, Competitor.name, Competitor.notes, Competitor.is_active]


class SourceAdmin(ModelView, model=Source):
    name = "Источник"
    name_plural = "Источники"
    icon = "fa-solid fa-rss"
    category = "Конфигурация"
    column_list = [Source.id, Source.type, Source.title, Source.identifier, Source.competitor, Source.is_active]
    column_searchable_list = [Source.identifier, Source.title]
    form_columns = [
        Source.competitor,
        Source.type,
        Source.identifier,
        Source.title,
        Source.config,
        Source.is_active,
    ]


# ----- Collected data (read-only-ish) -------------------------------------- #
class PostAdmin(ModelView, model=Post):
    name = "Пост"
    name_plural = "Посты"
    icon = "fa-solid fa-newspaper"
    category = "Данные"
    column_list = [Post.id, Post.source_id, Post.published_at, Post.text, Post.url]
    can_create = False
    can_edit = False


class ReviewAdmin(ModelView, model=Review):
    name = "Отзыв"
    name_plural = "Отзывы"
    icon = "fa-solid fa-star"
    category = "Данные"
    column_list = [Review.id, Review.source_id, Review.rating, Review.published_at, Review.text]
    can_create = False
    can_edit = False


class AppSnapshotAdmin(ModelView, model=AppSnapshot):
    name = "Снимок приложения"
    name_plural = "Динамика приложений"
    icon = "fa-solid fa-chart-line"
    category = "Данные"
    column_list = [AppSnapshot.id, AppSnapshot.source_id, AppSnapshot.taken_at, AppSnapshot.avg_rating, AppSnapshot.ratings_count]
    can_create = False
    can_edit = False


class ReportAdmin(ModelView, model=Report):
    name = "Отчёт"
    name_plural = "Отчёты"
    icon = "fa-solid fa-file-lines"
    category = "Данные"
    column_list = [Report.id, Report.product_id, Report.period_start, Report.period_end, Report.sent_at]
    can_create = False
    can_edit = False


# ----- Access control ------------------------------------------------------ #
class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    category = "Доступ"
    column_list = [User.id, User.email, User.is_active, User.created_at]
    # Passwords are set via scripts/create_user.py (bcrypt) — never edited raw here.
    can_create = False
    can_edit = False


ALL_VIEWS = [
    ProductAdmin,
    CompetitorAdmin,
    SourceAdmin,
    PostAdmin,
    ReviewAdmin,
    AppSnapshotAdmin,
    ReportAdmin,
    UserAdmin,
]
