from __future__ import annotations

import json as json_lib
from typing import Any

import msgspec
from rich.console import Console
from rich.table import Table


class Output:
    def __init__(self, *, no_color: bool = False) -> None:
        self.stdout = Console(no_color=no_color)
        self.stderr = Console(stderr=True, no_color=no_color)

    def success(self, message: str) -> None:
        self.stdout.print(f"[green]{message}[/green]")

    def info(self, message: str) -> None:
        self.stdout.print(message)

    def warn(self, message: str) -> None:
        self.stdout.print(f"[yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        self.stderr.print(f"[red]{message}[/red]")

    def status(self, message: str) -> Any:
        return self.stdout.status(message)

    def json(self, payload: object) -> None:
        encoded = msgspec.json.encode(payload)
        self.stdout.print(json_lib.dumps(json_lib.loads(encoded), indent=2))

    def table(self, columns: list[str]) -> Table:
        return Table(*columns, header_style="bold")

    def render(self, table: Table) -> None:
        self.stdout.print(table)


output = Output()
