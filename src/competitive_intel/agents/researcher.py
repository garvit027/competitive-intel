"""Researcher Agent - Responsible for gathering information from multiple sources."""

from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from competitive_intel.agents.base import AgentConfig, BaseAgent
from competitive_intel.models import (
    AgentState,
    Entity,
    ResearchBrief,
    SearchEngine,
    SearchQuery,
    SignalType,
)
from competitive_intel.tools.search_tools import SearchToolset


class ResearchPlan(BaseModel):
    """Plan for research execution."""

    queries: list[SearchQuery] = Field(default_factory=list)
    entities_to_research: list[str] = Field(default_factory=list)
    signal_types_to_track: list[SignalType] = Field(default_factory=list)
    reasoning: str = ""
    estimated_searches: int = 0


RESEARCHER_SYSTEM_PROMPT = """You are an expert Competitive Intelligence Researcher. Your role is to design and execute comprehensive research plans to gather intelligence on companies, products, markets, and technologies.

You have access to multiple search tools:
- Web search: General research, background information, official sources
- News search: Recent announcements, press coverage, earnings reports
- Shopping search: Product listings, pricing, availability, reviews
- Maps search: Physical locations, offices, retail presence
- Videos search: Product demos, conference presentations, interviews

Your research process:
1. Analyze the research brief to understand the scope and objectives
2. Identify key entities (companies, products, people) to investigate
3. Determine which signal types are most relevant
4. Create a comprehensive search plan with diverse queries
5. Execute searches across multiple engines and sources
6. Collect and organize raw results for analysis

Principles:
- Cast a wide net initially, then narrow based on findings
- Prioritize primary sources (official sites, SEC filings, press releases)
- Cross-reference information across multiple sources
- Track provenance of all findings for citation
- Look for both explicit signals and implicit indicators
- Consider geographic and language diversity

Output a ResearchPlan with specific, actionable search queries."""


class ResearcherAgent(BaseAgent):
    """Agent responsible for designing and executing research plans."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        llm: Any = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="researcher",
            description="Designs and executes comprehensive research plans",
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
        )
        super().__init__(config, llm, search_tools)

    async def execute(self, state: AgentState, config: RunnableConfig | None = None) -> AgentState:
        """Execute research phase: plan searches and gather data."""
        state = self.set_step(state, "planning")

        if not state.brief:
            return self.add_error(state, "No research brief provided")

        # Create research plan
        plan = await self._create_research_plan(state.brief)
        state = self.update_state(state, metadata={"research_plan": plan.model_dump()})

        # Execute searches
        state = self.set_step(state, "searching")
        search_results = await self._execute_searches(plan.queries)
        state = self.update_state(state, search_results=search_results)

        # Extract entities from results
        state = self.set_step(state, "extracting_entities")
        entities = await self._extract_entities(search_results, state.brief.entities)
        state = self.update_state(state, entities=entities)

        state = self.set_step(state, "completed")
        return state

    async def _create_research_plan(self, brief: ResearchBrief) -> ResearchPlan:
        """Create a comprehensive research plan from the brief."""
        prompt = self._build_planning_prompt(brief)
        messages = self._build_messages(prompt)

        # Use structured output for the plan
        structured_llm = self.llm.with_structured_output(ResearchPlan)
        plan = await structured_llm.ainvoke(messages)

        # Enhance with brief-specific queries
        plan.queries.extend(self._generate_entity_queries(brief))
        plan.queries.extend(self._generate_signal_queries(brief))
        plan.entities_to_research = [e.name for e in brief.entities]
        plan.signal_types_to_track = brief.signal_types
        plan.estimated_searches = len(plan.queries)

        return plan

    def _build_planning_prompt(self, brief: ResearchBrief) -> str:
        """Build the planning prompt."""
        entity_names = [e.name for e in brief.entities]
        signal_types = [s.value for s in brief.signal_types]

        return f"""Research Brief:
- Topic: {brief.topic}
- Entities: {", ".join(entity_names) if entity_names else "None specified"}
- Signal Types: {", ".join(signal_types) if signal_types else "All types"}
- Time Range: {brief.time_range}
- Depth: {brief.depth}
- Focus Areas: {", ".join(brief.focus_areas) if brief.focus_areas else "General"}
- Exclude Terms: {", ".join(brief.exclude_terms) if brief.exclude_terms else "None"}

Create a comprehensive research plan with search queries that will uncover competitive intelligence signals. 
Consider:
1. Direct queries for each entity + signal type combination
2. Comparative queries (entity vs competitor)
3. Market/industry trend queries
4. Technology/innovation queries
5. Financial/regulatory queries
6. Geographic expansion queries

