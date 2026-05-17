"""Helper: discover Telegram channel ID after bot has been added as admin.

Usage:
  1. Create the channel.
  2. Add the bot as admin with "Post messages" right.
  3. Post any message in the channel (or use the channel chat).
  4. Run: python -m src.tools.find_channel_id
  5. The script lists all chats the bot has seen, including channel chat_id.

Requires env var TG_BOT_TOKEN.
"""
import os
import sys

import httpx


def main() -> int:
    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        print("ERROR: TG_BOT_TOKEN env var is not set", file=sys.stderr)
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    r = httpx.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    if not data.get("ok"):
        print(f"ERROR: {data}", file=sys.stderr)
        return 2

    updates = data.get("result", [])
    if not updates:
        print("No updates yet.")
        print("Make sure: (1) bot is admin in the channel, (2) at least one message has been posted in the channel.")
        return 0

    seen: dict[int, str] = {}
    for u in updates:
        msg = u.get("channel_post") or u.get("message") or u.get("edited_channel_post")
        if not msg:
            continue
        chat = msg.get("chat", {})
        cid = chat.get("id")
        title = chat.get("title") or chat.get("username") or chat.get("first_name") or "(no name)"
        chat_type = chat.get("type", "?")
        if cid is not None:
            seen[cid] = f"{title} [{chat_type}]"

    if not seen:
        print("Updates exist but no chats found in them. Try posting in the channel directly.")
        return 0

    print("Chats the bot has seen:")
    for cid, label in seen.items():
        marker = " ← channel" if str(cid).startswith("-100") else ""
        print(f"  chat_id={cid}  {label}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
