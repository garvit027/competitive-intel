#!/usr/bin/env python
"""Advanced custom agents example - demonstrates extending the platform."""

import asyncio
from typing import Any
from pydantic import BaseModel, Field

from competitive_intel import (
    create_research_workflow,
    create_report_generator,
    ExportFormat,
)
from competitive_intel.agents import BaseAgent, AgentConfig, StructuredOutputAgent
from competitive_intel.models import (
    AgentState,
    Entity,
    EntityType,
    ResearchBrief,
    SignalType,
    ConfidenceLevel,
    CompetitiveSignal,
)
from competitive_intel.tools.search_tools import SearchToolset


# Custom signal type for financial analysis
class FinancialMetricSignal(BaseModel):
    """Structured financial signal."""
    company: str
    metric: str  # revenue, arr, valuation, etc.
    value: float
    currency: str = "USD"
    period: str  # Q1 2024, FY 2023, etc.
    source_url: str
    confidence: ConfidenceLevel


class FinancialSignalsBatch(BaseModel):
    """Batch of financial signals."""
    signals: list[FinancialMetricSignal] = Field(default_factory=list)


# Custom agent for financial intelligence
class FinancialAnalystAgent(StructuredOutputAgent):
    """Specialized agent for extracting financial metrics."""

    SYSTEM_PROMPT = """You are a Financial Intelligence Analyst specializing in extracting precise financial metrics from search results.

Focus on:
- Revenue, ARR, valuation figures
- Funding round amounts and valuations
- Growth rates (YoY, QoQ)
- Customer counts, retention rates
- Unit economics (CAC, LTV, margins)
- Guidance and projections

Rules:
- Only extract explicitly stated numbers with sources
- Distinguish between reported, estimated, and rumored figures
- Note the time period for each metric
- Include currency and scale (millions, billions)
- Confidence: high for official filings/earnings, medium for reputable reporting, low for estimates"""

    def __init__(self, llm: Any = None, search_tools: SearchToolset = None):
        config = AgentConfig(
            name="financial_analyst",
            description="Extracts structured financial metrics from search results",
            system_prompt=self.SYSTEM_PROMPT,
        )
        super().__init__(config, FinancialSignalsBatch, llm, search_tools)


# Custom workflow combining standard research + financial analysis
class EnhancedResearchWorkflow:
    """Extended workflow with financial analysis phase."""

    def __init__(self):
        self.research_workflow = create_research_workflow()
        self.financial_analyst = FinancialAnalystAgent()
        self.report_generator = create_report_generator()

    async def run(self, brief: ResearchBrief) -> Any:
        """Run enhanced research with financial analysis."""

        # Phase 1: Standard research
        print("Phase 1: Standard competitive research...")
        report = await self.research_workflow.run(brief)

        # Phase 2: Financial analysis on collected results
        print("Phase 2: Financial metrics extraction...")
        financial_state = AgentState(
            brief=brief,
            search_results=report.metadata.get("search_results", []) if report.metadata else [],
        )

        # We need to get search results from the workflow - in practice
        # you'd modify the workflow to expose them. For demo, we'll re-search.
        from competitive_intel.tools.serpapi_tools import get_serpapi_tools
        from competitive_intel.models import SearchQuery, SearchEngine

        tools = await get_serpapi_tools()

        financial_queries = []
        for entity in brief.entities:
            financial_queries.extend([
                SearchQuery(query=f"{entity.name} revenue ARR valuation", engines=[SearchEngine.GOOGLE_NEWS, SearchEngine.GOOGLE_LIGHT], date_range="past_month"),
                SearchQuery(query=f"{entity.name} funding round valuation", engines=[SearchEngine.GOOGLE_NEWS], date_range="past_month"),
            ])

        financial_results = await tools.search_multiple(financial_queries, "web")
        financial_results.extend(await tools.search_multiple(financial_queries, "news"))

        financial_state.search_results = financial_results
        financial_state = await self.financial_analyst.execute(financial_state)

        # Combine results
        report.metadata["financial_signals"] = [
            s.model_dump() for s in financial_state.metadata.get("financial_signals", [])
        ]

        return report


async def main():
    """Run advanced financial intelligence research."""
    brief = ResearchBrief(
        topic="AI Company Financial Intelligence - Funding & Revenue Analysis",
        entities=[
            Entity(name="OpenAI", type=EntityType.COMPANY),
            Entity(name="Anthropic", type=EntityType.COMPANY),
            Entity(name="Mistral AI", type=EntityType.COMPANY),
            Entity(name="Cohere", type=EntityType.COMPANY),
            Entity(name="Databricks", type=EntityType.COMPANY),
        ],
        signal_types=[SignalType.FUNDING, SignalType.EARNINGS_REPORT],
        time_range="past_month",
        depth="deep",
        focus_areas=["valuation", "revenue", "ARR", "funding rounds", "investors"],
    )

    workflow = EnhancedResearchWorkflow()
    report = await workflow.run(brief)

    generator = create_report_generator()

    # Export with financial data
    md_path = await generator.export_report(report, brief, ExportFormat.MARKDOWN)
    print(f"\nEnhanced report saved to: {md_path}")

    # Show financial signals
    financial_signals = report.metadata.get("financial_signals", [])
    if financial_signals:
        print(f"\n--- Financial Signals Extracted: {len(financial_signals)} ---")
        for signal in financial_signals[:10]:
            print(f"  {signal['company']}: {signal['metric']} = {signal['value']:,.0f} {signal['currency']} ({signal['period']})")


if __name__ == "__main__":
    asyncio.run(main())