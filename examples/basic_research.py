#!/usr/bin/env python
"""Basic research example - demonstrates core functionality."""

import asyncio
from competitive_intel import (
    create_research_workflow,
    create_report_generator,
    ExportFormat,
)
from competitive_intel.models import (
    Entity,
    EntityType,
    ResearchBrief,
    SignalType,
)


async def main():
    """Run a basic competitive intelligence research task."""

    # Define the research brief
    brief = ResearchBrief(
        topic="AI Foundation Model Companies - Competitive Landscape Q4 2024",
        entities=[
            Entity(name="OpenAI", type=EntityType.COMPANY),
            Entity(name="Anthropic", type=EntityType.COMPANY),
            Entity(name="Google DeepMind", type=EntityType.COMPANY),
            Entity(name="Meta AI", type=EntityType.COMPANY),
            Entity(name="Mistral AI", type=EntityType.COMPANY),
        ],
        signal_types=[
            SignalType.PRODUCT_LAUNCH,
            SignalType.FUNDING,
            SignalType.PARTNERSHIP,
            SignalType.LEADERSHIP_CHANGE,
            SignalType.PRICING_CHANGE,
        ],
        time_range="past_month",
        depth="standard",
        focus_areas=[
            "model releases and capabilities",
            "enterprise adoption",
            "pricing strategy changes",
            "partnerships with cloud providers",
        ],
        exclude_terms=["rumor", "speculation", "unconfirmed"],
    )

    print(f"Starting research on: {brief.topic}")
    print(f"Tracking {len(brief.entities)} entities")
    print(f"Monitoring {len(brief.signal_types)} signal types")

    # Create and run workflow
    workflow = create_research_workflow()
    report = await workflow.run(brief)

    # Generate report
    generator = create_report_generator()

    # Export as Markdown
    md_path = await generator.export_report(report, brief, ExportFormat.MARKDOWN)
    print(f"\nMarkdown report saved to: {md_path}")

    # Export as HTML
    html_path = await generator.export_report(report, brief, ExportFormat.HTML)
    print(f"HTML report saved to: {html_path}")

    # Export as JSON
    json_path = await generator.export_json(report, brief)
    print(f"JSON report saved to: {json_path}")

    # Print summary
    print(f"\n--- Research Summary ---")
    print(f"Title: {report.title}")
    print(f"Confidence Score: {report.confidence_score:.2f}")
    print(f"Signals Detected: {len(report.signals)}")
    print(f"Entities: {len(report.entities)}")
    print(f"Citations: {len(report.citations)}")
    print(f"Sections: {len(report.sections)}")

    # Show top signals by severity
    if report.signals:
        print(f"\n--- Top Signals ---")
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
        sorted_signals = sorted(report.signals, key=lambda s: severity_order.get(s.severity, 5))
        for signal in sorted_signals[:5]:
            print(f"  [{signal.severity.upper()}] {signal.title}")
            print(f"      Type: {signal.signal_type.value} | Confidence: {signal.confidence.value}")


if __name__ == "__main__":
    asyncio.run(main())