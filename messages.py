"""Random / editable bot messages for /meet."""

from __future__ import annotations

import json
import os
import random
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MESSAGES_FILE = Path(os.getenv("MESSAGES_FILE", str(BASE_DIR / "messages.json")))

_lock = threading.Lock()

_DEFAULT = {
    "pending": ["Създавам Google Meet линк…"],
    "ready": ["{user} споделя Meet линк:"],
}


def _ensure_file() -> None:
    if not MESSAGES_FILE.exists():
        MESSAGES_FILE.write_text(
            json.dumps(_DEFAULT, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def load_messages() -> dict[str, list[str]]:
    _ensure_file()
    with _lock:
        data = json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
    pending = [str(x).strip() for x in data.get("pending", []) if str(x).strip()]
    ready = [str(x).strip() for x in data.get("ready", []) if str(x).strip()]
    return {
        "pending": pending or list(_DEFAULT["pending"]),
        "ready": ready or list(_DEFAULT["ready"]),
    }


def save_messages(data: dict[str, list[str]]) -> None:
    payload = {
        "pending": list(data.get("pending", [])),
        "ready": list(data.get("ready", [])),
    }
    with _lock:
        MESSAGES_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def pick_pending() -> str:
    return random.choice(load_messages()["pending"])


def pick_ready(who: str) -> str:
    template = random.choice(load_messages()["ready"])
    return template.replace("{user}", who)


def add_message(kind: str, text: str) -> int:
    if kind not in ("pending", "ready"):
        raise ValueError("kind must be pending or ready")
    text = text.strip()
    if not text:
        raise ValueError("empty message")
    if kind == "ready" and "{user}" not in text:
        text = f"{{user}} {text}"
    data = load_messages()
    data[kind].append(text)
    save_messages(data)
    return len(data[kind])


def delete_message(kind: str, index: int) -> str:
    if kind not in ("pending", "ready"):
        raise ValueError("kind must be pending or ready")
    data = load_messages()
    items = data[kind]
    if index < 1 or index > len(items):
        raise IndexError(f"Няма съобщение №{index}")
    removed = items.pop(index - 1)
    if not items:
        raise ValueError("Не може да остане празен списък — добави друго преди да махнеш последното.")
    data[kind] = items
    save_messages(data)
    return removed
