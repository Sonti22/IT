"""Multi-provider LLM wrapper for Russian-language news summarization.

Providers, in order of preference (first available wins):
  1. Groq (Llama 3.3 70B) — fast, free, global. Set GROQ_API_KEY.
  2. Gemini 2.0 Flash — free if project supports it. Set GEMINI_API_KEY.
  3. Anthropic Claude Haiku — paid. Set ANTHROPIC_API_KEY.

If all fail or none configured, falls back to raw RSS summary (no LLM).
"""
import os
from dataclasses import dataclass

import httpx

from src.fetcher import Item

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
CLAUDE_MODEL = "claude-haiku-4-5"

PROMPT_TEMPLATE = """Ты редактор Telegram-канала "ИИ + DevOps дайджест на русском".
Сделай краткое русскоязычное саммари новости и добавь короткий комментарий "почему это важно".

ВХОД:
Заголовок: {title}
Источник: {source}
Описание: {summary}
Ссылка: {link}

ТРЕБОВАНИЯ:
- Заголовок поста: один ёмкий русский заголовок до 80 символов, без эмодзи в начале.
- TL;DR: 3–5 строк, простой русский, без воды.
- Почему важно: 1–2 строки, без штампов вроде "это важно потому что".
- Не выдумывай факты, опирайся только на вход.
- Никакого Markdown, никаких тегов, только чистый текст.

ВЫВОД СТРОГО В ФОРМАТЕ:
TITLE: <заголовок>
TLDR: <3–5 строк через перенос>
WHY: <1–2 строки>
"""


@dataclass
class Summary:
    title: str
    tldr: str
    why: str


def _parse(text: str, fallback_title: str) -> Summary:
    title = ""
    tldr_lines: list[str] = []
    why = ""

    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TITLE:"):
            current = "title"
            title = stripped[len("TITLE:"):].strip()
        elif stripped.startswith("TLDR:"):
            current = "tldr"
            rest = stripped[len("TLDR:"):].strip()
            if rest:
                tldr_lines.append(rest)
        elif stripped.startswith("WHY:"):
            current = "why"
            why = stripped[len("WHY:"):].strip()
        elif current == "tldr" and stripped:
            tldr_lines.append(stripped)
        elif current == "why" and stripped:
            why = (why + " " + stripped).strip()

    return Summary(
        title=title or fallback_title,
        tldr="\n".join(tldr_lines) or "Подробности по ссылке.",
        why=why,
    )


async def _groq(prompt: str, fallback_title: str) -> Summary:
    key = os.environ["GROQ_API_KEY"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 600,
            },
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    return _parse(text, fallback_title)


async def _gemini(prompt: str, fallback_title: str) -> Summary:
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
            },
        )
        r.raise_for_status()
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse(text, fallback_title)


async def _claude(prompt: str, fallback_title: str) -> Summary:
    key = os.environ["ANTHROPIC_API_KEY"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
    return _parse(text, fallback_title)


async def summarize(item: Item) -> Summary:
    prompt = PROMPT_TEMPLATE.format(
        title=item.title,
        source=item.source,
        summary=item.summary or "(нет описания)",
        link=item.link,
    )
    fallback_title = item.title[:80]

    providers = []
    if os.environ.get("GROQ_API_KEY"):
        providers.append(("groq", _groq))
    if os.environ.get("GEMINI_API_KEY"):
        providers.append(("gemini", _gemini))
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("claude", _claude))

    last_err: Exception | None = None
    for name, fn in providers:
        try:
            return await fn(prompt, fallback_title)
        except Exception as e:
            print(f"[summarize] {name} failed: {e}")
            last_err = e
            continue

    if last_err:
        print(f"[summarize] all providers failed, using raw RSS summary")
    else:
        print("[summarize] no LLM provider configured, using raw RSS summary")

    return Summary(
        title=fallback_title,
        tldr=(item.summary or "Подробности по ссылке.")[:300],
        why="",
    )
