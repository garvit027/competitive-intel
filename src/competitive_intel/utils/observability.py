"""Observability setup for logging, metrics, and tracing."""

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from competitive_intel.config import get_settings


# Prometheus metrics
SEARCH_REQUESTS = Counter(
    "competitive_intel_search_requests_total",
    "Total search requests",
    ["engine", "status"],
)

SEARCH_LATENCY = Histogram(
    "competitive_intel_search_latency_seconds",
    "Search request latency",
    ["engine"],
)

AGENT_RUNS = Counter(
    "competitive_intel_agent_runs_total",
    "Total agent runs",
    ["agent", "status"],
)

AGENT_LATENCY = Histogram(
    "competitive_intel_agent_latency_seconds",
    "Agent run latency",
    ["agent"],
)

SIGNALS_DETECTED = Counter(
    "competitive_intel_signals_detected_total",
    "Total signals detected",
    ["signal_type", "severity"],
)

ACTIVE_WORKFLOWS = Gauge(
    "competitive_intel_active_workflows",
    "Number of active workflows",
)

CACHE_HITS = Counter(
    "competitive_intel_cache_hits_total",
    "Cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "competitive_intel_cache_misses_total",
    "Cache misses",
    ["cache_type"],
)


def setup_observability() -> None:
    """Initialize observability (logging, metrics, tracing)."""
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.observability.log_format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.observability.log_level),
    )

    # Setup OpenTelemetry tracing
    if settings.observability.otlp_endpoint:
        resource = Resource.create({"service.name": settings.observability.service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.observability.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

    # Start Prometheus metrics server
    if settings.observability.enabled:
        start_http_server(settings.observability.prometheus_port)

    logger = get_logger(__name__)
    logger.info(
        "observability_initialized",
        log_level=settings.observability.log_level,
        log_format=settings.observability.log_format,
        tracing_enabled=bool(settings.observability.otlp_endpoint),
        metrics_port=settings.observability.prometheus_port,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)


def get_metrics() -> dict[str, Any]:
    """Get metrics registry for custom metrics."""
    return {
        "search_requests": SEARCH_REQUESTS,
        "search_latency": SEARCH_LATENCY,
        "agent_runs": AGENT_RUNS,
        "agent_latency": AGENT_LATENCY,
        "signals_detected": SIGNALS_DETECTED,
        "active_workflows": ACTIVE_WORKFLOWS,
        "cache_hits": CACHE_HITS,
        "cache_misses": CACHE_MISSES,
    }


class TracedOperation:
    """Context manager for traced operations."""

    def __init__(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self) -> "TracedOperation":
        tracer = trace.get_tracer(__name__)
        self.span = tracer.start_span(self.name, attributes=self.attributes)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.span:
            if exc_type:
                self.span.record_exception(exc_val)
                self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
            self.span.end()