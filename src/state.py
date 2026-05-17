"""State persistence via state.json (committed back to repo by GitHub Actions)."""
import json
from pathlib import Path
from typing import TypedDict

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


class State(TypedDict):
    posted_ids: list[str]


def load_state() -> State:
    if not STATE_PATH.exists():
        return {"posted_ids": []}
    with STATE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("posted_ids", [])
    return data


def save_state(state: State, max_history: int = 1000) -> None:
    state["posted_ids"] = state["posted_ids"][-max_history:]
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
