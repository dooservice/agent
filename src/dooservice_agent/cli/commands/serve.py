"""serve command — starts the agent daemon."""

from __future__ import annotations

from pathlib import Path

import cyclopts

from ...daemon.serve import run

app = cyclopts.App(name="serve", help="Start the agent daemon (NATS + job scheduler)")


@app.default
def serve(*, config: Path | None = None) -> None:
    """Connect to the orchestrator via NATS and process jobs.

    Args:
        config: Path to the agent.toml config file. Falls back to
                DOOSERVICE_AGENT_CONFIG env var or default locations.
    """
    run(config_path=config)
