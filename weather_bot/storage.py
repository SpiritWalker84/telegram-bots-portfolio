from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class UserStorage:
    """Thread-safe JSON storage for user preferences."""

    def __init__(self, file_path: str | Path = "User_Data.json") -> None:
        self.file_path = Path(file_path)
        self._lock = Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _read_all(self) -> dict[str, Any]:
        self._ensure_file()
        raw = self.file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            return {}
        except json.JSONDecodeError:
            # Corrupted data should not crash the bot.
            return {}

    def _write_all(self, payload: dict[str, Any]) -> None:
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_user(self, user_id: int) -> dict[str, Any]:
        key = str(user_id)
        with self._lock:
            users = self._read_all()
            user = users.get(key)
            if isinstance(user, dict):
                return user
            return {}

    def save_user(self, user_id: int, data: dict[str, Any]) -> None:
        key = str(user_id)
        with self._lock:
            users = self._read_all()
            users[key] = data
            self._write_all(users)


_default_storage = UserStorage()


def load_user(user_id: int) -> dict[str, Any]:
    return _default_storage.load_user(user_id)


def save_user(user_id: int, data: dict[str, Any]) -> None:
    _default_storage.save_user(user_id, data)
