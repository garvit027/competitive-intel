"""Core domain models for Competitive Intelligence Platform."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class SearchEngine(str, Enum):
    """Supported search engines."""

    GOOGLE = "google"
    GOOGLE_LIGHT = "google_light"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    YAHOO = "yahoo"
    GOOGLE_NEWS = "google_news"
    GOOGLE_SHOPPING = "google_shopping"
    AMAZON = "amazon"
    EBAY = "ebay"
    YOUTUBE = "youtube"
    GOOGLE_MAPS = "google_maps"
    GOOGLE_FLIGHTS = "google_flights"
    GOOGLE_HOTELS = "google_hotels"
    GOOGLE_SCHOLAR = "google_scholar"
    APPLE_APP_STORE = "apple_app_store"
    GOOGLE_PLAY = "google_play"


class SearchResultType(str, Enum):
    """Types of search results."""

    ORGANIC = "organic"
    NEWS = "news"
    SHOPPING = "shopping"
    MAPS = "maps"
    IMAGES = "images"
    VIDEOS = "videos"
    FLIGHTS = "flights"
    HOTELS = "hotels"
    ANSWER_BOX = "answer_box"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    RELATED_QUESTIONS = "related_questions"
    RELATED_SEARCHES = "related_searches"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted information."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class SourceType(str, Enum):
    """Source types for citations."""

    WEB = "web"
    NEWS = "news"
    ACADEMIC = "academic"
    FINANCIAL = "financial"
    SOCIAL = "social"
    OFFICIAL = "official"
    USER_GENERATED = "user_generated"


class EntityType(str, Enum):
    """Types of entities tracked."""

    COMPANY = "company"
    PRODUCT = "product"
    PERSON = "person"
    TECHNOLOGY = "technology"
    MARKET = "market"
    EVENT = "event"
    FINANCIAL_METRIC = "financial_metric"
    REGULATORY = "regulatory"


class SignalType(str, Enum):
    """Types of competitive signals."""

    PRODUCT_LAUNCH = "product_launch"
    FUNDING = "funding"
    ACQUISITION = "acquisition"
    PARTNERSHIP = "partnership"
    LEADERSHIP_CHANGE = "leadership_change"
    PRICING_CHANGE = "pricing_change"
    MARKET_EXPANSION = "market_expansion"
    REGULATORY_ACTION = "regulatory_action"
    PATENT_FILING = "patent_filing"
    HIRING_SURGE = "hiring_surge"
    LAYOFFS = "layoffs"
    TECHNOLOGY_ADOPTION = "technology_adoption"
    CUSTOMER_WIN = "customer_win"
    SECURITY_INCIDENT = "security_incident"
    EARNINGS_REPORT = "earnings_report"
    STRATEGIC_ANNOUNCEMENT = "strategic_announcement"


class SearchResult(BaseModel):
    """Normalized search result from any engine."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    url: str
    snippet: str
    source: str
    engine: SearchEngine
    result_type: SearchResultType
    position: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_data: dict[str, Any] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class Citation(BaseModel):
    """Citation for a claim or finding."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    claim: str
    quote: str | None = None
    url: str
    title: str
    source_type: SourceType
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    """Tracked entity (company, product, person, etc.)."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    type: EntityType
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    website: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()


class CompetitiveSignal(BaseModel):
    """A competitive intelligence signal."""

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID
    signal_type: SignalType
    title: str
    summary: str
    description: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    severity: Literal["critical", "high", "medium", "low", "informational"] = "medium"
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = ["critical", "high", "medium", "low", "informational"]
        if v not in valid:
            raise ValueError(f"Severity must be one of {valid}")
        return v


class SearchQuery(BaseModel):
    """Structured search query."""

    query: str
    engines: list[SearchEngine] = Field(default_factory=lambda: [SearchEngine.GOOGLE_LIGHT])
    location: str | None = None
    language: str | None = None
    country: str | None = None
    date_range: str | None = None  # e.g., "past_week", "past_month"
    safe_search: bool = True
    num_results: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response from search operation."""

    query: SearchQuery
    results: list[SearchResult] = Field(default_factory=list)
    total_results: int = 0
    search_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchBrief(BaseModel):
    """Input brief for research task."""

    id: UUID = Field(default_factory=uuid4)
    topic: str
    entities: list[Entity] = Field(default_factory=list)
    signal_types: list[SignalType] = Field(default_factory=list)
    time_range: str = "past_month"
    depth: Literal["quick", "standard", "deep"] = "standard"
    focus_areas: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    required_sources: list[SourceType] = Field(default_factory=list)
    output_format: Literal["brief", "detailed", "executive"] = "detailed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchReport(BaseModel):
    """Generated research report."""

    id: UUID = Field(default_factory=uuid4)
    brief_id: UUID
    title: str
    executive_summary: str
    sections: list["ReportSection"] = Field(default_factory=list)
    signals: list[CompetitiveSignal] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence_score: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportSection(BaseModel):
    """A section in a research report."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    content: str
    level: int = 1
    order: int = 0
    citations: list[Citation] = Field(default_factory=list)
    signals: list[CompetitiveSignal] = Field(default_factory=list)
    subsections: list["ReportSection"] = Field(default_factory=list)


class AgentState(BaseModel):
    """State passed between agents in the workflow."""

    brief: ResearchBrief | None = None
    search_queries: list[SearchQuery] = Field(default_factory=list)
    search_results: list[SearchResponse] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    signals: list[CompetitiveSignal] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    report: ResearchReport | None = None
    current_step: str = ""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Forward references
ReportSection.model_rebuild()
ResearchReport.model_rebuild()