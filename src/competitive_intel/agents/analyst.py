"""Analyst Agent - Responsible for detecting and analyzing competitive signals."""

from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from competitive_intel.agents.base import AgentConfig, BaseAgent, StructuredOutputAgent
from competitive_intel.models import (
    AgentState,
    CompetitiveSignal,
    ConfidenceLevel,
    Entity,
    SearchResponse,
    SignalType,
)
from competitive_intel.tools.search_tools import SearchToolset


class SignalAnalysis(BaseModel):
    """Analysis of a potential competitive signal."""

    signal_type: SignalType
    title: str
    summary: str
    description: str | None = None
    entity_name: str
    confidence: ConfidenceLevel
    severity: str
    supporting_evidence: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SignalBatch(BaseModel):
    """Batch of detected signals."""

    signals: list[SignalAnalysis] = Field(default_factory=list)
    reasoning: str = ""


ANALYST_SYSTEM_PROMPT = """You are an expert Competitive Intelligence Analyst. Your role is to analyze search results and detect meaningful competitive signals.

You receive raw search results from multiple sources (web, news, shopping, maps, videos). Your job is to:

1. Identify competitive signals from the noise
2. Classify each signal by type (product launch, funding, acquisition, etc.)
3. Assess confidence based on source quality and corroboration
4. Determine severity/impact level
5. Extract supporting evidence and citations
6. Tag signals for downstream processing

Signal Types:
- product_launch: New products, features, beta releases, GA announcements
- funding: VC rounds, strategic investments, IPOs, debt financing
- acquisition: M&A, acqui-hires, asset purchases
- partnership: Strategic alliances, integrations, channel partnerships
- leadership_change: C-suite changes, board appointments, key hires/departures
- pricing_change: Price increases/decreases, new tiers, model changes
- market_expansion: Geographic expansion, new verticals, customer segments
- regulatory_action: SEC filings, investigations, approvals, compliance
- patent_filing: Patent applications, grants, IP litigation
- hiring_surge: Mass hiring, key role openings, team expansions
- layoffs: Workforce reductions, restructuring, office closures
- technology_adoption: New tech stack, AI/ML adoption, platform migrations
- customer_win: Major customer announcements, case studies, logos
- security_incident: Breaches, vulnerabilities, compliance issues
- earnings_report: Quarterly results, guidance, KPIs
- strategic_announcement: Strategy shifts, pivots, major initiatives

Confidence Levels:
- high: Multiple reputable sources, official announcements, primary sources
- medium: Single reputable source, credible secondary sources
- low: Unverified sources, rumors, speculative reporting
- unverified: Social media, forums, anonymous sources

Severity:
- critical: Existential threat/opportunity, major market impact
- high: Significant competitive impact, material business change
- medium: Notable but not transformative
- low: Minor updates, incremental changes
- informational: Background context, no immediate action needed

Be conservative with high confidence ratings. Require corroboration for critical signals."""


class AnalystAgent(StructuredOutputAgent):
    """Agent responsible for detecting and analyzing competitive signals from search results."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        llm: Any = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="analyst",
            description="Detects and analyzes competitive signals from search results",
            system_prompt=ANALYST_SYSTEM_PROMPT,
        )
        # Initialize with SignalBatch as output model
        super().__init__(config, SignalBatch, llm, search_tools)

    async def execute(self, state: AgentState, config: RunnableConfig | None = None) -> AgentState:
        """Analyze search results and extract competitive signals."""
        state = self.set_step(state, "analyzing")

        if not state.search_results:
            return self.add_warning(state, "No search results to analyze")

        # Analyze each search result batch
        all_signals = []
        for response in state.search_results:
            if response.results:
                signals = await self._analyze_results(response)
                all_signals.extend(signals)

        # Deduplicate and enrich signals
        state = self.set_step(state, "deduplicating")
        unique_signals = self._deduplicate_signals(all_signals)

        # Convert to CompetitiveSignal objects
        competitive_signals = []
        for signal in unique_signals:
            comp_signal = self._convert_to_competitive_signal(signal, state.entities)
            competitive_signals.append(comp_signal)

        state = self.update_state(state, signals=competitive_signals)
        state = self.set_step(state, "completed")
        return state

    async def _analyze_results(self, response: SearchResponse) -> list[SignalAnalysis]:
        """Analyze a single search response for signals."""
        # Build context from results
        context = self._build_analysis_context(response)

        prompt = f"""Analyze these search results for competitive intelligence signals:

Search Query: {response.query.query}
Engine: {response.query.engines}
Results: {len(response.results)} items

{context}

Identify ALL competitive signals present. For each signal, provide:
1. Signal type classification
2. Clear title and summary
3. Entity involved (company/product/person)
4. Confidence level (high/medium/low/unverified)
5. Severity (critical/high/medium/low/informational)
6. Supporting evidence (quotes, data points)
7. Source URLs
8. Relevant tags

