import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class QVerisCacheStats:
    enabled: bool
    ttl_seconds: int
    hits: int = 0
    misses: int = 0
    writes: int = 0


class QVerisFileCache:
    def __init__(self, cache_dir: str, enabled: bool, ttl_seconds: int):
        self.cache_dir = cache_dir
        self.stats = QVerisCacheStats(enabled=enabled, ttl_seconds=ttl_seconds)
        if self.stats.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _key(self, tool_id: str, parameters: Dict[str, Any]) -> str:
        payload = json.dumps({"tool_id": tool_id, "parameters": parameters}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, tool_id: str, parameters: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        if not self.stats.enabled:
            return None, False

        key = self._key(tool_id, parameters)
        path = self._path(key)
        if not os.path.exists(path):
            self.stats.misses += 1
            return None, False

        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
        except Exception:
            self.stats.misses += 1
            return None, False

        created_at = obj.get("created_at", 0)
        if self.stats.ttl_seconds > 0 and (time.time() - created_at) > self.stats.ttl_seconds:
            self.stats.misses += 1
            return None, False

        self.stats.hits += 1
        return obj.get("response"), True

    def set(self, tool_id: str, parameters: Dict[str, Any], response: str) -> None:
        if not self.stats.enabled:
            return

        key = self._key(tool_id, parameters)
        path = self._path(key)
        tmp_path = f"{path}.tmp"
        obj = {
            "created_at": time.time(),
            "tool_id": tool_id,
            "parameters": parameters,
            "response": response,
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp_path, path)
        self.stats.writes += 1


_DEFAULT_CACHE: Optional[QVerisFileCache] = None


def get_qveris_cache() -> QVerisFileCache:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is not None:
        return _DEFAULT_CACHE

    enabled = os.getenv("QVERIS_CACHE_ENABLED", "").strip() in {"1", "true", "True", "yes", "YES"}
    ttl_seconds_str = os.getenv("QVERIS_CACHE_TTL_SECONDS", "0").strip()
    try:
        ttl_seconds = int(ttl_seconds_str)
    except Exception:
        ttl_seconds = 0

    cache_dir = os.getenv("QVERIS_CACHE_DIR", ".cache/qveris").strip()
    _DEFAULT_CACHE = QVerisFileCache(cache_dir=cache_dir, enabled=enabled, ttl_seconds=ttl_seconds)
    return _DEFAULT_CACHE

