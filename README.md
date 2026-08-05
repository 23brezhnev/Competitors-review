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

## Статус

Скелет: модель данных, админка с авторизацией, все коллекторы и недельный
пайплайн готовы. Следующий шаг — прогнать по одному источнику с реальными
ключами и подключить Supabase.
