"""Synthesizer Agent - Responsible for generating comprehensive research reports."""

from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from competitive_intel.agents.base import AgentConfig, BaseAgent, StructuredOutputAgent
from competitive_intel.models import (
    AgentState,
    Citation,
    CompetitiveSignal,
    ConfidenceLevel,
    Entity,
    ReportSection,
    ResearchBrief,
    ResearchReport,
    SignalType,
)
from competitive_intel.tools.search_tools import SearchToolset


class ReportStructure(BaseModel):
    """Planned report structure."""

    title: str
    executive_summary: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


SYNTHESIZER_SYSTEM_PROMPT = """You are an expert Competitive Intelligence Report Writer. Your role is to synthesize analyzed signals and research into clear, actionable intelligence reports.

You receive:
- Research brief (scope, entities, focus areas)
- Extracted entities with metadata
- Analyzed competitive signals with citations
- Raw search results for reference

Your output must be a comprehensive ResearchReport with:
1. Executive summary (2-3 paragraphs, bottom-line up front)
2. Structured sections organized by theme/entity/signal type
3. All claims backed by citations
4. Confidence scoring for each major finding
5. Actionable recommendations
6. Clear signal-to-noise separation

Report Structure Principles:
- Lead with the most impactful findings
- Group related signals into thematic sections
- Use evidence-based language ("Source X reports..." not "It appears...")
- Quantify wherever possible (funding amounts, headcount, dates)
- Distinguish confirmed facts from speculation
- Include competitive implications for each finding
- Provide specific, actionable recommendations

Citation Standards:
- Every factual claim must have a citation
- Use inline citations with source IDs
- Prefer primary sources (official announcements, SEC filings)
- Note when sources conflict
- Include source credibility assessment

Output Format:
Generate a ReportStructure that will be converted to a full ResearchReport."""


class SynthesizerAgent(StructuredOutputAgent):
    """Agent responsible for synthesizing research into comprehensive reports."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        llm: Any = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="synthesizer",
            description="Synthesizes research into comprehensive intelligence reports",
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
        )
        super().__init__(config, ReportStructure, llm, search_tools)

    async def execute(self, state: AgentState, config: RunnableConfig | None = None) -> AgentState:
        """Synthesize signals and research into a report."""
        state = self.set_step(state, "structuring")

        if not state.brief:
            return self.add_error(state, "No research brief provided")
        if not state.signals:
            return self.add_warning(state, "No signals to synthesize")

        # Plan report structure
        structure = await self._plan_report_structure(state)
        state = self.update_state(state, metadata={"report_structure": structure.model_dump()})

        # Generate full report
        state = self.set_step(state, "writing")
        report = await self._generate_report(state, structure)
        state = self.update_state(state, report=report)

        state = self.set_step(state, "completed")
        return state

    async def _plan_report_structure(self, state: AgentState) -> ReportStructure:
        """Plan the report structure based on signals and brief."""
        # Prepare signal summary
        signal_summary = self._summarize_signals(state.signals)
        entity_summary = self._summarize_entities(state.entities)

        prompt = f"""Plan a comprehensive competitive intelligence report structure.

Research Brief:
- Topic: {state.brief.topic}
- Depth: {state.brief.depth}
- Output Format: {state.brief.output_format}
- Focus Areas: {", ".join(state.brief.focus_areas) if state.brief.focus_areas else "General"}

Entities Tracked: {entity_summary}

Signals Detected ({len(state.signals)} total):
{signal_summary}

Design a report structure with:
1. Compelling title
2. Executive summary (key findings in 2-3 paragraphs)
3. 4-8 major sections organized by theme/entity/impact
4. Key findings list (5-10 bullet points)
5. Recommendations (3-5 actionable items)

