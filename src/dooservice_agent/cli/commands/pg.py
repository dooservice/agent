"""Shared Postgres container lifecycle commands."""

from __future__ import annotations

import cyclopts

from ..context import open_sdk
from ..output import output

app = cyclopts.App(name="pg", help="Manage the shared Postgres container")


@app.command
async def start() -> None:
    """Create and start (or restart if stopped) the shared Postgres container."""
    async with open_sdk() as sdk:
        with output.status("Starting Postgres..."):
            await sdk.bootstrap.postgres.ensure_running()
    output.success("Postgres running.")


@app.command
async def stop() -> None:
    """Stop the shared Postgres container."""
    async with open_sdk() as sdk:
        with output.status("Stopping Postgres..."):
            await sdk.bootstrap.postgres.stop()
    output.success("Postgres stopped.")


@app.command
async def destroy() -> None:
    """Remove the Postgres container (data volume is preserved)."""
    async with open_sdk() as sdk:
        with output.status("Removing Postgres container..."):
            await sdk.bootstrap.postgres.destroy()
    output.success("Postgres container removed. Data volume is intact.")


@app.command
async def rebuild() -> None:
    """Recreate the Postgres container with the current config (data preserved)."""
    async with open_sdk() as sdk:
        with output.status("Rebuilding Postgres..."):
            await sdk.bootstrap.postgres.destroy()
            await sdk.bootstrap.postgres.ensure_running()
    output.success("Postgres rebuilt with current configuration.")


@app.command
async def status() -> None:
    """Show the Postgres container status."""
    async with open_sdk() as sdk:
        svc = await sdk.bootstrap.postgres.status()
    state = "[green]running[/green]" if svc.running else "[red]stopped[/red]"
    output.info(f"  status:    {state}")
    output.info(f"  container: {svc.container_id[:12] if svc.container_id else '-'}")
