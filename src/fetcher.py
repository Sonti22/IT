"""Fetch RSS feeds, deduplicate against state."""
import hashlib
from dataclasses import dataclass
from typing import Iterable

import feedparser

from src.sources import SOURCES


@dataclass
class Item:
    id: str
    source: str
    tag: str
    emoji: str
    title: str
    link: str
    summary: str


def _item_id(link: str, title: str) -> str:
    return hashlib.sha1(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_new_items(posted_ids: Iterable[str]) -> list[Item]:
    seen = set(posted_ids)
    items: list[Item] = []

    for src in SOURCES:
        try:
            feed = feedparser.parse(src["url"])
        except Exception as e:
            print(f"[fetch] {src['name']} failed: {e}")
            continue

        for entry in feed.entries[:5]:
            link = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not link or not title:
                continue

            iid = _item_id(link, title)
            if iid in seen:
                continue

            summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))[:600]

            items.append(Item(
                id=iid,
                source=src["name"],
                tag=src["tag"],
                emoji=src["emoji"],
                title=title,
                link=link,
                summary=summary,
            ))

    items.sort(key=lambda x: x.id)
    return items
