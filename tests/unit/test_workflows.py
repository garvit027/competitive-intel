"""Unit tests for workflows."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from competitive_intel.workflows import (
    ResearchWorkflow,
    ResearchWorkflowConfig,
    create_research_workflow,
)
from competitive_intel.models import (
    Entity,
    EntityType,
    ResearchBrief,
    SignalType,
)


class TestResearchWorkflow:
    """Tests for ResearchWorkflow."""

    @pytest.mark.asyncio
    async def test_create_workflow(self):
        workflow = create_research_workflow()
        assert workflow is not None
        assert workflow.graph is not None

    @pytest.mark.asyncio
    async def test_workflow_with_config(self):
        config = ResearchWorkflowConfig(enable_human_review=True)
        workflow = create_research_workflow(config=config)
        assert workflow.config.enable_human_review is True

    def test_visualize_workflow(self):
        workflow = create_research_workflow()
        mermaid = workflow.visualize()
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()