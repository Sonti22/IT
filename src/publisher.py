"""Publish a formatted post to the Telegram channel via Bot API."""
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.text_decorations import html_decoration as html

from src.fetcher import Item
from src.summarizer import Summary

MAX_TITLE = 120
MAX_TLDR = 2500
MAX_WHY = 400


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_post(item: Item, summary: Summary) -> str:
    title = html.quote(_clip(summary.title, MAX_TITLE))
    tldr = html.quote(_clip(summary.tldr, MAX_TLDR))
    link = html.quote(item.link)
    tag = item.tag
    emoji = item.emoji

    why_block = ""
    if summary.why:
        why_block = f"\n\n💡 <i>Почему важно:</i> {html.quote(_clip(summary.why, MAX_WHY))}"

    return (
        f"{emoji} <b>{title}</b>\n\n"
        f"{tldr}"
        f"{why_block}\n\n"
        f"🔗 <a href=\"{link}\">читать оригинал</a> · {tag}"
    )


async def publish(item: Item, summary: Summary) -> None:
    token = os.environ.get("TG_BOT_TOKEN")
    channel_id = os.environ.get("TG_CHANNEL_ID")
    if not token or not channel_id:
        raise RuntimeError("TG_BOT_TOKEN or TG_CHANNEL_ID is not set")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(
            chat_id=channel_id,
            text=format_post(item, summary),
            disable_web_page_preview=False,
        )
    finally:
        await bot.session.close()
