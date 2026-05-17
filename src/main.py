"""Entry point. Run by GitHub Actions cron once per hour."""
import asyncio

from src.fetcher import fetch_new_items
from src.publisher import publish
from src.sources import MAX_POSTS_PER_RUN, MAX_STATE_HISTORY
from src.state import load_state, save_state
from src.summarizer import summarize


async def main() -> None:
    state = load_state()
    try:
        new_items = await fetch_new_items(state["posted_ids"])
    except Exception as e:
        print(f"[main] fetch failed entirely: {e}")
        return

    if not new_items:
        print("[main] no new items")
        return

    to_post = new_items[:MAX_POSTS_PER_RUN]
    print(f"[main] fetched {len(new_items)} new items, posting {len(to_post)}")

    try:
        for item in to_post:
            try:
                summary = await summarize(item)
                await publish(item, summary)
                state["posted_ids"].append(item.id)
                save_state(state, max_history=MAX_STATE_HISTORY)
                print(f"[main] posted: {item.title[:60]}")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[main] FAILED on {item.title[:60]}: {e}")
    finally:
        save_state(state, max_history=MAX_STATE_HISTORY)
        print("[main] state saved")


if __name__ == "__main__":
    asyncio.run(main())
