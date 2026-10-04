"""Monitoring workflow for continuous competitive intelligence."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from competitive_intel.agents import MonitorAgent, create_monitor_agent
from competitive_intel.agents.monitor import MonitorConfig
from competitive_intel.models import AgentState, CompetitiveSignal, ResearchBrief
from competitive_intel.tools.search_tools import SearchToolset


class MonitoringWorkflowConfig(BaseModel):
    """Configuration for monitoring workflow."""

    interval_seconds: int = 3600  # 1 hour default
    max_concurrent_runs: int = 1
    alert_on_new_signals: bool = True
    alert_threshold: str = "medium"
    persist_signals: bool = True


class MonitoringWorkflow:
    """
    LangGraph workflow for continuous monitoring.
    Runs periodically and maintains signal history.
    """

    def __init__(
        self,
        monitor_config: MonitorConfig,
        config: MonitoringWorkflowConfig | None = None,
        monitor_agent: MonitorAgent | None = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        self.monitor_config = monitor_config
        self.config = config or MonitoringWorkflowConfig()
        self.monitor_agent = monitor_agent or create_monitor_agent(monitor_config)
        self.search_tools = search_tools or SearchToolset()
        self._graph: CompiledStateGraph | None = None
        self._checkpointer = MemorySaver()
        self._running = False
        self._task: asyncio.Task | None = None

    def _build_graph(self) -> CompiledStateGraph:
        """Build the monitoring graph."""
        workflow = StateGraph(AgentState)

        workflow.add_node("monitor", self._monitor_node)
        workflow.add_node("alert", self._alert_node)
        workflow.add_node("persist", self._persist_node)

        workflow.set_entry_point("monitor")
        workflow.add_edge("monitor", "alert")
        workflow.add_edge("alert", "persist")
        workflow.add_edge("persist", END)

        return workflow.compile(checkpointer=self._checkpointer)

    @property
    def graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    async def _monitor_node(self, state: AgentState) -> AgentState:
        """Run monitoring cycle."""
        return await self.monitor_agent.execute(state)

    async def _alert_node(self, state: AgentState) -> AgentState:
        """Check for alert conditions."""
        if not self.config.alert_on_new_signals:
            return state

        # Get new signals from this run
        monitor_result = state.metadata.get("monitor_result", {})
        new_signals = monitor_result.get("new_signals", [])

        # Filter by threshold
        threshold_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold_level = threshold_order.get(self.config.alert_threshold, 1)

        alerts = [
            s for s in new_signals
            if threshold_order.get(s.severity, 0) >= threshold_level
        ]

        if alerts:
            state.metadata["alerts"] = [
                {
                    "signal_id": str(s.id),
                    "title": s.title,
                    "severity": s.severity,
                    "entity_id": str(s.entity_id),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                for s in alerts
            ]
            # In production, send to notification system
            print(f"ALERT: {len(alerts)} new signals above threshold")

        return state

    async def _persist_node(self, state: AgentState) -> AgentState:
        """Persist signals to database."""
        if not self.config.persist_signals:
            return state

        # In production, write to database
        # For now, just log
        signal_count = len(state.signals)
        print(f"Persisted {signal_count} signals to storage")
        return state

    async def run_once(self, thread_id: str | None = None) -> AgentState:
        """Run a single monitoring cycle."""
        thread_id = thread_id or f"monitor_{uuid4().hex[:8]}"
        run_config = {"configurable": {"thread_id": thread_id}}

        initial_state = AgentState(
            brief=self.monitor_config.brief,
            entities=self.monitor_config.entities,
        )

        final_state = await self.graph.ainvoke(initial_state, run_config)
        return final_state if isinstance(final_state, AgentState) else AgentState(**final_state)

    async def start_continuous(self, thread_id: str | None = None) -> None:
        """Start continuous monitoring loop."""
        if self._running:
            return

        self._running = True
        thread_id = thread_id or f"monitor_{uuid4().hex[:8]}"

        async def monitoring_loop():
            while self._running:
                try:
                    await self.run_once(thread_id)
                except Exception as e:
                    print(f"Monitoring cycle failed: {e}")
                await asyncio.sleep(self.config.interval_seconds)

        self._task = asyncio.create_task(monitoring_loop())

    async def stop_continuous(self) -> None:
        """Stop continuous monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def get_signal_history(self, entity_id: str, signal_type: str) -> list[CompetitiveSignal]:
        """Get signal history from monitor agent."""
        return self.monitor_agent.get_signal_history(entity_id, signal_type)


def create_monitoring_workflow(
    monitor_config: MonitorConfig,
    config: MonitoringWorkflowConfig | None = None,
    **kwargs: Any,
) -> MonitoringWorkflow:
    """Factory function to create a MonitoringWorkflow."""
    return MonitoringWorkflow(monitor_config=monitor_config, config=config, **kwargs)