"""Allowlist: which chats/users may use /meet."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ACCESS_FILE = Path(os.getenv("ACCESS_FILE", str(BASE_DIR / "access.json")))

_lock = threading.Lock()

_DEFAULT = {
    "enabled": True,
    "chats": [],
    "users": [],
}


def _admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
    if not raw:
        return set()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
            ids.add(int(part))
    return ids


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in _admin_ids()


def load_access() -> dict:
    if not ACCESS_FILE.exists():
        save_access(_DEFAULT)
    with _lock:
        data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
    return {
        "enabled": bool(data.get("enabled", True)),
        "chats": [int(x) for x in data.get("chats", [])],
        "users": [int(x) for x in data.get("users", [])],
    }


def save_access(data: dict) -> None:
    payload = {
        "enabled": bool(data.get("enabled", True)),
        "chats": sorted({int(x) for x in data.get("chats", [])}),
        "users": sorted({int(x) for x in data.get("users", [])}),
    }
    with _lock:
        ACCESS_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def is_allowed(chat_id: int | None, user_id: int | None) -> bool:
    if is_admin(user_id):
        return True
    data = load_access()
    if not data["enabled"]:
        return True
    if chat_id is not None and chat_id in data["chats"]:
        return True
    if user_id is not None and user_id in data["users"]:
        return True
    return False


def set_enabled(enabled: bool) -> None:
    data = load_access()
    data["enabled"] = enabled
    save_access(data)


def allow_chat(chat_id: int) -> bool:
    data = load_access()
    if chat_id in data["chats"]:
        return False
    data["chats"].append(chat_id)
    save_access(data)
    return True


def deny_chat(chat_id: int) -> bool:
    data = load_access()
    if chat_id not in data["chats"]:
        return False
    data["chats"] = [c for c in data["chats"] if c != chat_id]
    save_access(data)
    return True


def allow_user(user_id: int) -> bool:
    data = load_access()
    if user_id in data["users"]:
        return False
    data["users"].append(user_id)
    save_access(data)
    return True


def deny_user(user_id: int) -> bool:
    data = load_access()
    if user_id not in data["users"]:
        return False
    data["users"] = [u for u in data["users"] if u != user_id]
    save_access(data)
    return True
