"""Shared infrastructure stack management (Postgres + PgDog + Traefik + Capture)."""

from __future__ import annotations

import sys

import cyclopts

from ..context import open_sdk
from ..errors import ExitCode
from ..output import output

app = cyclopts.App(name="bootstrap", help="Manage the shared infrastructure stack")


@app.command
async def configure(
    *,
    base_domain:      str | None  = None,
    acme_email:       str | None  = None,
    use_wildcard:     bool | None = None,
    staging:          bool | None = None,
    dashboard:        bool | None = None,
    dashboard_domain: str | None  = None,
    dns_provider:     str | None  = None,
    server_ip:        str | None  = None,
) -> None:
    """Configure the proxy base domain, TLS and DNS provider.

    This is the first step when setting up a new VPS. Run it once before
    starting the stack with 'bootstrap start'.

    Any omitted flag falls back to its DOOSERVICE_* environment variable.

    Modes:
      * HTTP only:              --base-domain
      * TLS HTTP-01:            --base-domain --acme-email
      * TLS DNS-01 wildcard:    --base-domain --acme-email --dns-provider X --use-wildcard
      * Auto-CNAME:             --base-domain --acme-email --dns-provider X

    --dns-provider values: cloudflare_token | cloudflare_global_key | route53 |
    digitalocean | gandi | ovh | hetzner | linode | godaddy | namecheap
    """
    async with open_sdk() as sdk:
        try:
            proxy_config = await sdk.bootstrap.configure(
                base_domain       = base_domain,
                acme_email        = acme_email,
                use_wildcard      = use_wildcard,
                staging           = staging,
                dashboard_enabled = dashboard,
                dashboard_domain  = dashboard_domain,
                dns_provider_kind = dns_provider,
                server_ip         = server_ip,
            )
        except ValueError as error:
            output.error(str(error))
            sys.exit(ExitCode.USAGE_ERROR)

    output.success(f"Proxy configured for '{proxy_config.base_domain}'.")
    if proxy_config.tls.enabled:
        if proxy_config.tls.use_wildcard and proxy_config.tls.dns_provider:
            mode = "DNS-01 wildcard"
        elif proxy_config.tls.dns_provider:
            mode = "HTTP-01 + auto-CNAME"
        else:
            mode = "HTTP-01 (manual DNS)"
        suffix = ", staging" if proxy_config.tls.staging else ""
        output.info(f"  TLS: {mode} ({proxy_config.tls.acme_email}{suffix})")
    else:
        output.info("  TLS: disabled (HTTP only)")
    output.info("  Run 'bootstrap start' to bring up the full stack.")


@app.command
async def start() -> None:
    """Start Postgres, PgDog, Traefik and Capture in order."""
    async with open_sdk() as sdk:
        with output.status("Starting stack..."):
            await sdk.bootstrap.ensure_running()
    output.success("Stack running.")


@app.command
async def stop() -> None:
    """Stop Capture, Traefik, PgDog and Postgres in reverse order."""
    async with open_sdk() as sdk:
        with output.status("Stopping stack..."):
            await sdk.bootstrap.stop()
    output.success("Stack stopped.")


@app.command
async def destroy() -> None:
    """Remove all stack containers (data volumes are preserved)."""
    async with open_sdk() as sdk:
        with output.status("Removing stack containers..."):
            await sdk.bootstrap.destroy()
    output.success("Stack containers removed. Data volumes are intact.")


@app.command
async def rebuild() -> None:
    """Recreate all stack containers with the current config (data preserved)."""
    async with open_sdk() as sdk:
        with output.status("Rebuilding stack..."):
            await sdk.bootstrap.destroy()
            await sdk.bootstrap.ensure_running()
    output.success("Stack rebuilt with current configuration.")


@app.command
async def status() -> None:
    """Show the status of all infrastructure services."""
    async with open_sdk() as sdk:
        pg_status, pgdog_status, proxy_status, capture_status = await sdk.bootstrap.status()

    table = output.table(["Service", "Status", "Container ID"])
    for svc in (pg_status, pgdog_status):
        state     = "[green]running[/green]" if svc.running else "[red]stopped[/red]"
        container = svc.container_id[:12] if svc.container_id else "-"
        table.add_row(svc.name, state, container)

    proxy_state     = "[green]running[/green]" if proxy_status.running else "[red]stopped[/red]"
    proxy_container = proxy_status.container_id[:12] if proxy_status.container_id else "-"
    table.add_row("traefik", proxy_state, proxy_container)

    capture_state     = "[green]running[/green]" if capture_status.running else "[red]stopped[/red]"
    capture_container = capture_status.container_id[:12] if capture_status.container_id else "-"
    capture_domain    = sdk.bootstrap.capture.domain
    capture_label     = f"capture ({capture_domain})" if capture_domain else "capture"
    table.add_row(capture_label, capture_state, capture_container)

    output.render(table)