Generate 15-25 diverse search queries using different engines and parameters."""

    def _generate_entity_queries(self, brief: ResearchBrief) -> list[SearchQuery]:
        """Generate queries for each entity."""
        queries = []
        for entity in brief.entities:
            base_queries = [
                f"{entity.name} latest news announcements",
                f"{entity.name} product launch",
                f"{entity.name} funding investment",
                f"{entity.name} acquisition merger",
                f"{entity.name} partnership collaboration",
                f"{entity.name} leadership change CEO CTO",
                f"{entity.name} pricing strategy",
                f"{entity.name} market expansion",
                f"{entity.name} earnings financial results",
                f"{entity.name} technology innovation patent",
            ]
            for q in base_queries:
                queries.append(SearchQuery(
                    query=q,
                    engines=[SearchEngine.GOOGLE_LIGHT, SearchEngine.GOOGLE_NEWS],
                    date_range=brief.time_range,
                ))
        return queries

    def _generate_signal_queries(self, brief: ResearchBrief) -> list[SearchQuery]:
        """Generate queries for signal types."""
        queries = []
        signal_templates = {
            SignalType.PRODUCT_LAUNCH: ["new product launch", "product announcement", "beta release", "general availability"],
            SignalType.FUNDING: ["series A funding", "series B funding", "venture capital", "strategic investment", "IPO"],
            SignalType.ACQUISITION: ["acquires", "acquisition of", "merger with", "buys startup"],
            SignalType.PARTNERSHIP: ["partnership with", "strategic alliance", "integration with", "collaboration"],
            SignalType.LEADERSHIP_CHANGE: ["appoints new CEO", "hires CTO", "executive departure", "board appointment"],
            SignalType.PRICING_CHANGE: ["price increase", "new pricing", "pricing model", "subscription pricing"],
            SignalType.MARKET_EXPANSION: ["expands to", "enters market", "launches in", "international expansion"],
            SignalType.REGULATORY_ACTION: ["SEC filing", "regulatory approval", "compliance", "investigation"],
            SignalType.PATENT_FILING: ["patent filed", "patent granted", "intellectual property"],
            SignalType.HIRING_SURGE: ["hiring spree", "job openings", "talent acquisition", "team growth"],
            SignalType.LAYOFFS: ["layoffs", "restructuring", "workforce reduction", "headcount reduction"],
            SignalType.CUSTOMER_WIN: ["new customer", "wins contract", "case study", "deployment at"],
            SignalType.EARNINGS_REPORT: ["quarterly earnings", "financial results", "revenue growth", "ARR"],
        }

        for signal_type in brief.signal_types or list(SignalType):
            templates = signal_templates.get(signal_type, [signal_type.value.replace("_", " ")])
            for entity in brief.entities:
                for template in templates:
                    queries.append(SearchQuery(
                        query=f"{entity.name} {template}",
                        engines=[SearchEngine.GOOGLE_NEWS, SearchEngine.GOOGLE_LIGHT],
                        date_range=brief.time_range,
                    ))
        return queries

    async def _execute_searches(self, queries: list[SearchQuery]) -> list[Any]:
        """Execute all search queries in parallel batches."""
        from competitive_intel.tools.serpapi_tools import get_serpapi_tools

        tools = await get_serpapi_tools()
        results = []

        # Group by tool for efficiency
        web_queries = [q for q in queries if SearchEngine.GOOGLE_LIGHT in q.engines or SearchEngine.BING in q.engines]
        news_queries = [q for q in queries if SearchEngine.GOOGLE_NEWS in q.engines]
        shopping_queries = [q for q in queries if SearchEngine.GOOGLE_SHOPPING in q.engines or SearchEngine.AMAZON in q.engines]

        if web_queries:
            results.extend(await tools.search_multiple(web_queries, "web"))
        if news_queries:
            results.extend(await tools.search_multiple(news_queries, "news"))
        if shopping_queries:
            results.extend(await tools.search_multiple(shopping_queries, "shopping"))

        return results

    async def _extract_entities(self, search_results: list[Any], known_entities: list[Entity]) -> list[Entity]:
        """Extract and deduplicate entities from search results."""
        # For now, return known entities - in production, use NER
        return known_entities


def create_researcher_agent(
    llm: Any = None,
    search_tools: SearchToolset | None = None,
) -> ResearcherAgent:
    """Factory function to create a ResearcherAgent."""
    return ResearcherAgent(llm=llm, search_tools=search_tools)