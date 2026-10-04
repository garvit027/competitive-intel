"""Command-line interface for Competitive Intelligence Platform."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from competitive_intel import (
    ExportFormat,
    MonitoringWorkflowConfig,
    ResearchWorkflow,
    ResearchWorkflowConfig,
    create_monitoring_workflow,
    create_report_generator,
    create_research_workflow,
)
from competitive_intel.config import get_settings
from competitive_intel.models import (
    Entity,
    EntityType,
    ResearchBrief,
    SignalType,
)
from competitive_intel.utils.observability import setup_observability

app = typer.Typer(
    name="competitive-intel",
    help="Competitive Intelligence Platform - AI-powered market research",
    add_completion=False,
)
console = Console()


def setup() -> None:
    """Initialize the platform."""
    setup_observability()


@app.command()
def research(
    topic: Annotated[str, typer.Argument(help="Research topic or question")],
    entities: Annotated[str | None, typer.Option("--entity", "-e", help="Comma-separated entity names")] = None,
    entity_types: Annotated[str | None, typer.Option("--entity-type", "-t", help="Comma-separated entity types")] = None,
    signals: Annotated[str | None, typer.Option("--signal", "-s", help="Comma-separated signal types")] = None,
    time_range: Annotated[str, typer.Option("--time-range", help="Time range (past_day, past_week, past_month, past_year)")] = "past_month",
    depth: Annotated[str, typer.Option("--depth", help="Research depth (quick, standard, deep)")] = "standard",
    format: Annotated[ExportFormat, typer.Option("--format", "-f", help="Output format")] = ExportFormat.MARKDOWN,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    human_review: Annotated[bool, typer.Option("--human-review", help="Enable human review checkpoint")] = False,
) -> None:
    """Run a competitive intelligence research task."""
    setup()

    async def _run():
        # Parse entities
        entity_list = []
        if entities:
            names = [n.strip() for n in entities.split(",")]
            types = [t.strip() for t in entity_types.split(",")] if entity_types else [EntityType.COMPANY] * len(names)
            for name, etype in zip(names, types, strict=False):
                entity_list.append(Entity(name=name, type=EntityType(etype)))

        # Parse signals
        signal_list = []
        if signals:
            signal_list = [SignalType(s.strip()) for s in signals.split(",")]

        # Create brief
        brief = ResearchBrief(
            topic=topic,
            entities=entity_list,
            signal_types=signal_list,
            time_range=time_range,
            depth=depth,
        )

        # Create workflow
        config = ResearchWorkflowConfig(enable_human_review=human_review)
        workflow = create_research_workflow(config=config)

        console.print(Panel.fit(
            f"[bold]Starting Research[/bold]\n"
            f"Topic: {topic}\n"
            f"Entities: {len(entity_list)}\n"
            f"Signals: {len(signal_list) or 'All'}\n"
            f"Time Range: {time_range}\n"
            f"Depth: {depth}",
            title="Competitive Intelligence",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running research workflow...", total=None)
            report = await workflow.run(brief)
            progress.update(task, description="Generating report...")

        # Export report
        generator = create_report_generator()
        output_path = await generator.export_report(report, brief, format, output.stem if output else None)

        console.print(f"\n[green]✓[/green] Report saved to: {output_path}")

        # Print summary
        table = Table(title="Research Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Signals Found", str(len(report.signals)))
        table.add_row("Entities", str(len(report.entities)))
        table.add_row("Citations", str(len(report.citations)))
        table.add_row("Confidence", f"{report.confidence_score:.2f}")
        console.print(table)

    asyncio.run(_run())


@app.command()
def monitor(
    topic: Annotated[str, typer.Argument(help="Monitoring topic")],
    entities: Annotated[str, typer.Option("--entity", "-e", help="Comma-separated entity names")],
    interval: Annotated[int, typer.Option("--interval", "-i", help="Monitoring interval in minutes")] = 60,
    threshold: Annotated[str, typer.Option("--threshold", help="Alert threshold (low, medium, high, critical)")] = "medium",
    once: Annotated[bool, typer.Option("--once", help="Run once and exit")] = False,
) -> None:
    """Start continuous monitoring."""
    setup()

    async def _run():
        names = [n.strip() for n in entities.split(",")]
        entity_list = [Entity(name=name, type=EntityType.COMPANY) for name in names]

        brief = ResearchBrief(topic=topic, entities=entity_list)

        monitor_config = MonitoringWorkflowConfig(
            interval_seconds=interval * 60,
            alert_threshold=threshold,
        )

        workflow = create_monitoring_workflow(
            monitor_config=brief,  # type: ignore
            config=monitor_config,
        )

        if once:
            console.print("[yellow]Running single monitoring cycle...[/yellow]")
            result = await workflow.run_once()
            console.print(f"[green]✓[/green] Found {len(result.signals)} new signals")
        else:
            console.print(Panel.fit(
                f"[bold]Starting Continuous Monitoring[/bold]\n"
                f"Topic: {topic}\n"
                f"Entities: {', '.join(names)}\n"
                f"Interval: {interval} minutes\n"
                f"Alert Threshold: {threshold}",
                title="Monitor Mode",
            ))
            await workflow.start_continuous()
            try:
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping monitor...[/yellow]")
                await workflow.stop_continuous()

    asyncio.run(_run())


@app.command()
def brief(
    topic: Annotated[str, typer.Argument(help="Research topic")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output brief file")],
) -> None:
    """Generate a research brief template."""
    brief = ResearchBrief(
        topic=topic,
        entities=[],
        signal_types=list(SignalType),
        time_range="past_month",
        depth="standard",
        focus_areas=[],
        exclude_terms=[],
        required_sources=[],
        output_format="detailed",
    )

    data = brief.model_dump(mode="json")
    output.write_text(json.dumps(data, indent=2, default=str))
    console.print(f"[green]✓[/green] Brief template saved to: {output}")


@app.command()
def validate(
    brief_file: Annotated[Path, typer.Argument(help="Brief file to validate")],
) -> None:
    """Validate a research brief file."""
    setup()

    try:
        data = json.loads(brief_file.read_text())
        brief = ResearchBrief.model_validate(data)
        console.print(f"[green]✓[/green] Brief is valid: {brief.topic}")
        console.print(f"  Entities: {len(brief.entities)}")
        console.print(f"  Signal Types: {len(brief.signal_types)}")
        console.print(f"  Time Range: {brief.time_range}")
        console.print(f"  Depth: {brief.depth}")
    except Exception as e:
        console.print(f"[red]✗[/red] Invalid brief: {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from competitive_intel import __version__
    console.print(f"Competitive Intelligence Platform v{__version__}")


@app.command()
def demo() -> None:
    """Run a quick demo with sample data."""
    setup()

    async def _demo():
        console.print(Panel.fit(
            "[bold]Competitive Intelligence Demo[/bold]\n"
            "Running a sample research task on AI companies",
            title="Demo",
        ))

        brief = ResearchBrief(
            topic="AI Foundation Model Companies - Competitive Landscape",
            entities=[
                Entity(name="OpenAI", type=EntityType.COMPANY),
                Entity(name="Anthropic", type=EntityType.COMPANY),
                Entity(name="Google DeepMind", type=EntityType.COMPANY),
            ],
            signal_types=[
                SignalType.PRODUCT_LAUNCH,
                SignalType.FUNDING,
                SignalType.PARTNERSHIP,
            ],
            time_range="past_month",
            depth="quick",
        )

        workflow = create_research_workflow()
        report = await workflow.run(brief)

        generator = create_report_generator()
        output_path = await generator.export_report(report, brief, ExportFormat.MARKDOWN)

        console.print(f"\n[green]✓[/green] Demo report saved to: {output_path}")

    asyncio.run(_demo())


if __name__ == "__main__":
    app()