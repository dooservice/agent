"""Agent daemon — connects to NATS, dispatches jobs, and sends heartbeats."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from pathlib import Path
import sys

import psutil

from dooservice_transport.agent import AgentTransport
from dooservice_transport.protocol.messages import JobSubmit

from dooservice_sdk import DooServiceSDK
from dooservice_sdk.jobs.dispatcher import WorkflowDispatcher

from dooservice_models import BackupStatus
from dooservice_db_agent.repositories import BackupRepository

from ..config import AgentConfig, resolve_agent_id
from .scheduler import BackupScheduler

log = logging.getLogger(__name__)


class HeartbeatSender:
    def __init__(self, transport: AgentTransport, interval: int) -> None:
        self.transport  = transport
        self.interval   = interval
        self.start_time = time.monotonic()

    async def run(self) -> None:
        while True:
            try:
                uptime, last_backup_at, last_backup_ok, cpu, mem_pct, mem_used, mem_total, disk_used, disk_total = await self.collect_metrics()
                await self.transport.send_heartbeat(
                    uptime_seconds=uptime,
                    last_backup_at=last_backup_at,
                    last_backup_ok=last_backup_ok,
                    cpu_percent=cpu,
                    mem_percent=mem_pct,
                    mem_used_gb=mem_used,
                    mem_total_gb=mem_total,
                    disk_used_gb=disk_used,
                    disk_total_gb=disk_total,
                )
            except Exception:
                log.exception("Failed to send heartbeat")
            await asyncio.sleep(self.interval)

    async def collect_metrics(self) -> tuple[int, str | None, bool | None, float | None, float | None, float | None, float | None, float | None, float | None]:
        uptime_seconds = int(time.monotonic() - self.start_time)
        last_backup_at: str | None  = None
        last_backup_ok: bool | None = None
        cpu_percent:    float | None = None
        mem_percent:    float | None = None
        mem_used_gb:    float | None = None
        mem_total_gb:   float | None = None
        disk_used_gb:   float | None = None
        disk_total_gb:  float | None = None
        try:
            backup = await BackupRepository.get_latest()
            if backup is not None:
                last_backup_at = backup.created_at
                last_backup_ok = backup.status == BackupStatus.COMPLETED
        except Exception:
            log.exception("Failed to collect backup metrics for heartbeat")
        try:
            cpu_percent   = psutil.cpu_percent(interval=0.1)
            mem           = psutil.virtual_memory()
            mem_percent   = mem.percent
            mem_used_gb   = round(mem.used  / 1024 ** 3, 2)
            mem_total_gb  = round(mem.total / 1024 ** 3, 2)
            disk          = psutil.disk_usage('/')
            disk_used_gb  = round(disk.used  / 1024 ** 3, 2)
            disk_total_gb = round(disk.total / 1024 ** 3, 2)
        except Exception:
            log.exception("Failed to collect system metrics for heartbeat")
        return uptime_seconds, last_backup_at, last_backup_ok, cpu_percent, mem_percent, mem_used_gb, mem_total_gb, disk_used_gb, disk_total_gb


def run(config_path: Path | None = None) -> None:
    config = AgentConfig.load(config_path)

    if not config.nats_url:
        print("ERROR: nats_url is required in config or DOOSERVICE_NATS_URL env var", flush=True)
        sys.exit(1)

    logging.basicConfig(
        level=logging.DEBUG if config.sdk.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    agent_id = resolve_agent_id()
    log.info("Agent ID: %s  Region: %s", agent_id, config.region or "(none)")

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(config, agent_id))


async def serve(config: AgentConfig, agent_id: str) -> None:
    sdk       = DooServiceSDK(config.sdk)
    transport = AgentTransport(
        nats_url=config.nats_url,
        agent_id=agent_id,
        region=config.region,
        user=config.nats_user,
        password=config.nats_password,
        base_domain=config.sdk.proxy.base_domain,
        secondary_domains=config.sdk.proxy.secondary_domains,
    )
    scheduler = BackupScheduler(sdk, max_concurrent=config.max_concurrent_backups)
    sender    = HeartbeatSender(transport, config.heartbeat_interval)

    async with sdk, scheduler:
        await transport.connect()
        dispatcher = WorkflowDispatcher(sdk, scheduler)

        background_tasks: set[asyncio.Task] = set()

        async def dispatch_job(job: JobSubmit) -> None:
            task = asyncio.create_task(dispatcher.run(
                job_id=job.job_id,
                kind=job.kind,
                args=job.args,
                on_progress=transport.report_progress,
                on_completed=transport.report_completed,
                on_failed=transport.report_failed,
            ))
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        await transport.start(
            async_handler=dispatch_job,
            sync_handler=dispatcher.handle_sync,
        )

        heartbeat_task = asyncio.create_task(sender.run())
        try:
            await asyncio.Event().wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            heartbeat_task.cancel()
            await transport.close()
