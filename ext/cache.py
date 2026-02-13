from datetime import datetime, timedelta
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[Any, tuple[Any, datetime]] = {}

    def get(self, key: Any) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if datetime.utcnow() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: Any, value: Any):
        self._store[key] = (value, datetime.utcnow() + self.ttl)

    def clear(self):
        self._store.clear()

    def delete(self, key: Any):
        self._store.pop(key, None)
