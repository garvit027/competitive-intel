"""Core SerpApi integration with caching, rate limiting, and error handling."""

import asyncio
import hashlib
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

import structlog
from diskcache import Cache
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from competitive_intel.config import get_settings
from competitive_intel.models import (
    SearchEngine,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchResultType,
)

logger = structlog.get_logger(__name__)


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""

    rate_per_minute: int
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.rate_per_minute)
        self.last_update = time.monotonic()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.rate_per_minute, self.tokens + elapsed * self.rate_per_minute / 60.0)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    self.last_update = now
                    return

                wait_time = (1.0 - self.tokens) * 60.0 / self.rate_per_minute
                await asyncio.sleep(min(wait_time, 1.0))


class SerpApiError(Exception):
    """Base exception for SerpApi errors."""

    def __init__(self, message: str, engine: str | None = None, query: str | None = None) -> None:
        super().__init__(message)
        self.engine = engine
        self.query = query


class SerpApiRateLimitError(SerpApiError):
    """Rate limit exceeded."""

    pass


class SerpApiTimeoutError(SerpApiError):
    """Request timeout."""

    pass


class SerpApiTools:
    """
    High-level SerpApi tools with caching, rate limiting, and retries.

    This class wraps serpapi-search-tools-python and adds:
    - Disk-based caching with TTL
    - Token bucket rate limiting
    - Exponential backoff retries
    - Structured logging
    - Metrics collection
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self._cache: Cache | None = None
        self._rate_limiter: RateLimiter | None = None
        self._tools: dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize cache, rate limiter, and search tools."""
        if self._initialized:
            return

        # Initialize cache
        if self.settings.cache.enabled:
            self._cache = Cache(
                directory=self.settings.cache.directory,
                size_limit=self.settings.cache.max_size_mb * 1024 * 1024,
            )

        # Initialize rate limiter
        self._rate_limiter = RateLimiter(rate_per_minute=self.settings.serpapi.rate_limit_rpm)

        # Initialize search tools
        await self._init_search_tools()

        self._initialized = True
        logger.info("serpapi_tools_initialized", rate_limit_rpm=self.settings.serpapi.rate_limit_rpm)

    async def _init_search_tools(self) -> None:
        """Initialize all search tools from serpapi-search-tools-python."""
        from serpapi_search_tools import (
            web_search,
            news_search,
            shopping_search,
            maps_search,
            images_search,
            videos_search,
            flights_search,
            hotels_search,
            travel_explore_search,
        )

        common_kwargs = {
            "default_params": {
                "hl": self.settings.serpapi.default_language,
                "gl": self.settings.serpapi.default_country,
                "location": self.settings.serpapi.default_location,
                "safe": "active" if self.settings.serpapi.safe_search else "off",
            },
            "result_limit": self.settings.agent.max_search_results,
            "response_format": "markdown",
            "mode": "compact",
        }

        self._tools = {
            "web": web_search(**common_kwargs, allowed_engines=["google_light", "bing", "duckduckgo"]),
            "news": news_search(**common_kwargs),
            "shopping": shopping_search(**common_kwargs, allowed_engines=["google_shopping", "amazon", "ebay"]),
            "maps": maps_search(**common_kwargs),
            "images": images_search(**common_kwargs),
            "videos": videos_search(**common_kwargs),
            "flights": flights_search(**common_kwargs),
            "hotels": hotels_search(**common_kwargs),
            "travel_explore": travel_explore_search(**common_kwargs),
        }

    def _get_cache_key(self, tool_name: str, query: SearchQuery) -> str:
        """Generate cache key for a search query."""
        key_data = f"{tool_name}:{query.query}:{query.engines}:{query.location}:{query.language}:{query.country}:{query.num_results}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    async def _execute_with_retry(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with retry logic."""
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self.settings.serpapi.max_retries),
            wait=wait_exponential_jitter(initial=1, max=10),
            retry=retry_if_exception_type((SerpApiTimeoutError, SerpApiRateLimitError, ConnectionError)),
            reraise=True,
        )

        return await retrying(func, *args, **kwargs)

    async def search(self, query: SearchQuery, tool_name: str = "web") -> SearchResponse:
        """
        Execute a search query with caching and rate limiting.

        Args:
            query: Structured search query
            tool_name: Name of the search tool to use

        Returns:
            SearchResponse with results
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.perf_counter()
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown search tool: {tool_name}")

        # Check cache
        cache_key = self._get_cache_key(tool_name, query)
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug("cache_hit", tool=tool_name, query=query.query[:50])
                return SearchResponse.model_validate(cached)

        # Rate limit
        await self._rate_limiter.acquire()

        # Build parameters for serpapi-search-tools
        params = {"q": query.query}
        if query.location:
            params["location"] = query.location
        if query.language:
            params["hl"] = query.language
        if query.country:
            params["gl"] = query.country
        if query.date_range:
            params["tbs"] = f"qdr:{query.date_range[5:]}" if query.date_range.startswith("past_") else query.date_range

        # Execute search
        try:
            logger.info("search_executing", tool=tool_name, query=query.query[:100])
            result = await self._execute_with_retry(tool.ainvoke, params)

            search_time_ms = (time.perf_counter() - start_time) * 1000

            # Parse results
            response = self._parse_results(query, result, tool_name, search_time_ms)

            # Cache result
            if self._cache:
                self._cache.set(cache_key, response.model_dump(), expire=self.settings.cache.ttl_seconds)

            logger.info(
                "search_completed",
                tool=tool_name,
                query=query.query[:50],
                results=len(response.results),
                time_ms=search_time_ms,
            )
            return response

        except Exception as e:
            search_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error("search_failed", tool=tool_name, query=query.query[:50], error=str(e))
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=search_time_ms,
                errors=[str(e)],
            )

    def _parse_results(self, query: SearchQuery, raw_result: Any, tool_name: str, search_time_ms: float) -> SearchResponse:
        """Parse raw search results into structured format."""
        results: list[SearchResult] = []

        # Handle markdown response (default)
        if isinstance(raw_result, str):
            # Parse markdown results - simplified for now
            lines = raw_result.split("\n")
            current_result: dict[str, Any] = {}
            position = 0

            for line in lines:
                if line.startswith("## ") or line.startswith("### "):
                    if current_result:
                        position += 1
                        results.append(
                            SearchResult(
                                title=current_result.get("title", ""),
                                url=current_result.get("url", ""),
                                snippet=current_result.get("snippet", ""),
                                source=tool_name,
                                engine=SearchEngine.GOOGLE_LIGHT,
                                result_type=SearchResultType.ORGANIC,
                                position=position,
                                metadata=current_result.get("metadata", {}),
                            )
                        )
                    current_result = {"title": line.lstrip("# ").strip(), "metadata": {}}
                elif line.startswith("[") and "](" in line and line.endswith(")"):
                    # Link format: [title](url)
                    import re

                    match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", line)
                    if match:
                        current_result["title"] = match.group(1)
                        current_result["url"] = match.group(2)
                elif line.startswith("> ") or line.startswith("- "):
                    current_result.setdefault("snippet", "")
                    current_result["snippet"] += line[2:] + " "
                elif ":" in line and not line.startswith(" "):
                    key, value = line.split(":", 1)
                    current_result["metadata"][key.strip().lower()] = value.strip()

            # Don't forget the last result
            if current_result:
                position += 1
                results.append(
                    SearchResult(
                        title=current_result.get("title", ""),
                        url=current_result.get("url", ""),
                        snippet=current_result.get("snippet", ""),
                        source=tool_name,
                        engine=SearchEngine.GOOGLE_LIGHT,
                        result_type=SearchResultType.ORGANIC,
                        position=position,
                        metadata=current_result.get("metadata", {}),
                    )
                )

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
            metadata={"tool": tool_name, "raw_length": len(str(raw_result))},
        )

    async def search_multiple(self, queries: list[SearchQuery], tool_name: str = "web") -> list[SearchResponse]:
        """Execute multiple searches in parallel with concurrency control."""
        semaphore = asyncio.Semaphore(self.settings.agent.parallel_searches)

        async def bounded_search(q: SearchQuery) -> SearchResponse:
            async with semaphore:
                return await self.search(q, tool_name)

        return await asyncio.gather(*[bounded_search(q) for q in queries])

    async def close(self) -> None:
        """Clean up resources."""
        if self._cache:
            self._cache.close()
        logger.info("serpapi_tools_closed")


# Global instance
_tools_instance: SerpApiTools | None = None


async def get_serpapi_tools() -> SerpApiTools:
    """Get or create the global SerpApiTools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = SerpApiTools()
        await _tools_instance.initialize()
    return _tools_instance


async def close_serpapi_tools() -> None:
    """Close the global SerpApiTools instance."""
    global _tools_instance
    if _tools_instance:
        await _tools_instance.close()
        _tools_instance = None