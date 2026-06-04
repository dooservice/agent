"""PgDog connection pooler container lifecycle commands."""

from __future__ import annotations

import cyclopts

from ..context import open_sdk
from ..output import output

app = cyclopts.App(name="pgdog", help="Manage the PgDog connection pooler container")


@app.command
async def start() -> None:
    """Create and start (or restart if stopped) the PgDog container."""
    async with open_sdk() as sdk:
        with output.status("Starting PgDog..."):
            await sdk.bootstrap.pgdog.ensure_running()
    output.success("PgDog running.")


@app.command
async def stop() -> None:
    """Stop the PgDog container."""
    async with open_sdk() as sdk:
        with output.status("Stopping PgDog..."):
            await sdk.bootstrap.pgdog.stop()
    output.success("PgDog stopped.")


@app.command
async def destroy() -> None:
    """Remove the PgDog container (config directory is preserved)."""
    async with open_sdk() as sdk:
        with output.status("Removing PgDog container..."):
            await sdk.bootstrap.pgdog.destroy()
    output.success("PgDog container removed. Config directory is intact.")


@app.command
async def rebuild() -> None:
    """Recreate the PgDog container with the current config (config dir preserved)."""
    async with open_sdk() as sdk:
        with output.status("Rebuilding PgDog..."):
            await sdk.bootstrap.pgdog.destroy()
            await sdk.bootstrap.pgdog.ensure_running()
    output.success("PgDog rebuilt with current configuration.")


@app.command
async def status() -> None:
    """Show the PgDog container status."""
    async with open_sdk() as sdk:
        svc = await sdk.bootstrap.pgdog.status()
    state = "[green]running[/green]" if svc.running else "[red]stopped[/red]"
    output.info(f"  status:    {state}")
    output.info(f"  container: {svc.container_id[:12] if svc.container_id else '-'}")
