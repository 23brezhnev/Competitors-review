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
- **Сбор:** VK API, `t.me/s` (без ключей), feedparser/BeautifulSoup,
  google-play-scraper, Apple RSS + Lookup API
- **LLM:** DeepSeek (OpenAI-совместимый API)
- **Доставка:** Telegram Bot API, у каждого продукта свой бот
- **Хостинг:** админка на Vercel, недельная задача в GitHub Actions

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
| `TG_BOT_TOKEN`, `TG_CHAT_ID` | @BotFather → отправка отчёта (общий бот по умолчанию) |
| `DEEPSEEK_API_KEY` | platform.deepseek.com |

> Для **чтения** Telegram-каналов ключи не нужны: публичные каналы читаются
> через веб-превью `t.me/s/<канал>`. Токен бота нужен только чтобы **отправить**
> готовый отчёт.

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

## Деплой: Vercel (админка) + GitHub Actions (отчёты)

Почему так: сбор данных ходит по всем источникам и вызывает LLM — это минуты, а
serverless-функция Vercel на Hobby-плане умирает через 60 секунд. Actions даёт
30 минут и логи каждого запуска. Админка же — обычные короткие HTTP-запросы,
для неё serverless подходит.

### 1. Админка на Vercel

Импортируйте репозиторий на [vercel.com/new](https://vercel.com/new). Конфиг
(`vercel.json`, `api/index.py`) уже в проекте, настраивать сборку не нужно.

В **Settings → Environment Variables** добавьте:

| Переменная | Значение |
|---|---|
| `DATABASE_URL` | строка подключения Supabase (см. выше, префикс `postgresql+psycopg2://`) |
| `SECRET_KEY` | длинная случайная строка для сессий |

Обязательно берите **Connection pooling** строку (порт `6543`), а не прямую
(5432): serverless открывает соединение на каждый вызов и быстро исчерпает
лимит Postgres. Код это учитывает — при переменной `VERCEL` пул отключается
(`NullPool`).

Создать первого пользователя админки (Vercel не даёт shell — запустите локально
с тем же `DATABASE_URL`):

```bash
DATABASE_URL='<строка от Supabase>' python -m scripts.create_user you@example.com 'пароль'
```

### 2. Отчёты в GitHub Actions

Workflow лежит в `.github/workflows/weekly-report.yml`: понедельник, 06:00 UTC
(09:00 МСК), плюс кнопка ручного запуска.

В **Settings → Secrets and variables → Actions** добавьте секреты:

`DATABASE_URL`, `DEEPSEEK_API_KEY`, `VK_SERVICE_TOKEN`, `TG_BOT_TOKEN`,
`TG_CHAT_ID`

Здесь можно использовать прямое соединение (порт 5432) — задача одна и
долгоживущая.

Первый прогон запустите руками: вкладка **Actions → Weekly competitor report →
Run workflow**. Так вы увидите ошибки сразу, а не через неделю.

## Альтернатива: деплой на VPS

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
- коллектор App Store: 50 отзывов, рейтинг и даты; пустой стор и троттлинг со
  стороны Apple не роняют сбор;
- коллектор Telegram (`t.me/s`, без ключей): пагинация уходит назад за пределы
  недельного окна, ID уникальны;
- коллектор сайтов: RSS (40 и 200 записей) и детект изменений по хэшу;
- недельный пайплайн: сбор → дедуп (повторный запуск не плодит дубли) →
  снимок → отчёт → отправка в бот продукта;
- динамика рейтинга: `рейтинг 4.78 (-0.17 за неделю)`;
- сломанный источник не роняет отчёт, а попадает в него как `⚠️`.

Не проверено вживую (нужны ключи): VK, Google Play, DeepSeek, а также сам
деплой на Vercel и запуск workflow в Actions.