Be thorough but precise. Only report signals with at least some supporting evidence."""

        try:
            result = await self.execute_structured(prompt)
            return result.signals if isinstance(result, SignalBatch) else []
        except Exception as e:
            # Fallback to manual parsing if structured output fails
            return await self._fallback_analysis(response)

    def _build_analysis_context(self, response: SearchResponse) -> str:
        """Build context string from search results."""
        lines = []
        for i, result in enumerate(response.results[:15], 1):  # Limit context size
            lines.append(f"\n--- Result {i} ---")
            lines.append(f"Title: {result.title}")
            lines.append(f"URL: {result.url}")
            lines.append(f"Snippet: {result.snippet[:500]}")
            if result.metadata:
                lines.append(f"Metadata: {result.metadata}")
        return "\n".join(lines)

    async def _fallback_analysis(self, response: SearchResponse) -> list[SignalAnalysis]:
        """Fallback analysis using simpler prompting."""
        # Simplified keyword-based detection for fallback
        signals = []
        signal_keywords = {
            SignalType.PRODUCT_LAUNCH: ["launch", "release", "announce", "unveil", "debut", "introduce"],
            SignalType.FUNDING: ["funding", "investment", "raise", "series", "venture", "capital"],
            SignalType.ACQUISITION: ["acquire", "acquisition", "buy", "purchase", "merger"],
            SignalType.PARTNERSHIP: ["partner", "partnership", "alliance", "collaboration", "integration"],
            SignalType.LEADERSHIP_CHANGE: ["appoint", "hire", "depart", "resign", "promote", "ceo", "cto"],
            SignalType.PRICING_CHANGE: ["price", "pricing", "cost", "subscription", "tier"],
            SignalType.MARKET_EXPANSION: ["expand", "enter", "launch in", "available in", "international"],
            SignalType.REGULATORY_ACTION: ["sec", "filing", "regulatory", "compliance", "investigation"],
            SignalType.HIRING_SURGE: ["hiring", "jobs", "openings", "recruit", "talent"],
            SignalType.LAYOFFS: ["layoff", "restructuring", "cut", "reduce", "downsize"],
            SignalType.CUSTOMER_WIN: ["customer", "client", "deal", "contract", "wins", "chooses"],
            SignalType.EARNINGS_REPORT: ["earnings", "revenue", "quarterly", "financial results", "arr"],
        }

        for result in response.results:
            text = f"{result.title} {result.snippet}".lower()
            for signal_type, keywords in signal_keywords.items():
                if any(kw in text for kw in keywords):
                    signals.append(SignalAnalysis(
                        signal_type=signal_type,
                        title=result.title[:200],
                        summary=result.snippet[:300],
                        entity_name=self._extract_entity_name(result),
                        confidence=ConfidenceLevel.LOW,
                        severity="low",
                        supporting_evidence=[result.snippet[:200]],
                        source_urls=[result.url],
                        tags=["auto-detected"],
                    ))
        return signals

    def _extract_entity_name(self, result: SearchResponse) -> str:
        """Extract likely entity name from result."""
        # Simple heuristic - first capitalized words in title
        words = result.title.split()
        entities = [w for w in words[:5] if w[0].isupper() and len(w) > 2]
        return " ".join(entities[:3]) if entities else "Unknown"

    def _deduplicate_signals(self, signals: list[SignalAnalysis]) -> list[SignalAnalysis]:
        """Deduplicate signals by entity + type + similar title."""
        seen = set()
        unique = []
        for signal in signals:
            key = (signal.entity_name.lower(), signal.signal_type.value, signal.title[:50].lower())
            if key not in seen:
                seen.add(key)
                unique.append(signal)
        return unique

    def _convert_to_competitive_signal(self, signal: SignalAnalysis, entities: list[Entity]) -> CompetitiveSignal:
        """Convert SignalAnalysis to CompetitiveSignal with entity linking."""
        # Find matching entity
        entity_id = None
        for entity in entities:
            if entity.name.lower() in signal.entity_name.lower() or signal.entity_name.lower() in entity.name.lower():
                entity_id = entity.id
                break

        # Create citations from source URLs
        citations = []
        for url in signal.source_urls:
            citations.append(
                CompetitiveSignal.model_fields["citations"].annotation[0](
                    source_id=uuid4(),
                    claim=signal.summary,
                    url=url,
                    title=signal.title,
                    source_type="web",
                    confidence=signal.confidence,
                )
            )

        return CompetitiveSignal(
            entity_id=entity_id or uuid4(),
            signal_type=signal.signal_type,
            title=signal.title,
            summary=signal.summary,
            description=signal.description,
            source_urls=signal.source_urls,
            citations=citations,
            confidence=signal.confidence,
            severity=signal.severity,
            tags=signal.tags,
        )


def create_analyst_agent(
    llm: Any = None,
    search_tools: SearchToolset | None = None,
) -> AnalystAgent:
    """Factory function to create an AnalystAgent."""
    return AnalystAgent(llm=llm, search_tools=search_tools)