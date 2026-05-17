"""Хранение состояния psy-бота в state_psy.json (коммитится GitHub Actions).

Состояние — список id уже опубликованных тем. Если все темы пройдены,
вызывающий код сбрасывает список, чтобы запустить новый цикл.
"""
import json
from pathlib import Path
from typing import TypedDict

STATE_PATH = Path(__file__).resolve().parent.parent / "state_psy.json"


class PsyState(TypedDict):
    posted_topic_ids: list[str]


def load_state() -> PsyState:
    if not STATE_PATH.exists():
        return {"posted_topic_ids": []}
    with STATE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("posted_topic_ids", [])
    return data


def save_state(state: PsyState, max_history: int = 2000) -> None:
    state["posted_topic_ids"] = state["posted_topic_ids"][-max_history:]
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
