# IT News Telegram Bot

Автопостер новостей в Telegram-канал. Работает на GitHub Actions (без сервера), суммаризует через Gemini 2.0 Flash на русском, постит через Telegram Bot API.

## Что внутри

```
it-news-bot/
├── .github/workflows/post.yml   # cron: каждый час
├── src/
│   ├── main.py                  # точка входа
│   ├── sources.py               # список RSS + лимиты
│   ├── fetcher.py               # парсинг RSS + дедуп
│   ├── summarizer.py            # Gemini 2.0 Flash (легко заменить на Claude)
│   ├── publisher.py             # Telegram Bot API через aiogram
│   └── state.py                 # state.json для дедупа между запусками
├── state.json                   # ID опубликованных новостей (коммитится ботом)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Деплой за 7 шагов

### 1. Создать канал и бота в Telegram

1. Создать публичный канал в Telegram (например `@ai_devops_daily_ru`).
2. Открыть `@BotFather` → `/newbot` → задать имя и username → **сохранить TOKEN**.
3. Добавить бота админом канала с правом "Post messages".
4. Узнать `chat_id` канала: переслать любое сообщение из канала в `@userinfobot` → скопировать число вида `-100xxxxxxxxxx`.

### 2. Получить ключ Gemini

1. Открыть [aistudio.google.com](https://aistudio.google.com).
2. **Get API Key** → **Create API key in new project**.
3. Сохранить ключ. Бесплатный лимит — 1500 запросов/день, для 8 постов/час хватит с запасом.

### 3. Создать репозиторий на GitHub

```bash
cd it-news-bot
git init
git add .
git commit -m "init bot"
gh repo create it-news-bot --private --source=. --push
```

Без `gh`: создать репозиторий на github.com вручную, затем:

```bash
git remote add origin https://github.com/<username>/it-news-bot.git
git branch -M main
git push -u origin main
```

### 4. Добавить секреты репозитория

На GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Создать три секрета:

| Имя | Значение |
|-----|----------|
| `TG_BOT_TOKEN` | токен от @BotFather |
| `TG_CHANNEL_ID` | chat_id канала (с минусом) |
| `GEMINI_API_KEY` | ключ Gemini |

### 5. Запустить workflow вручную

**Actions** → **Post IT News** → **Run workflow** → подождать ~1 мин → проверить логи и канал.

### 6. Cron включится автоматически

Раз в час (`0 * * * *`) бот будет проверять RSS, постить до 3 новых новостей за запуск, дедуплицировать через `state.json`.

### 7. Проверка через 24 часа

- В канале должно быть 50–70 постов за сутки.
- Файл `state.json` растёт, в нём накапливаются ID.
- Вкладка **Actions** — все запуски зелёные.

## Локальный запуск (для тестирования)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # заполнить значения
python -m src.main
```

`.env` автоматически подхватывается, если установлен `python-dotenv`. Для прода (GitHub Actions) переменные приходят из secrets.

## Настройка

### Изменить частоту постинга

В `.github/workflows/post.yml`:
- `cron: '0 * * * *'` — каждый час
- `cron: '0 */2 * * *'` — каждые 2 часа
- `cron: '*/30 * * * *'` — каждые 30 минут

В `src/sources.py`:
- `MAX_POSTS_PER_RUN = 3` — максимум новостей за запуск

### Изменить источники

Редактировать `src/sources.py`. Добавить любой RSS:

```python
{
    "name": "Source Name",
    "url": "https://example.com/feed.xml",
    "tag": "#tag",
    "emoji": "🔥",
},
```

### Переключиться с Gemini на Claude

В `src/summarizer.py` заменить вызов Gemini на Anthropic SDK. Контракт `summarize(item) -> Summary` сохраняется, остальной код не трогать.

```python
# pip install anthropic
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def summarize(item: Item) -> Summary:
    msg = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(...)}],
    )
    return _parse(msg.content[0].text)
```

Не забыть добавить секрет `ANTHROPIC_API_KEY` в репо.

## Подключение Claude Desktop к каналу через MCP (опционально)

Если хочешь читать/постить в канал прямо из Claude Desktop (для ручной работы со вторым каналом — психология):

1. Установить готовый MCP-сервер Telegram, например [chaindead/telegram-mcp](https://github.com/chaindead/telegram-mcp) или поискать актуальные на github.com/topics/mcp-server.
2. Получить `api_id` и `api_hash` на [my.telegram.org](https://my.telegram.org) (это user-API, не Bot API).
3. Прописать MCP-сервер в конфиге Claude Desktop (`~/.claude.json` на Mac/Linux, `%USERPROFILE%\.claude.json` на Windows):

```json
{
  "mcpServers": {
    "telegram": {
      "command": "npx",
      "args": ["-y", "telegram-mcp"],
      "env": {
        "TELEGRAM_API_ID": "...",
        "TELEGRAM_API_HASH": "..."
      }
    }
  }
}
```

4. Перезапустить Claude Desktop. В новом чате попросить Claude прочитать сообщения или запостить — он будет действовать от твоего имени.

## Лимиты и риски

- **GitHub Actions**: 2000 мин/мес для приватных репо. ~720 запусков в месяц × 1 мин = в лимит влезает. Для публичного репо лимит снят.
- **Gemini Free Tier**: 1500 запросов/день. 8 постов/час × 24 = 192/день. С запасом.
- **Cron задержки**: GitHub Actions может задержать запуск на 5–15 мин при пиках платформы. Не критично.
- **Авто-отключение cron**: GitHub отключает cron, если репо не активен 60 дней. Бот сам коммитит `state.json` → активность есть.
- **Telegram rate limit**: 30 сообщений/сек на канал. У нас 3 поста за запуск с 2-секундной паузой — невозможно превысить.

## Возможные проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| Workflow падает на `git push` | Нет permissions | Проверить `permissions: contents: write` в workflow |
| Бот не постит | Бот не админ канала | Добавить с правом Post messages |
| `GEMINI_API_KEY is not set` | Секрет не добавлен | Settings → Secrets → проверить имя |
| Дубли постов | `state.json` не коммитится | Проверить шаг `Commit state` в Actions log |
| Текст обрезан | Длинный TLDR | Уменьшить `max_output_tokens` в `summarizer.py` |

## Лицензия

MIT (для личного использования).
