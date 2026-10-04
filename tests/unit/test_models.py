"""Unit tests for domain models."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from competitive_intel.models import (
    AgentState,
    Citation,
    CompetitiveSignal,
    ConfidenceLevel,
    Entity,
    EntityType,
    ResearchBrief,
    ReportSection,
    ResearchReport,
    SearchEngine,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchResultType,
    SignalType,
    SourceType,
)


class TestEntity:
    """Tests for Entity model."""

    def test_create_entity(self):
        entity = Entity(name="Test Corp", type=EntityType.COMPANY)
        assert entity.name == "Test Corp"
        assert entity.type == EntityType.COMPANY
        assert entity.id is not None

    def test_entity_name_validation(self):
        entity = Entity(name="  Test Corp  ", type=EntityType.COMPANY)
        assert entity.name == "Test Corp"

    def test_entity_aliases(self):
        entity = Entity(name="Test", type=EntityType.COMPANY, aliases=["Test Inc", "Test LLC"])
        assert len(entity.aliases) == 2


class TestSearchQuery:
    """Tests for SearchQuery model."""

    def test_create_search_query(self):
        query = SearchQuery(query="test query")
        assert query.query == "test query"
        assert query.engines == [SearchEngine.GOOGLE_LIGHT]
        assert query.num_results == 10

    def test_search_query_with_options(self):
        query = SearchQuery(
            query="test",
            engines=[SearchEngine.GOOGLE_NEWS, SearchEngine.BING],
            location="San Francisco",
            date_range="past_week",
            num_results=20,
        )
        assert len(query.engines) == 2
        assert query.location == "San Francisco"
        assert query.date_range == "past_week"
        assert query.num_results == 20


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self):
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            source="web",
            engine=SearchEngine.GOOGLE_LIGHT,
            result_type=SearchResultType.ORGANIC,
            position=1,
        )
        assert result.title == "Test"
        assert result.url == "https://example.com"

    def test_url_validation(self):
        with pytest.raises(ValueError):
            SearchResult(
                title="Test",
                url="not-a-url",
                snippet="Test",
                source="web",
                engine=SearchEngine.GOOGLE_LIGHT,
                result_type=SearchResultType.ORGANIC,
                position=1,
            )


class TestCompetitiveSignal:
    """Tests for CompetitiveSignal model."""

    def test_create_signal(self):
        entity_id = uuid4()
        signal = CompetitiveSignal(
            entity_id=entity_id,
            signal_type=SignalType.PRODUCT_LAUNCH,
            title="New Product Launch",
            summary="Company launched new product",
            confidence=ConfidenceLevel.HIGH,
            severity="high",
        )
        assert signal.entity_id == entity_id
        assert signal.signal_type == SignalType.PRODUCT_LAUNCH
        assert signal.confidence == ConfidenceLevel.HIGH
        assert signal.severity == "high"

    def test_severity_validation(self):
        entity_id = uuid4()
        with pytest.raises(ValueError):
            CompetitiveSignal(
                entity_id=entity_id,
                signal_type=SignalType.PRODUCT_LAUNCH,
                title="Test",
                summary="Test",
                severity="invalid",
            )


class TestResearchBrief:
    """Tests for ResearchBrief model."""

    def test_create_brief(self):
        brief = ResearchBrief(topic="Test Topic")
        assert brief.topic == "Test Topic"
        assert brief.depth == "standard"
        assert brief.time_range == "past_month"

    def test_brief_with_entities(self):
        brief = ResearchBrief(
            topic="Test",
            entities=[Entity(name="Co1", type=EntityType.COMPANY)],
            signal_types=[SignalType.FUNDING],
        )
        assert len(brief.entities) == 1
        assert len(brief.signal_types) == 1


class TestResearchReport:
    """Tests for ResearchReport model."""

    def test_create_report(self):
        brief_id = uuid4()
        report = ResearchReport(
            brief_id=brief_id,
            title="Test Report",
            executive_summary="Summary",
        )
        assert report.brief_id == brief_id
        assert report.title == "Test Report"
        assert report.confidence_score == 0.0


class TestAgentState:
    """Tests for AgentState model."""

    def test_initial_state(self):
        state = AgentState()
        assert state.current_step == ""
        assert state.errors == []
        assert state.warnings == []

    def test_state_with_brief(self):
        brief = ResearchBrief(topic="Test")
        state = AgentState(brief=brief)
        assert state.brief is not None
        assert state.brief.topic == "Test"


class TestCitation:
    """Tests for Citation model."""

    def test_create_citation(self):
        citation = Citation(
            source_id=uuid4(),
            claim="Test claim",
            url="https://example.com",
            title="Test Source",
            source_type=SourceType.WEB,
        )
        assert citation.claim == "Test claim"
        assert citation.confidence == ConfidenceLevel.MEDIUM


class TestReportSection:
    """Tests for ReportSection model."""

    def test_create_section(self):
        section = ReportSection(
            title="Test Section",
            content="Section content",
            level=1,
        )
        assert section.title == "Test Section"
        assert section.level == 1