Sections should have: title, level (1-2), description of content, relevant signal types, key entities."""

        result = await self.execute_structured(prompt)
        return result if isinstance(result, ReportStructure) else ReportStructure(
            title=f"Competitive Intelligence: {state.brief.topic}",
            executive_summary="Report generation failed.",
            sections=[],
        )

    def _summarize_signals(self, signals: list[CompetitiveSignal]) -> str:
        """Create a summary of signals for the prompt."""
        by_type: dict[SignalType, list[CompetitiveSignal]] = {}
        for s in signals:
            by_type.setdefault(s.signal_type, []).append(s)

        lines = []
        for sig_type, sigs in sorted(by_type.items(), key=lambda x: -len(x[1])):
            high_conf = [s for s in sigs if s.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)]
            lines.append(f"\n{sig_type.value} ({len(sigs)} total, {len(high_conf)} medium+ confidence):")
            for s in sigs[:5]:  # Top 5 per type
                lines.append(f"  - {s.title} [{s.confidence.value}] ({s.severity})")
        return "\n".join(lines)

    def _summarize_entities(self, entities: list[Entity]) -> str:
        """Create entity summary."""
        if not entities:
            return "None specified"
        return ", ".join([f"{e.name} ({e.type.value})" for e in entities])

    async def _generate_report(self, state: AgentState, structure: ReportStructure) -> ResearchReport:
        """Generate the full research report."""
        # Build sections from structure
        sections = []
        all_citations = []
        section_signals_map: dict[str, list[CompetitiveSignal]] = {}

        # Map signals to sections
        for section_plan in structure.sections:
            section_title = section_plan.get("title", "")
            relevant_signals = self._match_signals_to_section(section_title, state.signals)
            section_signals_map[section_title] = relevant_signals

        # Write each section
        for i, section_plan in enumerate(structure.sections):
            section_title = section_plan.get("title", f"Section {i+1}")
            signals_for_section = section_signals_map.get(section_title, [])

            content = await self._write_section(
                section_title,
                section_plan.get("description", ""),
                signals_for_section,
                state.brief,
            )

            # Collect citations from signals
            section_citations = []
            for signal in signals_for_section:
                section_citations.extend(signal.citations)
                all_citations.extend(signal.citations)

            sections.append(ReportSection(
                id=uuid4(),
                title=section_title,
                content=content,
                level=section_plan.get("level", 1),
                order=i,
                citations=section_citations,
                signals=signals_for_section,
            ))

        # Calculate overall confidence
        confidence_score = self._calculate_confidence(state.signals)

        return ResearchReport(
            id=uuid4(),
            brief_id=state.brief.id,
            title=structure.title,
            executive_summary=structure.executive_summary,
            sections=sections,
            signals=state.signals,
            entities=state.entities,
            citations=self._deduplicate_citations(all_citations),
            confidence_score=confidence_score,
            metadata={
                "structure": structure.model_dump(),
                "signal_count": len(state.signals),
                "entity_count": len(state.entities),
            },
        )

    def _match_signals_to_section(self, section_title: str, signals: list[CompetitiveSignal]) -> list[CompetitiveSignal]:
        """Match signals to report sections based on title/keywords."""
        title_lower = section_title.lower()
        keywords = title_lower.split()

        matched = []
        for signal in signals:
            signal_text = f"{signal.title} {signal.summary}".lower()
            if any(kw in signal_text for kw in keywords if len(kw) > 3):
                matched.append(signal)
            elif signal.signal_type.value.replace("_", " ") in title_lower:
                matched.append(signal)

        return matched if matched else signals[:3]  # Fallback: assign some signals

    async def _write_section(
        self,
        title: str,
        description: str,
        signals: list[CompetitiveSignal],
        brief: ResearchBrief,
    ) -> str:
        """Write a single report section."""
        signal_details = "\n".join([
            f"- {s.title}: {s.summary} (Confidence: {s.confidence.value}, Severity: {s.severity})"
            for s in signals
        ])

        prompt = f"""Write a detailed report section.

Section: {title}
Description: {description}
Available Signals:
{signal_details if signals else "No specific signals assigned - synthesize from context"}

Requirements:
- Professional intelligence report tone
- Evidence-based claims with inline citations [source_id]
- Quantify metrics where possible
- Include competitive implications
- Distinguish confirmed vs. speculative
- Length: 2-5 paragraphs
- Use clear headings if subsections needed"""

        messages = self._build_messages(prompt)
        response = await self.llm.ainvoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

    def _calculate_confidence(self, signals: list[CompetitiveSignal]) -> float:
        """Calculate overall report confidence score."""
        if not signals:
            return 0.0

        weights = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.UNVERIFIED: 0.1,
        }

        total_weight = sum(weights.get(s.confidence, 0) for s in signals)
        max_possible = len(signals) * 1.0
        return min(total_weight / max_possible, 1.0) if max_possible > 0 else 0.0

    def _deduplicate_citations(self, citations: list[Citation]) -> list[Citation]:
        """Deduplicate citations by URL."""
        seen = set()
        unique = []
        for c in citations:
            if c.url not in seen:
                seen.add(c.url)
                unique.append(c)
        return unique


def create_synthesizer_agent(
    llm: Any = None,
    search_tools: SearchToolset | None = None,
) -> SynthesizerAgent:
    """Factory function to create a SynthesizerAgent."""
    return SynthesizerAgent(llm=llm, search_tools=search_tools)