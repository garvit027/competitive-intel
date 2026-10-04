"""Research workflow using LangGraph for multi-agent orchestration."""

import asyncio
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from competitive_intel.agents import (
    AnalystAgent,
    ResearcherAgent,
    SynthesizerAgent,
    create_analyst_agent,
    create_researcher_agent,
    create_synthesizer_agent,
)
from competitive_intel.models import AgentState, ResearchBrief, ResearchReport
from competitive_intel.tools.search_tools import SearchToolset


class WorkflowConfig(BaseModel):
    """Configuration for research workflow."""

    enable_human_review: bool = False
    human_review_step: Literal["after_research", "after_analysis", "after_synthesis"] = "after_synthesis"
    max_parallel_agents: int = 3
    timeout_seconds: int = 300
    save_intermediate_state: bool = True


class ResearchWorkflow:
    """
    LangGraph workflow orchestrating the full research pipeline:
    Researcher -> Analyst -> Synthesizer
    """

    def __init__(
        self,
        config: WorkflowConfig | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        synthesizer: SynthesizerAgent | None = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        self.config = config or WorkflowConfig()
        self.researcher = researcher or create_researcher_agent()
        self.analyst = analyst or create_analyst_agent()
        self.synthesizer = synthesizer or create_synthesizer_agent()
        self.search_tools = search_tools or SearchToolset()
        self._graph: CompiledStateGraph | None = None
        self._checkpointer = MemorySaver()

    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("synthesizer", self._synthesizer_node)

        # Add conditional human review node if enabled
        if self.config.enable_human_review:
            workflow.add_node("human_review", self._human_review_node)

        # Define edges
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "analyst")
        workflow.add_edge("analyst", "synthesizer")

        if self.config.enable_human_review:
            if self.config.human_review_step == "after_research":
                workflow.add_edge("researcher", "human_review")
                workflow.add_edge("human_review", "analyst")
            elif self.config.human_review_step == "after_analysis":
                workflow.add_edge("analyst", "human_review")
                workflow.add_edge("human_review", "synthesizer")
            else:  # after_synthesis
                workflow.add_edge("synthesizer", "human_review")
                workflow.add_edge("human_review", END)
        else:
            workflow.add_edge("synthesizer", END)

        return workflow.compile(checkpointer=self._checkpointer)

    @property
    def graph(self) -> CompiledStateGraph:
        """Get or build the compiled graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    async def _researcher_node(self, state: AgentState) -> AgentState:
        """Researcher agent node."""
        return await self.researcher.execute(state)

    async def _analyst_node(self, state: AgentState) -> AgentState:
        """Analyst agent node."""
        return await self.analyst.execute(state)

    async def _synthesizer_node(self, state: AgentState) -> AgentState:
        """Synthesizer agent node."""
        return await self.synthesizer.execute(state)

    async def _human_review_node(self, state: AgentState) -> AgentState:
        """Human review checkpoint - pauses for human input."""
        # In production, this would integrate with a human-in-the-loop system
        # For now, just log and continue
        state.metadata["human_review_required"] = True
        state.metadata["review_step"] = self.config.human_review_step
        return state

    async def run(
        self,
        brief: ResearchBrief,
        thread_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> ResearchReport:
        """
        Run the complete research workflow.

        Args:
            brief: Research brief defining scope and parameters
            thread_id: Optional thread ID for checkpointing
            config: Additional LangGraph config

        Returns:
            Completed ResearchReport
        """
        thread_id = thread_id or str(uuid4())
        run_config = {
            "configurable": {"thread_id": thread_id},
            **(config or {}),
        }

        initial_state = AgentState(brief=brief)

        # Execute workflow
        final_state = await self.graph.ainvoke(initial_state, run_config)

        # Extract report
        if isinstance(final_state, dict):
            report = final_state.get("report")
        else:
            report = final_state.report

        if not report:
            raise RuntimeError("Workflow completed but no report generated")

        return report

    async def run_streaming(
        self,
        brief: ResearchBrief,
        thread_id: str | None = None,
    ) -> Any:
        """Run workflow with streaming updates."""
        thread_id = thread_id or str(uuid4())
        run_config = {"configurable": {"thread_id": thread_id}}

        initial_state = AgentState(brief=brief)

        async for event in self.graph.astream(initial_state, run_config, stream_mode="updates"):
            yield event

    def get_state(self, thread_id: str) -> AgentState | None:
        """Get current state for a thread."""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)
            return state.values if state else None
        except Exception:
            return None

    def visualize(self) -> str:
        """Get Mermaid diagram of the workflow."""
        return self.graph.get_graph().draw_mermaid()


def create_research_workflow(
    config: WorkflowConfig | None = None,
    **agent_kwargs: Any,
) -> ResearchWorkflow:
    """Factory function to create a ResearchWorkflow."""
    return ResearchWorkflow(config=config, **agent_kwargs)