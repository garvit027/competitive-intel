"""Monitor Agent - Responsible for continuous competitive monitoring."""

from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from competitive_intel.agents.base import AgentConfig, BaseAgent
from competitive_intel.models import (
    AgentState,
    CompetitiveSignal,
    Entity,
    ResearchBrief,
    SignalType,
)
from competitive_intel.tools.search_tools import SearchToolset


class MonitorConfig(BaseModel):
    """Configuration for monitoring."""

    brief: ResearchBrief
    interval_minutes: int = 60
    signal_types: list[SignalType] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    notification_threshold: str = "medium"  # low, medium, high, critical
    max_signals_per_run: int = 50


class MonitorResult(BaseModel):
    """Result of a monitoring run."""

    new_signals: list[CompetitiveSignal] = Field(default_factory=list)
    updated_signals: list[CompetitiveSignal] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    run_duration_seconds: float = 0.0


MONITOR_SYSTEM_PROMPT = """You are a Competitive Intelligence Monitor. Your role is to continuously track entities and detect new signals.

You operate on a schedule, comparing current state against previous runs to identify:
- New signals (first appearance)
- Signal updates (changes in existing stories)
- Signal resolution (closed/confirmed/denied)

Key Principles:
- Minimize false positives through corroboration
- Track signal evolution over time
- Prioritize by business impact
- Maintain signal history for trend analysis
- Alert on threshold crossings"""


class MonitorAgent(BaseAgent):
    """Agent for continuous competitive monitoring."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        llm: Any = None,
        search_tools: SearchToolset | None = None,
        monitor_config: MonitorConfig | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="monitor",
            description="Continuously monitors entities for new competitive signals",
            system_prompt=MONITOR_SYSTEM_PROMPT,
        )
        super().__init__(config, llm, search_tools)
        self.monitor_config = monitor_config
        self._previous_signals: dict[str, CompetitiveSignal] = {}

    async def execute(self, state: AgentState, config: RunnableConfig | None = None) -> AgentState:
        """Execute a monitoring cycle."""
        if not self.monitor_config:
            return self.add_error(state, "No monitor configuration provided")

        state = self.set_step(state, "monitoring")

        # Generate monitoring queries
        queries = self._generate_monitoring_queries(self.monitor_config)

        # Execute searches
        from competitive_intel.tools.serpapi_tools import get_serpapi_tools
        tools = await get_serpapi_tools()
        results = await tools.search_multiple(queries, "web")
        results.extend(await tools.search_multiple(queries, "news"))

        # Analyze for new signals
        state = self.set_step(state, "analyzing")
        new_signals = await self._detect_new_signals(results, state)

        # Compare with previous run
        state = self.set_step(state, "comparing")
        new_signals, updated = self._compare_with_previous(new_signals)

        # Update state
        state.signals.extend(new_signals)
        state.signals.extend(updated)

        # Store for next run
        for signal in new_signals + updated:
            self._previous_signals[f"{signal.entity_id}:{signal.signal_type}:{signal.title[:50]}"] = signal

        state = self.update_state(state, metadata={
            "monitor_result": MonitorResult(
                new_signals=new_signals,
                updated_signals=updated,
            ).model_dump()
        })

        state = self.set_step(state, "completed")
        return state

    def _generate_monitoring_queries(self, config: MonitorConfig) -> list:
        """Generate queries for monitoring run."""
        from competitive_intel.models import SearchEngine, SearchQuery

        queries = []
        for entity in config.entities:
            # High-priority signal types for monitoring
            priority_signals = config.signal_types or [
                SignalType.PRODUCT_LAUNCH,
                SignalType.FUNDING,
                SignalType.ACQUISITION,
                SignalType.PARTNERSHIP,
                SignalType.LEADERSHIP_CHANGE,
                SignalType.PRICING_CHANGE,
                SignalType.CUSTOMER_WIN,
                SignalType.EARNINGS_REPORT,
            ]

            for signal_type in priority_signals:
                query_text = f"{entity.name} {signal_type.value.replace('_', ' ')}"
                queries.append(SearchQuery(
                    query=query_text,
                    engines=[SearchEngine.GOOGLE_NEWS, SearchEngine.GOOGLE_LIGHT],
                    date_range="past_day",  # Only recent for monitoring
                    num_results=5,
                ))

        return queries[:config.max_signals_per_run]

    async def _detect_new_signals(
        self,
        results: list[Any],
        state: AgentState,
    ) -> list[CompetitiveSignal]:
        """Detect signals from monitoring results."""
        # Reuse analyst logic for detection
        from competitive_intel.agents.analyst import AnalystAgent

        analyst = AnalystAgent(llm=self.llm, search_tools=self.search_tools)
        temp_state = AgentState(search_results=results, entities=state.entities)
        temp_state = await analyst.execute(temp_state)
        return temp_state.signals

    def _compare_with_previous(
        self,
        current_signals: list[CompetitiveSignal],
    ) -> tuple[list[CompetitiveSignal], list[CompetitiveSignal]]:
        """Compare current signals with previous run."""
        new_signals = []
        updated_signals = []

        for signal in current_signals:
            key = f"{signal.entity_id}:{signal.signal_type}:{signal.title[:50]}"
            if key in self._previous_signals:
                # Check if signal has been updated
                prev = self._previous_signals[key]
                if self._signal_changed(prev, signal):
                    signal.metadata["previous_confidence"] = prev.confidence.value
                    signal.metadata["previous_severity"] = prev.severity
                    updated_signals.append(signal)
            else:
                new_signals.append(signal)

        return new_signals, updated_signals

    def _signal_changed(self, previous: CompetitiveSignal, current: CompetitiveSignal) -> bool:
        """Check if a signal has materially changed."""
        return (
            previous.confidence != current.confidence
            or previous.severity != current.severity
            or len(current.source_urls) > len(previous.source_urls)
        )

    def get_signal_history(self, entity_id: str, signal_type: SignalType) -> list[CompetitiveSignal]:
        """Get history of signals for an entity/type."""
        return [
            s for k, s in self._previous_signals.items()
            if k.startswith(f"{entity_id}:{signal_type.value}:")
        ]


def create_monitor_agent(
    monitor_config: MonitorConfig,
    llm: Any = None,
    search_tools: SearchToolset | None = None,
) -> MonitorAgent:
    """Factory function to create a MonitorAgent."""
    return MonitorAgent(monitor_config=monitor_config, llm=llm, search_tools=search_tools)