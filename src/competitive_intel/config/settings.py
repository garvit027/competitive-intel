"""Application settings using Pydantic Settings for type-safe configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LLMSettings(BaseModel):
    """LLM provider configuration."""

    provider: Literal["openai", "anthropic", "azure"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4096
    api_key: str = ""
    base_url: str | None = None
    organization: str | None = None
    timeout: float = 60.0
    max_retries: int = 3


class SerpApiSettings(BaseModel):
    """SerpApi configuration."""

    api_key: str = ""
    base_url: str = "https://serpapi.com"
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit_rpm: int = 100  # requests per minute
    default_location: str = "United States"
    default_language: str = "en"
    default_country: str = "us"
    safe_search: bool = True


class CacheSettings(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    backend: Literal["disk", "memory", "redis"] = "disk"
    directory: str = ".cache/serpapi"
    ttl_seconds: int = 3600  # 1 hour default
    max_size_mb: int = 500
    redis_url: str = "redis://localhost:6379/0"


class ObservabilitySettings(BaseModel):
    """Observability and monitoring configuration."""

    enabled: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    service_name: str = "competitive-intel"
    otlp_endpoint: str | None = None
    prometheus_port: int = 9090
    trace_sample_rate: float = 0.1


class DatabaseSettings(BaseModel):
    """Database configuration for persistence."""

    url: str = "sqlite:///data/competitive_intel.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class ReportSettings(BaseModel):
    """Report generation settings."""

    output_dir: str = "reports"
    template_dir: str = "templates"
    default_format: Literal["markdown", "html", "pdf"] = "markdown"
    include_citations: bool = True
    include_raw_data: bool = False
    max_report_size_mb: int = 10


class AgentSettings(BaseModel):
    """Agent behavior settings."""

    max_iterations: int = 10
    max_search_results: int = 10
    search_timeout: float = 30.0
    enable_human_in_loop: bool = False
    confidence_threshold: float = 0.7
    parallel_searches: int = 3


class Settings(BaseModel):
    """Main application settings."""

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    serpapi: SerpApiSettings = Field(default_factory=SerpApiSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    report: ReportSettings = Field(default_factory=ReportSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _load_settings_from_env() -> Settings:
    """Load settings from environment variables."""
    import os

    def get_env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def get_env_bool(key: str, default: bool = False) -> bool:
        val = os.environ.get(key, "").lower()
        return val in ("true", "1", "yes", "on") if val else default

    def get_env_int(key: str, default: int = 0) -> int:
        val = os.environ.get(key, "")
        return int(val) if val else default

    def get_env_float(key: str, default: float = 0.0) -> float:
        val = os.environ.get(key, "")
        return float(val) if val else default

    return Settings(
        environment=get_env("ENVIRONMENT", "development"),
        debug=get_env_bool("DEBUG", False),
        llm=LLMSettings(
            provider=get_env("CI_LLM_PROVIDER", "openai"),
            model=get_env("CI_LLM_MODEL", "gpt-4o-mini"),
            temperature=get_env_float("CI_LLM_TEMPERATURE", 0.1),
            max_tokens=get_env_int("CI_LLM_MAX_TOKENS", 4096),
            api_key=get_env("CI_LLM_API_KEY", ""),
            base_url=get_env("CI_LLM_BASE_URL", "") or None,
            organization=get_env("CI_LLM_ORGANIZATION", "") or None,
            timeout=get_env_float("CI_LLM_TIMEOUT", 60.0),
            max_retries=get_env_int("CI_LLM_MAX_RETRIES", 3),
        ),
        serpapi=SerpApiSettings(
            api_key=get_env("CI_SERPAPI_API_KEY", ""),
            base_url=get_env("CI_SERPAPI_BASE_URL", "https://serpapi.com"),
            timeout=get_env_float("CI_SERPAPI_TIMEOUT", 30.0),
            max_retries=get_env_int("CI_SERPAPI_MAX_RETRIES", 3),
            rate_limit_rpm=get_env_int("CI_SERPAPI_RATE_LIMIT_RPM", 100),
            default_location=get_env("CI_SERPAPI_DEFAULT_LOCATION", "United States"),
            default_language=get_env("CI_SERPAPI_DEFAULT_LANGUAGE", "en"),
            default_country=get_env("CI_SERPAPI_DEFAULT_COUNTRY", "us"),
            safe_search=get_env_bool("CI_SERPAPI_SAFE_SEARCH", True),
        ),
        cache=CacheSettings(
            enabled=get_env_bool("CI_CACHE_ENABLED", True),
            backend=get_env("CI_CACHE_BACKEND", "disk"),
            directory=get_env("CI_CACHE_DIRECTORY", ".cache/serpapi"),
            ttl_seconds=get_env_int("CI_CACHE_TTL_SECONDS", 3600),
            max_size_mb=get_env_int("CI_CACHE_MAX_SIZE_MB", 500),
            redis_url=get_env("CI_CACHE_REDIS_URL", "redis://localhost:6379/0"),
        ),
        observability=ObservabilitySettings(
            enabled=get_env_bool("CI_OBS_ENABLED", True),
            log_level=get_env("CI_OBS_LOG_LEVEL", "INFO"),
            log_format=get_env("CI_OBS_LOG_FORMAT", "console"),
            service_name=get_env("CI_OBS_SERVICE_NAME", "competitive-intel"),
            otlp_endpoint=get_env("CI_OBS_OTLP_ENDPOINT", "") or None,
            prometheus_port=get_env_int("CI_OBS_PROMETHEUS_PORT", 9090),
            trace_sample_rate=get_env_float("CI_OBS_TRACE_SAMPLE_RATE", 0.1),
        ),
        database=DatabaseSettings(
            url=get_env("CI_DB_URL", "sqlite:///data/competitive_intel.db"),
            echo=get_env_bool("CI_DB_ECHO", False),
            pool_size=get_env_int("CI_DB_POOL_SIZE", 5),
            max_overflow=get_env_int("CI_DB_MAX_OVERFLOW", 10),
        ),
        report=ReportSettings(
            output_dir=get_env("CI_REPORT_OUTPUT_DIR", "reports"),
            template_dir=get_env("CI_REPORT_TEMPLATE_DIR", "templates"),
            default_format=get_env("CI_REPORT_DEFAULT_FORMAT", "markdown"),
            include_citations=get_env_bool("CI_REPORT_INCLUDE_CITATIONS", True),
            include_raw_data=get_env_bool("CI_REPORT_INCLUDE_RAW_DATA", False),
            max_report_size_mb=get_env_int("CI_REPORT_MAX_REPORT_SIZE_MB", 10),
        ),
        agent=AgentSettings(
            max_iterations=get_env_int("CI_AGENT_MAX_ITERATIONS", 10),
            max_search_results=get_env_int("CI_AGENT_MAX_SEARCH_RESULTS", 10),
            search_timeout=get_env_float("CI_AGENT_SEARCH_TIMEOUT", 30.0),
            enable_human_in_loop=get_env_bool("CI_AGENT_ENABLE_HUMAN_IN_LOOP", False),
            confidence_threshold=get_env_float("CI_AGENT_CONFIDENCE_THRESHOLD", 0.7),
            parallel_searches=get_env_int("CI_AGENT_PARALLEL_SEARCHES", 3),
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return _load_settings_from_env()


# For backwards compatibility and easy access
settings = get_settings()