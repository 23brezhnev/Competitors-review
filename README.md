# Competitor Monitor

Еженедельный мониторинг конкурентов: VK, Telegram, сайты и отзывы из App Store /
Google Play. Собирает активность, суммаризирует через DeepSeek и присылает
дайджест в Telegram. Конфигурация — через веб-админку.

## Модель данных

```
Продукт ──< Конкурент ──< Источник (vk | telegram | website | appstore | googleplay)
Собираемое:  Post (посты)   Review (отзывы)   AppSnapshot (динамика рейтингов)
```

## Стек

- **Админка/бэкенд:** FastAPI + SQLAdmin (авто-CRUD, простой вход по таблице `users`)
- **БД:** PostgreSQL (Supabase) в проде, SQLite для локальной разработки
- **Сбор:** VK API, Telethon, feedparser/BeautifulSoup, google-play-scraper, Apple RSS
- **LLM:** DeepSeek (OpenAI-совместимый API)
- **Доставка:** Telegram Bot API
- **Расписание:** cron (раз в неделю)

## Быстрый старт (локально)

```bash
cd competitor-monitor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # заполнить ключи
python -m scripts.create_user admin@example.com 'strong-password'
uvicorn app.main:app --reload
```

Админка: http://127.0.0.1:8000/admin  (вход — созданным пользователем).

## Заполнение конфигурации

1. Создать **Продукт**.
2. Добавить **Конкурентов** к продукту.
3. Добавить **Источники** конкуренту. Поле `identifier`:
   - `vk` — короткое имя группы или ссылка на стену
   - `telegram` — `@channel` или ссылка `t.me/...`
   - `website` — URL страницы или RSS (для RSS в `config` укажите `{"rss": true}`)
   - `appstore` — числовой ID приложения
   - `googleplay` — package name (`com.example.app`)

## Запуск отчёта

```bash
python -m pipeline.run_weekly
```

Cron (по понедельникам в 9:00):

```
0 9 * * 1  cd /opt/competitor-monitor && .venv/bin/python -m pipeline.run_weekly
```

## Ключи (.env)

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | Supabase Postgres (или SQLite локально) |
| `SECRET_KEY` | сессии админки |
| `VK_SERVICE_TOKEN` | dev.vk.com → сервисный ключ |
| `TG_API_ID`, `TG_API_HASH` | my.telegram.org → чтение каналов |
| `TG_BOT_TOKEN`, `TG_CHAT_ID` | @BotFather → отправка отчёта |
| `DEEPSEEK_API_KEY` | platform.deepseek.com |

> Telethon при первом запуске попросит код из Telegram и создаст файл сессии
> (`tg_session.session`). Сделайте это один раз локально, затем скопируйте файл
> на сервер.

## База данных (Supabase)

Проект `competitor-monitor` создан в регионе `eu-central-1`, схема из 8 таблиц
уже накатана миграцией `create_competitor_monitor_schema`. RLS включён без
политик: через публичный API данные недоступны никому, приложение ходит в базу
напрямую по Postgres-соединению.

`DATABASE_URL` возьмите в дашборде Supabase → **Project Settings → Database →
Connection string → URI** (пароль базы там же, при необходимости сбросить):

```
postgresql+psycopg2://postgres.<ref>:<пароль>@<host>:6543/postgres
```

Обратите внимание: SQLAlchemy требует префикс `postgresql+psycopg2://`, а
Supabase показывает строку как `postgresql://` — замените начало.

Схема уже существует, поэтому `Base.metadata.create_all()` в `app/main.py`
ничего не пересоздаёт.

## Деплой на VPS

```bash
git clone <ваш-репозиторий> /opt/competitor-monitor
cd /opt/competitor-monitor
cp .env.example .env && nano .env      # заполнить ключи и DATABASE_URL от Supabase
docker compose up -d --build
docker compose exec web python -m scripts.create_user you@example.com 'пароль'
```

Админка будет на `http://<ip-сервера>:8000/admin`.

> **Важно:** порт 8000 открыт наружу без HTTPS. Перед боевым использованием
> поставьте перед ним nginx/Caddy с TLS, иначе пароль от админки идёт открытым
> текстом. Вариант с Caddy — одна строка в `Caddyfile`:
> `monitor.example.com { reverse_proxy localhost:8000 }`

### Сессия Telegram

Telethon при первом входе запрашивает код из Telegram — сделайте это
интерактивно один раз:

```bash
docker compose run --rm web python -c "from collectors.telegram import fetch_telegram_posts; print(len(fetch_telegram_posts('@durov', limit=5)))"
```

Созданный `tg_session.session` подхватится через volume.

### Еженедельный запуск (cron на хосте)

```
0 9 * * 1  cd /opt/competitor-monitor && docker compose run --rm web python -m pipeline.run_weekly >> /var/log/competitor-monitor.log 2>&1
```

## Отчёты по продуктам

У каждого продукта — свой Telegram-бот (поля `tg_bot_token` / `tg_chat_id` в
карточке продукта). Если они пустые, используется общий бот из `.env`. Отчёт по
каждому продукту отправляется отдельным сообщением в свой чат.

## Что проверено

Прогнано локально на SQLite:

- админка стартует, вход работает (неверный пароль → 400, верный → 302), все
  8 разделов открываются, CRUD создаёт записи через реальные формы;
- иерархия Продукт → Конкурент → Источник сохраняется и читается;
- коллектор App Store: 50 отзывов, рейтинг и даты; пустой стор не падает;
- коллектор сайтов: RSS (40 и 200 записей) и детект изменений по хэшу;
- недельный пайплайн: сбор → дедуп (повторный запуск не плодит дубли) →
  снимок → отчёт → отправка в бот продукта;
- динамика рейтинга: `рейтинг 4.78 (-0.17 за неделю)`;
- сломанный источник не роняет отчёт, а попадает в него как `⚠️`.

Не проверено вживую (нужны ключи): VK, Telegram, Google Play, DeepSeek.
