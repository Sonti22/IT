"""Генератор поста для psy-канала.

Тот же multi-provider подход, что и в src/summarizer.py:
  1. Groq (Llama 3.3 70B) — GROQ_API_KEY
  2. Gemini 2.0 Flash — GEMINI_API_KEY
  3. Anthropic Claude Haiku — ANTHROPIC_API_KEY

Если все провайдеры падают — используем заголовок и brief темы как запасной вариант.
"""
import os
import re
from dataclasses import dataclass, field

import httpx

from src_psy.topics import TOPICS, Topic

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"
CLAUDE_MODEL = "claude-haiku-4-5"


PROMPT_TEMPLATE = """Ты редактор русскоязычного Telegram-канала о психологии денег и принятия решений.
Напиши один пост на заданную тему.

ТЕМА: {title}
КАТЕГОРИЯ: {category}
ЧТО ОСВЕТИТЬ: {brief}

ТРЕБОВАНИЯ К ПОСТУ:
- Язык: русский, разговорный, без канцелярита.
- Длина тела поста: 500–1000 символов (без учёта заголовка и хэштегов).
- Структура: цепляющее начало (1–2 строки) → реальный пример или конкретная ситуация → практический вывод (1–2 строки).
- Никакого Markdown, никаких звёздочек, решёток, подчёркиваний.
- Никаких эмодзи в начале строк и заголовка.
- Не используй штампы вроде «в современном мире», «как известно».
- Не выдумывай статистику, которой не существует. Если приводишь цифру — это либо общеизвестный факт, либо округлённый бытовой пример.
- 3–4 релевантных хэштега на русском или транслите, через пробел, в одну строку.

ВЫВОД СТРОГО В ФОРМАТЕ:
TITLE: <короткий русский заголовок до 80 символов>
BODY: <тело поста на 500–1000 символов, можно с переносами строк>
TAGS: <#тег1 #тег2 #тег3>
"""


@dataclass
class Post:
    title: str
    body: str
    hashtags: list[str] = field(default_factory=list)


def pick_next_topic(posted_ids: list[str]) -> tuple[Topic, bool]:
    """Возвращает (тему, было_ли_сброшено).

    Если все темы уже опубликованы — сбрасывает цикл и берёт первую.
    """
    posted_set = set(posted_ids)
    for topic in TOPICS:
        if topic["id"] not in posted_set:
            return topic, False
    # Все темы пройдены — стартуем новый цикл.
    return TOPICS[0], True


_TAG_RE = re.compile(r"#\S+")


def _parse(text: str, fallback: Topic) -> Post:
    title = ""
    body_lines: list[str] = []
    tags_line = ""

    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TITLE:"):
            current = "title"
            title = stripped[len("TITLE:"):].strip()
        elif stripped.startswith("BODY:"):
            current = "body"
            rest = stripped[len("BODY:"):].strip()
            if rest:
                body_lines.append(rest)
        elif stripped.startswith("TAGS:"):
            current = "tags"
            tags_line = stripped[len("TAGS:"):].strip()
        elif current == "body":
            # Сохраняем пустые строки внутри тела, но без хвостов.
            body_lines.append(line.rstrip())
        elif current == "tags" and stripped:
            tags_line = (tags_line + " " + stripped).strip()

    # Чистим хвостовые пустые строки в теле.
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    body = "\n".join(body_lines).strip()
    hashtags = _TAG_RE.findall(tags_line)

    if not title:
        title = fallback["title"]
    if not body:
        body = fallback["brief"]
    if not hashtags:
        hashtags = ["#психология", "#деньги", "#решения"]

    return Post(title=title, body=body, hashtags=hashtags)


async def _groq(prompt: str, fallback: Topic) -> Post:
    key = os.environ["GROQ_API_KEY"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 900,
            },
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    return _parse(text, fallback)


async def _gemini(prompt: str, fallback: Topic) -> Post:
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 900},
            },
        )
        r.raise_for_status()
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse(text, fallback)


async def _claude(prompt: str, fallback: Topic) -> Post:
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
                "max_tokens": 900,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
    return _parse(text, fallback)


async def generate_post(topic: Topic) -> Post:
    prompt = PROMPT_TEMPLATE.format(
        title=topic["title"],
        category=topic["category"],
        brief=topic["brief"],
    )

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
            return await fn(prompt, topic)
        except Exception as e:
            print(f"[generate] {name} failed: {e}")
            last_err = e
            continue

    if last_err:
        print("[generate] all providers failed, using topic brief as body")
    else:
        print("[generate] no LLM provider configured, using topic brief as body")

    return Post(
        title=topic["title"],
        body=topic["brief"],
        hashtags=["#психология", "#деньги", "#решения"],
    )
