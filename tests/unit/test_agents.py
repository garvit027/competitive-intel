"""Unit tests for agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from competitive_intel.agents import (
    AnalystAgent,
    ResearcherAgent,
    SynthesizerAgent,
    create_analyst_agent,
    create_researcher_agent,
    create_synthesizer_agent,
)
from competitive_intel.models import (
    AgentState,
    ConfidenceLevel,
    Entity,
    EntityType,
    ResearchBrief,
    SearchEngine,
    SearchResponse,
    SearchResult,
    SearchResultType,
    SignalType,
)
from competitive_intel.tools.search_tools import SearchToolset


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    mock.with_structured_output = MagicMock(return_value=mock)
    return mock


@pytest.fixture
def sample_brief():
    return ResearchBrief(
        topic="Test Topic",
        entities=[Entity(name="TestCo", type=EntityType.COMPANY)],
        signal_types=[SignalType.PRODUCT_LAUNCH],
        time_range="past_week",
        depth="quick",
    )


@pytest.fixture
def sample_search_results():
    return SearchResponse(
        query=type('obj', (object,), {'query': 'test', 'engines': [SearchEngine.GOOGLE_LIGHT]})(),
        results=[
            SearchResult(
                title="TestCo launches new product",
                url="https://example.com/1",
                snippet="TestCo announced a new AI product today",
                source="web",
                engine=SearchEngine.GOOGLE_LIGHT,
                result_type=SearchResultType.ORGANIC,
                position=1,
            ),
        ],
        total_results=1,
        search_time_ms=100.0,
    )


class TestResearcherAgent:
    """Tests for ResearcherAgent."""

    @pytest.mark.asyncio
    async def test_create_researcher_agent(self, mock_llm):
        agent = create_researcher_agent(llm=mock_llm)
        assert agent.name == "researcher"
        assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_researcher_execute(self, mock_llm, sample_brief):
        agent = create_researcher_agent(llm=mock_llm)

        # Mock the structured output
        mock_plan = MagicMock()
        mock_plan.queries = []
        mock_plan.entities_to_research = ["TestCo"]
        mock_plan.signal_types_to_track = [SignalType.PRODUCT_LAUNCH]
        mock_plan.reasoning = "Test plan"
        mock_plan.estimated_searches = 5
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_plan)

        state = AgentState(brief=sample_brief)
        result = await agent.execute(state)

        assert result.current_step == "researcher.completed"
        assert "research_plan" in result.metadata


class TestAnalystAgent:
    """Tests for AnalystAgent."""

    @pytest.mark.asyncio
    async def test_create_analyst_agent(self, mock_llm):
        agent = create_analyst_agent(llm=mock_llm)
        assert agent.name == "analyst"

    @pytest.mark.asyncio
    async def test_analyst_execute_no_results(self, mock_llm, sample_brief):
        agent = create_analyst_agent(llm=mock_llm)
        state = AgentState(brief=sample_brief, search_results=[])
        result = await agent.execute(state)
        assert "No search results to analyze" in result.warnings[0]


class TestSynthesizerAgent:
    """Tests for SynthesizerAgent."""

    @pytest.mark.asyncio
    async def test_create_synthesizer_agent(self, mock_llm):
        agent = create_synthesizer_agent(llm=mock_llm)
        assert agent.name == "synthesizer"

    @pytest.mark.asyncio
    async def test_synthesizer_execute_no_signals(self, mock_llm, sample_brief):
        agent = create_synthesizer_agent(llm=mock_llm)
        state = AgentState(brief=sample_brief, signals=[])
        result = await agent.execute(state)
        assert "No signals to synthesize" in result.warnings[0]