# Competitive Intelligence Platform

> **AI agents that plan, search, analyze, and report on your competitive landscape using live search data.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![SerpApi](https://img.shields.io/badge/powered%20by-SerpApi-orange)](https://serpapi.com)

---

## What it does

Give it a topic and a list of companies. It returns a cited, executive-ready report on what they're doing — product launches, funding, M&A, partnerships, leadership changes, pricing shifts, layoffs, earnings, regulatory actions, patents, hiring surges, customer wins — with confidence scores and severity ratings.

A companion **Monitor Agent** runs continuous tracking with alerting so you never miss a move.

---

## Quick Start

```bash
# 1. Clone & install
git clone https://github.com/garvit027/competitive-intel.git
cd competitive-intel
./scripts/setup.sh

# 2. Add API keys to .env (created by setup.sh)
# SERPAPI_API_KEY — free 250 searches/month at https://serpapi.com/manage-api-key
# OPENAI_API_KEY  — or compatible provider

# 3. Run a research task
uv run competitive-intel research "AI Foundation Models" \
  --entity "OpenAI,Anthropic,Google DeepMind,Meta AI" \
  --entity-type "company,company,company,company" \
  --signal "product_launch,funding,partnership,pricing_change" \
  --depth standard --format markdown

# 4. Or start continuous monitoring
uv run competitive-intel monitor "AI Infrastructure" \
  --entity "NVIDIA,AMD,Intel,CoreWeave,Lambda Labs" \
  --interval 60 --threshold medium
```

---

## Example Output

```
--- Research Summary ---
Title: Competitive Intelligence: AI Foundation Models
Confidence Score: 0.87
Signals Detected: 23
Entities: 4
Citations: 47
Sections: 6

--- Top Signals ---
[CRITICAL] Anthropic raises $4B from Amazon at $18.4B valuation
    Type: funding | Confidence: high
[HIGH] OpenAI launches GPT-4o with real-time voice
    Type: product_launch | Confidence: high
[MEDIUM] Google DeepMind merges with Google Brain
    Type: acquisition | Confidence: medium
```

Reports include: executive summary, detailed sections by theme, signal tables, entity profiles, and full citation bibliography.

---

## Features

| Capability | Details |
|------------|---------|
| **9 Search Engines** | Web, News, Shopping, Maps, Images, Videos, Flights, Hotels, Travel Explore |
| **15 Signal Types** | product_launch, funding, acquisition, partnership, leadership_change, pricing_change, market_expansion, regulatory_action, patent_filing, hiring_surge, layoffs, technology_adoption, customer_win, security_incident, earnings_report |
| **Output Formats** | Markdown, HTML, PDF (WeasyPrint), JSON |
| **Observability** | Structured logging, Prometheus metrics, OpenTelemetry tracing |
| **Caching** | Disk-based with TTL (60–80% hit rate on recurring monitoring) |
| **Rate Limiting** | Token bucket, respects SerpApi limits |
| **Human-in-the-Loop** | Optional review checkpoints in workflow |

---

## Architecture

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Researcher    │──▶│    Analyst      │──▶│  Synthesizer    │
│   (plans)       │   │   (detects)     │   │   (reports)     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
│  (stateful, checkpointed, streamable, human-review ready)  │
└─────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Web Search    │   │  News Search    │   │ Shopping/Maps/  │
│  (Google, Bing, │   │  (Google News)  │   │  Videos/Flights │
│   DuckDuckGo)   │   │                 │   │  /Hotels/etc.   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `competitive-intel research <topic>` | Run a one-off research task |
| `competitive-intel monitor <topic>` | Start continuous monitoring |
| `competitive-intel brief <topic> -o file.json` | Generate a brief template |
| `competitive-intel validate <file.json>` | Validate a brief file |
| `competitive-intel demo` | Run a quick demo with sample data |
| `competitive-intel version` | Show version |

### Research Options
```bash
--entity, -e         Comma-separated entity names
--entity-type, -t    Comma-separated types (company, product, person, technology, market)
--signal, -s         Comma-separated signal types (default: all)
--time-range         past_day, past_week, past_month, past_year
--depth              quick, standard, deep
--format             markdown, html, pdf, json
--output, -o         Output file path
--human-review       Enable human review checkpoint
```

---

## Programmatic Usage

```python
import asyncio
from competitive_intel import (
    create_research_workflow,
    create_report_generator,
    ExportFormat,
)
from competitive_intel.models import Entity, EntityType, ResearchBrief, SignalType

async def main():
    brief = ResearchBrief(
        topic="Cloud AI Platforms Competitive Analysis",
        entities=[
            Entity(name="AWS", type=EntityType.COMPANY),
            Entity(name="Google Cloud", type=EntityType.COMPANY),
            Entity(name="Azure", type=EntityType.COMPANY),
        ],
        signal_types=[
            SignalType.PRODUCT_LAUNCH,
            SignalType.PARTNERSHIP,
            SignalType.PRICING_CHANGE,
        ],
        time_range="past_month",
        depth="standard",
    )

    workflow = create_research_workflow()
    report = await workflow.run(brief)

    generator = create_report_generator()
    await generator.export_report(report, brief, ExportFormat.MARKDOWN)

asyncio.run(main())
```

---

## Docker Deployment

```bash
# Build
docker build -t competitive-intel .

# Or run full observability stack (Grafana, Tempo, Prometheus, Redis, PostgreSQL)
docker-compose up -d
```

---

## Project Structure

```
competitive_intel/
├── src/competitive_intel/
│   ├── agents/          # Researcher, Analyst, Synthesizer, Monitor
│   ├── workflows/       # LangGraph workflows (research + monitoring)
│   ├── tools/           # SerpApi integration (caching, rate limits, retries)
│   ├── models/          # 20+ Pydantic domain models
│   ├── reports/         # Markdown/HTML/PDF/JSON export
│   ├── config/          # Pydantic Settings
│   └── utils/           # Observability, caching, helpers
├── examples/            # basic_research.py, continuous_monitoring.py, advanced_custom_agents.py
├── tests/               # Unit + integration tests
└── scripts/             # setup.sh, run.sh
```

---

## Configuration

All settings via environment variables (prefix `CI_`):

```env
# Required
CI_SERPAPI_API_KEY=your_key
CI_LLM_API_KEY=your_key

# LLM
CI_LLM_PROVIDER=openai
CI_LLM_MODEL=gpt-4o-mini

# SerpApi
CI_SERPAPI_RATE_LIMIT_RPM=100

# Cache
CI_CACHE_ENABLED=true
CI_CACHE_TTL_SECONDS=3600

# Observability
CI_OBS_ENABLED=true
CI_OBS_LOG_LEVEL=INFO
CI_OBS_OTLP_ENDPOINT=http://otel:4317
```

See [`.env.example`](.env.example) for all options.

---

## Extending

### Add a Custom Agent
```python
from competitive_intel.agents import StructuredOutputAgent, AgentConfig
from pydantic import BaseModel

class MySignal(BaseModel): ...

class MyAgent(StructuredOutputAgent):
    def __init__(self):
        super().__init__(AgentConfig(...), MySignal)
```

### Add a Signal Type
1. Add to `SignalType` enum in `models/__init__.py`
2. Add detection keywords in `agents/analyst.py`
3. Add tests

---

## Testing

```bash
make test              # Unit tests (64 passing)
make test-integration  # Requires SERPAPI_API_KEY + OPENAI_API_KEY
```

---

## License

MIT — see [LICENSE](LICENSE)

---

## Acknowledgments

- [SerpApi](https://serpapi.com) for search infrastructure
- [LangGraph](https://langchain-ai.github.io/langgraph/) for workflow orchestration
- [serpapi-search-tools-python](https://github.com/serpapi/serpapi-search-tools-python) for tool integration