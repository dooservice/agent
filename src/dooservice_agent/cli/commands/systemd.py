"""Agent daemon management via systemd."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

import cyclopts

from dooservice_models import DEFAULT_DATA_DIR

from ..errors import ExitCode
from ..output import output

app = cyclopts.App(name="agent", help="Manage the dooservice-agent daemon via systemd")

SERVICE_NAME   = "dooservice-agent"
UNIT_PATH      = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
TEMPLATES_DIR  = Path(__file__).parent.parent.parent / "templates"
UNIT_TEMPLATE  = TEMPLATES_DIR / f"{SERVICE_NAME}.service"
DEFAULT_CONFIG = DEFAULT_DATA_DIR / "agent.toml"


@app.command
def install(*, config: Path = DEFAULT_CONFIG) -> None:
    """Install the systemd unit file and reload the daemon.

    Args:
        config: Path to the agent.toml config file passed to `serve --config`.
    """
    binary = shutil.which("dooservice-agent")
    if not binary:
        output.error("'dooservice-agent' not found in PATH.")
        sys.exit(ExitCode.GENERAL_ERROR)

    unit_content = UNIT_TEMPLATE.read_text().format(
        exec_start=binary,
        config_path=config,
    )
    try:
        UNIT_PATH.write_text(unit_content)
    except PermissionError:
        output.error(f"Permission denied writing to {UNIT_PATH}. Run as root.")
        sys.exit(ExitCode.GENERAL_ERROR)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    output.success(f"Service '{SERVICE_NAME}' installed at {UNIT_PATH}.")
    output.info("  Run 'dooservice-agent agent enable' to start on boot.")
    output.info("  Run 'dooservice-agent agent start' to start now.")


@app.command
def start() -> None:
    """Start the systemd service."""
    subprocess.run(["systemctl", "start", SERVICE_NAME], check=True)
    output.success(f"Service '{SERVICE_NAME}' started.")


@app.command
def stop() -> None:
    """Stop the systemd service."""
    subprocess.run(["systemctl", "stop", SERVICE_NAME], check=True)
    output.success(f"Service '{SERVICE_NAME}' stopped.")


@app.command
def restart() -> None:
    """Restart the systemd service."""
    subprocess.run(["systemctl", "restart", SERVICE_NAME], check=True)
    output.success(f"Service '{SERVICE_NAME}' restarted.")


@app.command
def status() -> None:
    """Show the systemd service status."""
    result = subprocess.run(["systemctl", "status", SERVICE_NAME])
    sys.exit(result.returncode)


@app.command
def enable() -> None:
    """Enable the service to start automatically on boot."""
    subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
    output.success(f"Service '{SERVICE_NAME}' enabled for automatic start.")


@app.command
def disable() -> None:
    """Disable automatic start on boot."""
    subprocess.run(["systemctl", "disable", SERVICE_NAME], check=True)
    output.success(f"Service '{SERVICE_NAME}' disabled.")


@app.command
def logs(*, follow: bool = True, lines: int = 100) -> None:
    """Stream service logs via journalctl.

    Args:
        follow: Follow log output in real time.
        lines:  Number of prior lines to show.
    """
    cmd = ["journalctl", "-u", SERVICE_NAME, f"-n{lines}"]
    if follow:
        cmd.append("-f")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
