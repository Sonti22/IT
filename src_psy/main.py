"""Точка входа psy-бота. Один запуск — одна тема.

Запускается GitHub Actions два раза в сутки.
"""
import asyncio

from src_psy.generator import generate_post, pick_next_topic
from src_psy.publisher import publish
from src_psy.state import load_state, save_state


async def main() -> None:
    state = load_state()
    topic, cycled = pick_next_topic(state["posted_topic_ids"])

    if cycled:
        print("[psy.main] все темы пройдены, начинаю новый цикл")
        state["posted_topic_ids"] = []

    print(f"[psy.main] выбрана тема: {topic['id']} — {topic['title']}")

    try:
        post = await generate_post(topic)
        await publish(post)
    except Exception as e:
        print(f"[psy.main] FAILED on topic {topic['id']}: {e}")
        save_state(state)
        raise

    state["posted_topic_ids"].append(topic["id"])
    save_state(state)
    print(f"[psy.main] опубликовано: {post.title[:60]}")


if __name__ == "__main__":
    asyncio.run(main())
