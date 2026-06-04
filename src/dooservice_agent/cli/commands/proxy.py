"""Traefik proxy container lifecycle commands."""

from __future__ import annotations

import cyclopts

from ..context import open_sdk
from ..output import output

app = cyclopts.App(name="proxy", help="Manage the Traefik proxy container")


@app.command
async def show(*, json: bool = False) -> None:
    """Show the current proxy configuration."""
    async with open_sdk() as sdk:
        proxy_config = await sdk.proxy.get()
    if json:
        output.json(proxy_config)
        return
    output.info("[bold]Proxy[/bold]")
    output.info(f"  base_domain:  {proxy_config.base_domain or '(not set)'}")
    output.info(f"  server_ip:    {proxy_config.server_ip or '(not set)'}")
    output.info(f"  network:      {proxy_config.network_name}")
    output.info(f"  TLS:          {'enabled' if proxy_config.tls.enabled else 'disabled'}")
    if proxy_config.tls.enabled:
        output.info(f"  ACME email:   {proxy_config.tls.acme_email}")
        output.info(f"  wildcard:     {proxy_config.tls.use_wildcard}")
        output.info(f"  staging:      {proxy_config.tls.staging}")
        if proxy_config.tls.dns_provider:
            output.info(f"  DNS provider: {type(proxy_config.tls.dns_provider).__name__}")


@app.command
async def start() -> None:
    """Create and start (or restart if stopped) the Traefik container."""
    async with open_sdk() as sdk:
        with output.status("Starting Traefik..."):
            await sdk.bootstrap.proxy.ensure_running()
    output.success("Traefik running.")


@app.command
async def stop() -> None:
    """Stop the Traefik container."""
    async with open_sdk() as sdk:
        with output.status("Stopping Traefik..."):
            await sdk.bootstrap.proxy.stop()
    output.success("Traefik stopped.")


@app.command
async def destroy() -> None:
    """Remove the Traefik container (TLS certificates are preserved)."""
    async with open_sdk() as sdk:
        with output.status("Removing Traefik container..."):
            await sdk.bootstrap.proxy.destroy()
    output.success("Traefik container removed. Certificates are intact.")


@app.command
async def rebuild() -> None:
    """Recreate the Traefik container with the current config (certificates preserved)."""
    async with open_sdk() as sdk:
        with output.status("Rebuilding Traefik..."):
            await sdk.bootstrap.proxy.destroy()
            await sdk.bootstrap.proxy.ensure_running()
    output.success("Traefik rebuilt with current configuration.")


@app.command
async def status(*, json: bool = False) -> None:
    """Show the Traefik container status."""
    async with open_sdk() as sdk:
        info = await sdk.bootstrap.proxy.status()
    if json:
        output.json(info)
        return
    state = "[green]running[/green]" if info.running else "[red]stopped[/red]"
    output.info(f"  status:      {state}")
    output.info(f"  base_domain: {info.base_domain or '(not set)'}")
    output.info(f"  container:   {info.container_id[:12] if info.container_id else '-'}")
    if info.dashboard_domain:
        output.info(f"  dashboard:   {info.dashboard_domain}")
