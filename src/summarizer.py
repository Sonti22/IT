"""Wrap Gemini 2.0 Flash for Russian-language news summarization.

Designed so swapping to Claude later is a one-class change: implement the same
`summarize(item) -> Summary` contract.
"""
import os
from dataclasses import dataclass

import google.generativeai as genai

from src.fetcher import Item

MODEL_NAME = "gemini-2.0-flash"

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


def _configure() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)


def _parse(text: str) -> Summary:
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
        title=title or "Без заголовка",
        tldr="\n".join(tldr_lines) or "Подробности по ссылке.",
        why=why or "",
    )


async def summarize(item: Item) -> Summary:
    _configure()
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = PROMPT_TEMPLATE.format(
        title=item.title,
        source=item.source,
        summary=item.summary or "(нет описания)",
        link=item.link,
    )

    response = await model.generate_content_async(
        prompt,
        generation_config={
            "temperature": 0.4,
            "max_output_tokens": 600,
        },
    )

    text = (response.text or "").strip()
    return _parse(text)
