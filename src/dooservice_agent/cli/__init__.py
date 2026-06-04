"""DooService Agent CLI."""

from __future__ import annotations

import sys
from importlib.metadata import version

import cyclopts

from dooservice_sdk import CoreError

from .commands import bootstrap_app, pg_app, pgdog_app, proxy_app, serve_app, systemd_app
from .errors import ExitCode
from .output import output

app = cyclopts.App(
    name="dooservice-agent",
    version=version("dooservice-agent"),
    help="DooService Agent — infrastructure management and agent daemon",
)

app.command(serve_app)
app.command(systemd_app)
app.command(bootstrap_app)
app.command(pg_app)
app.command(pgdog_app)
app.command(proxy_app)


def main() -> None:
    try:
        app()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        output.warn("Cancelled.")
        sys.exit(ExitCode.USER_CANCELLED)
    except CoreError as error:
        output.error(f"Error: {error}")
        sys.exit(ExitCode.GENERAL_ERROR)
    except Exception as error:
        output.error(f"Unexpected error: {error}")
        sys.exit(ExitCode.GENERAL_ERROR)
