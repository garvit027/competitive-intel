"""Cache management for Competitive Intelligence Platform."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Generic, TypeVar

from diskcache import Cache

from competitive_intel.config import get_settings
from competitive_intel.utils.observability import get_logger, get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

T = TypeVar("T")


class CacheManager(Generic[T]):
    """Generic cache manager with TTL and size limits."""

    def __init__(
        self,
        namespace: str,
        ttl_seconds: int | None = None,
        max_size_mb: int | None = None,
    ) -> None:
        self.namespace = namespace
        settings = get_settings()

        self._cache = Cache(
            directory=str(Path(settings.cache.directory) / namespace),
            size_limit=(max_size_mb or settings.cache.max_size_mb) * 1024 * 1024,
        )
        self._ttl = ttl_seconds or settings.cache.ttl_seconds

    def get(self, key: str) -> T | None:
        """Get value from cache."""
        try:
            value = self._cache.get(key)
            if value is not None:
                metrics["cache_hits"].labels(cache_type=self.namespace).inc()
                logger.debug("cache_hit", namespace=self.namespace, key=key[:50])
                return value
            else:
                metrics["cache_misses"].labels(cache_type=self.namespace).inc()
                return None
        except Exception as e:
            logger.warning("cache_get_error", namespace=self.namespace, key=key[:50], error=str(e))
            return None

    def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        """Set value in cache with TTL."""
        try:
            self._cache.set(key, value, expire=ttl or self._ttl)
            logger.debug("cache_set", namespace=self.namespace, key=key[:50])
            return True
        except Exception as e:
            logger.warning("cache_set_error", namespace=self.namespace, key=key[:50], error=str(e))
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            self._cache.delete(key)
            return True
        except Exception as e:
            logger.warning("cache_delete_error", namespace=self.namespace, key=key[:50], error=str(e))
            return False

    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            self._cache.clear()
            logger.info("cache_cleared", namespace=self.namespace)
            return True
        except Exception as e:
            logger.warning("cache_clear_error", namespace=self.namespace, error=str(e))
            return False

    def make_key(self, *parts: Any) -> str:
        """Create a cache key from parts."""
        key_data = ":".join(str(p) for p in parts)
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            return {
                "size": self._cache.volume(),
                "entries": len(self._cache),
                "directory": str(self._cache.directory),
            }
        except Exception:
            return {"error": "Failed to get stats"}

    def close(self) -> None:
        """Close cache connection."""
        self._cache.close()


# Global cache managers
_cache_managers: dict[str, CacheManager] = {}


def get_cache_manager(namespace: str, **kwargs: Any) -> CacheManager:
    """Get or create a cache manager for a namespace."""
    if namespace not in _cache_managers:
        _cache_managers[namespace] = CacheManager(namespace, **kwargs)
    return _cache_managers[namespace]


class SearchCache:
    """Specialized cache for search results."""

    def __init__(self) -> None:
        self._cache = get_cache_manager("search")

    def get_search_results(self, query_hash: str) -> list[dict] | None:
        """Get cached search results."""
        return self._cache.get(f"results:{query_hash}")

    def set_search_results(self, query_hash: str, results: list[dict], ttl: int | None = None) -> bool:
        """Cache search results."""
        return self._cache.set(f"results:{query_hash}", results, ttl)

    def get_query_hash(self, query: str, engine: str, params: dict) -> str:
        """Generate hash for a search query."""
        key_data = f"{engine}:{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]


class EntityCache:
    """Specialized cache for entity data."""

    def __init__(self) -> None:
        self._cache = get_cache_manager("entities")

    def get_entity(self, entity_id: str) -> dict | None:
        return self._cache.get(f"entity:{entity_id}")

    def set_entity(self, entity_id: str, data: dict, ttl: int | None = None) -> bool:
        return self._cache.set(f"entity:{entity_id}", data, ttl)

    def get_entities_by_name(self, name: str) -> list[dict] | None:
        return self._cache.get(f"name:{name.lower()}")

    def set_entities_by_name(self, name: str, entities: list[dict], ttl: int | None = None) -> bool:
        return self._cache.set(f"name:{name.lower()}", entities, ttl)


class ReportCache:
    """Specialized cache for generated reports."""

    def __init__(self) -> None:
        self._cache = get_cache_manager("reports")

    def get_report(self, report_id: str) -> dict | None:
        return self._cache.get(f"report:{report_id}")

    def set_report(self, report_id: str, report_data: dict, ttl: int | None = None) -> bool:
        return self._cache.set(f"report:{report_id}", report_data, ttl)