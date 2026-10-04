"""Competitive Intelligence Platform - Principal Engineer Level AI Agent System."""

from .config import Settings, get_settings
from .models import (
    AgentState,
    CompetitiveSignal,
    ConfidenceLevel,
    Entity,
    EntityType,
    ResearchBrief,
    ResearchReport,
    SearchEngine,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SignalType,
    SourceType,
)
from .agents import (
    AnalystAgent,
    MonitorAgent,
    ResearcherAgent,
    SynthesizerAgent,
    create_analyst_agent,
    create_monitor_agent,
    create_researcher_agent,
    create_synthesizer_agent,
)
from .workflows import (
    MonitoringWorkflow,
    MonitoringWorkflowConfig,
    ResearchWorkflow,
    ResearchWorkflowConfig,
    create_monitoring_workflow,
    create_research_workflow,
)
from .reports import (
    ReportGenerator,
    ExportFormat,
    create_report_generator,
)
from .tools import SearchToolset, create_search_toolset

__version__ = "0.1.0"

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Models
    "AgentState",
    "CompetitiveSignal",
    "ConfidenceLevel",
    "Entity",
    "EntityType",
    "ResearchBrief",
    "ResearchReport",
    "SearchEngine",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SignalType",
    "SourceType",
    # Agents
    "AnalystAgent",
    "MonitorAgent",
    "ResearcherAgent",
    "SynthesizerAgent",
    "create_analyst_agent",
    "create_monitor_agent",
    "create_researcher_agent",
    "create_synthesizer_agent",
    # Workflows
    "MonitoringWorkflow",
    "MonitoringWorkflowConfig",
    "ResearchWorkflow",
    "ResearchWorkflowConfig",
    "create_monitoring_workflow",
    "create_research_workflow",
    # Reports
    "ReportGenerator",
    "ExportFormat",
    "create_report_generator",
    # Tools
    "SearchToolset",
    "create_search_toolset",
]