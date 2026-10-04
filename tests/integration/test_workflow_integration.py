"""Integration tests for workflows (require API keys)."""

import os
import pytest

# Skip integration tests if no API keys
pytestmark = pytest.mark.skipif(
    not os.getenv("SERPAPI_API_KEY") or not os.getenv("OPENAI_API_KEY"),
    reason="Requires SERPAPI_API_KEY and OPENAI_API_KEY environment variables",
)


class TestFullWorkflowIntegration:
    """Integration tests that hit real APIs."""

    @pytest.mark.asyncio
    async def test_research_workflow_minimal(self):
        """Test minimal research workflow with real APIs."""
        from competitive_intel import create_research_workflow
        from competitive_intel.models import Entity, EntityType, ResearchBrief, SignalType

        brief = ResearchBrief(
            topic="OpenAI recent announcements",
            entities=[Entity(name="OpenAI", type=EntityType.COMPANY)],
            signal_types=[SignalType.PRODUCT_LAUNCH],
            time_range="past_week",
            depth="quick",
        )

        workflow = create_research_workflow()
        report = await workflow.run(brief)

        assert report is not None
        assert report.title
        assert len(report.signals) >= 0  # May find 0 or more
        assert report.confidence_score >= 0

    @pytest.mark.asyncio
    async def test_monitoring_workflow_single(self):
        """Test single monitoring cycle."""
        from competitive_intel.workflows import MonitoringWorkflowConfig, create_monitoring_workflow
        from competitive_intel.models import Entity, EntityType, ResearchBrief, SignalType

        brief = ResearchBrief(
            topic="Anthropic monitoring",
            entities=[Entity(name="Anthropic", type=EntityType.COMPANY)],
            signal_types=[SignalType.FUNDING, SignalType.PRODUCT_LAUNCH],
        )

        config = MonitoringWorkflowConfig(interval_seconds=3600)
        workflow = create_monitoring_workflow(brief, config=config)

        result = await workflow.run_once()
        assert result is not None