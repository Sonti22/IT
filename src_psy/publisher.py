"""Публикация поста в psy-канал через Telegram Bot API.

Использует общий токен TG_BOT_TOKEN, но отдельный канал TG_PSY_CHANNEL_ID.
"""
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.text_decorations import html_decoration as html

from src_psy.generator import Post

MAX_TITLE = 120
MAX_BODY = 3500
MAX_TAGS = 200


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_post(post: Post) -> str:
    title = html.quote(_clip(post.title, MAX_TITLE))
    body = html.quote(_clip(post.body, MAX_BODY))
    tags_text = " ".join(post.hashtags)
    tags = html.quote(_clip(tags_text, MAX_TAGS))

    tags_block = f"\n\n{tags}" if tags else ""
    return f"<b>{title}</b>\n\n{body}{tags_block}"


async def publish(post: Post) -> None:
    token = os.environ.get("TG_BOT_TOKEN")
    channel_id = os.environ.get("TG_PSY_CHANNEL_ID")
    if not token or not channel_id:
        raise RuntimeError("TG_BOT_TOKEN or TG_PSY_CHANNEL_ID is not set")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(
            chat_id=channel_id,
            text=format_post(post),
            disable_web_page_preview=True,
        )
    finally:
        await bot.session.close()
