"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set test environment variables
os.environ.setdefault("CI_SERPAPI_API_KEY", "test-key")
os.environ.setdefault("CI_LLM_API_KEY", "test-key")
os.environ.setdefault("CI_LLM_PROVIDER", "openai")
os.environ.setdefault("CI_LLM_MODEL", "gpt-4o-mini")
os.environ.setdefault("ENVIRONMENT", "development")


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    mock.astream = AsyncMock(return_value=iter([MagicMock(content="Test")]))
    mock.with_structured_output = MagicMock(return_value=mock)
    return mock


@pytest.fixture
def sample_research_brief():
    """Sample research brief for testing."""
    from competitive_intel.models import Entity, EntityType, ResearchBrief, SignalType

    return ResearchBrief(
        topic="Test Topic",
        entities=[
            Entity(name="Test Company", type=EntityType.COMPANY),
        ],
        signal_types=[SignalType.PRODUCT_LAUNCH, SignalType.FUNDING],
        time_range="past_week",
        depth="quick",
    )


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    from competitive_intel.models import SearchEngine, SearchQuery, SearchResponse, SearchResult, SearchResultType
    from datetime import UTC, datetime

    return SearchResponse(
        query=SearchQuery(query="test query"),
        results=[
            SearchResult(
                title="Test Result 1",
                url="https://example.com/1",
                snippet="This is a test snippet about product launch",
                source="web",
                engine=SearchEngine.GOOGLE_LIGHT,
                result_type=SearchResultType.ORGANIC,
                position=1,
            ),
            SearchResult(
                title="Test Result 2",
                url="https://example.com/2",
                snippet="Another test about funding round",
                source="news",
                engine=SearchEngine.GOOGLE_NEWS,
                result_type=SearchResultType.NEWS,
                position=2,
            ),
        ],
        total_results=2,
        search_time_ms=100.0,
    )