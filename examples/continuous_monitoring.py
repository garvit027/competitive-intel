#!/usr/bin/env python
"""Continuous monitoring example - demonstrates monitoring workflow."""

import asyncio
import signal
from competitive_intel import (
    MonitoringWorkflowConfig,
    create_monitoring_workflow,
)
from competitive_intel.models import (
    Entity,
    EntityType,
    ResearchBrief,
    SignalType,
)


class MonitoringApp:
    """Continuous monitoring application."""

    def __init__(self):
        self.workflow = None
        self.running = False

    async def setup(self, topic: str, entities: list[str], interval_minutes: int = 60):
        """Setup monitoring configuration."""
        entity_list = [Entity(name=name.strip(), type=EntityType.COMPANY) for name in entities]

        brief = ResearchBrief(
            topic=topic,
            entities=entity_list,
            signal_types=[
                SignalType.PRODUCT_LAUNCH,
                SignalType.FUNDING,
                SignalType.ACQUISITION,
                SignalType.PARTNERSHIP,
                SignalType.LEADERSHIP_CHANGE,
                SignalType.PRICING_CHANGE,
                SignalType.CUSTOMER_WIN,
                SignalType.EARNINGS_REPORT,
            ],
            time_range="past_day",  # Only recent for monitoring
            depth="quick",
        )

        config = MonitoringWorkflowConfig(
            interval_seconds=interval_minutes * 60,
            alert_threshold="medium",
            alert_on_new_signals=True,
            persist_signals=True,
        )

        self.workflow = create_monitoring_workflow(
            monitor_config=brief,  # type: ignore
            config=config,
        )

    async def run_continuous(self):
        """Run continuous monitoring loop."""
        if not self.workflow:
            raise RuntimeError("Call setup() first")

        self.running = True
        print(f"Starting continuous monitoring (interval: {self.workflow.config.interval_seconds//60} min)")
        print("Press Ctrl+C to stop")

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        await self.workflow.start_continuous()

        try:
            while self.running:
                await asyncio.sleep(60)
                # Print status periodically
                print(f"[{asyncio.get_event_loop().time():.0f}s] Monitoring active...")
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Stop monitoring."""
        print("\nShutting down...")
        self.running = False
        if self.workflow:
            await self.workflow.stop_continuous()


async def main():
    """Run continuous monitoring."""
    app = MonitoringApp()

    # Configure what to monitor
    await app.setup(
        topic="AI Infrastructure Companies - Competitive Monitoring",
        entities=[
            "NVIDIA",
            "AMD",
            "Intel",
            "Google Cloud",
            "AWS",
            "Microsoft Azure",
            "CoreWeave",
            "Lambda Labs",
        ],
        interval_minutes=30,
    )

    try:
        await app.run_continuous()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())