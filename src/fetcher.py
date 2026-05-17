"""Fetch RSS feeds, deduplicate against state."""
import asyncio
import hashlib
import re
import socket
import time
from dataclasses import dataclass
from typing import Iterable

import feedparser

from src.sources import SOURCES

socket.setdefaulttimeout(20)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class Item:
    id: str
    source: str
    tag: str
    emoji: str
    title: str
    link: str
    summary: str
    published_ts: float


def _item_id(link: str, title: str) -> str:
    return hashlib.sha1(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    return _WS_RE.sub(" ", text).strip()


def _published_ts(entry) -> float:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return time.mktime(parsed)
            except (TypeError, ValueError, OverflowError):
                continue
    return 0.0


def _safe_link(link: str) -> bool:
    return isinstance(link, str) and link.startswith(("http://", "https://"))


_USER_AGENT = (
    "Mozilla/5.0 (compatible; ITNewsBot/1.0; +https://github.com/Sonti22/IT)"
)


def _parse_one(url: str):
    return feedparser.parse(url, agent=_USER_AGENT)


async def fetch_new_items(posted_ids: Iterable[str]) -> list[Item]:
    seen = set(posted_ids)
    items: list[Item] = []

    feeds = await asyncio.gather(
        *(asyncio.to_thread(_parse_one, src["url"]) for src in SOURCES),
        return_exceptions=True,
    )

    for src, feed in zip(SOURCES, feeds):
        if isinstance(feed, Exception):
            print(f"[fetch] {src['name']} failed: {feed}")
            continue

        for entry in feed.entries[:5]:
            link = entry.get("link", "")
            title = (entry.get("title") or "").strip()
            if not title or not _safe_link(link):
                continue

            iid = _item_id(link, title)
            if iid in seen:
                continue

            raw_summary = entry.get("summary") or entry.get("description") or ""
            summary = _strip_html(raw_summary)[:600]

            items.append(Item(
                id=iid,
                source=src["name"],
                tag=src["tag"],
                emoji=src["emoji"],
                title=title,
                link=link,
                summary=summary,
                published_ts=_published_ts(entry),
            ))

    items.sort(key=lambda x: x.published_ts, reverse=True)
    return items
