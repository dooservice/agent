"""Backup scheduler — daily at 03:00 per production-environment timezone."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dooservice_db_agent import BackupRepository, EnvironmentRepository
from dooservice_models import BackupSource, BackupType, EnvironmentMode, LifecycleState

log = logging.getLogger(__name__)

BACKUP_HOUR            = 3
BACKUP_MINUTE          = 0
SHUTDOWN_GRACE_SECONDS = 120


class BackupScheduler:
    def __init__(self, sdk, max_concurrent: int = 3) -> None:
        self.sdk           = sdk
        self.semaphore     = asyncio.Semaphore(max_concurrent)
        self.env_locks: dict[UUID, asyncio.Lock] = {}
        self.running_tasks: set[asyncio.Task] = set()
        self.apscheduler   = AsyncIOScheduler(timezone=ZoneInfo("UTC"))

    async def __aenter__(self) -> BackupScheduler:
        self.apscheduler.start()
        await self.load_active_environments()
        log.info("Backup scheduler started")
        return self

    async def __aexit__(self, *_) -> None:
        if self.apscheduler.running:
            self.apscheduler.shutdown(wait=False)
        if self.running_tasks:
            await asyncio.wait(self.running_tasks, timeout=SHUTDOWN_GRACE_SECONDS)

    def register(self, env_id: UUID, project_id: UUID, timezone: str = "UTC") -> None:
        self.apscheduler.add_job(
            self.run_scheduled_backup,
            "cron",
            hour=BACKUP_HOUR,
            minute=BACKUP_MINUTE,
            timezone=self.resolve_timezone(timezone, env_id),
            id=self.job_id(env_id),
            replace_existing=True,
            kwargs={"env_id": env_id, "project_id": project_id},
        )
        log.info("Registered backup for env %s at 03:00 %s", env_id, timezone or "UTC")

    def unregister(self, env_id: UUID) -> None:
        if self.apscheduler.get_job(self.job_id(env_id)):
            self.apscheduler.remove_job(self.job_id(env_id))
            log.info("Unregistered backup for env %s", env_id)

    async def load_active_environments(self) -> None:
        all_envs = await EnvironmentRepository.list_all()
        eligible = [
            env for env in all_envs
            if env.lifecycle_state == LifecycleState.ACTIVE
            and env.mode == EnvironmentMode.PRODUCTION
        ]
        for env in eligible:
            self.register(env.id, env.project_id, env.config.timezone)
        log.info("Scheduled backups for %d production environment(s)", len(eligible))

    async def run_scheduled_backup(self, env_id: UUID, project_id: UUID) -> None:
        task = asyncio.current_task()
        if task is not None:
            self.running_tasks.add(task)
        try:
            env_lock = self.env_locks.setdefault(env_id, asyncio.Lock())
            if env_lock.locked():
                log.warning("Backup for env %s skipped: already in progress", env_id)
                return
            async with env_lock, self.semaphore:
                await self.execute_backup(env_id, project_id)
        finally:
            if task is not None:
                self.running_tasks.discard(task)

    async def execute_backup(self, env_id: UUID, project_id: UUID) -> None:
        try:
            env = await EnvironmentRepository.get(env_id)
        except Exception:
            log.warning("Backup for env %s cancelled: not found — unregistering", env_id)
            self.unregister(env_id)
            return

        if env.lifecycle_state != LifecycleState.ACTIVE or env.mode != EnvironmentMode.PRODUCTION:
            log.info("Backup for env %s skipped: %s/%s — unregistering", env_id, env.lifecycle_state, env.mode)
            self.unregister(env_id)
            return

        if not env.config.auto_backup_enabled:
            log.info("Backup for env %s skipped: auto_backup_enabled is False", env_id)
            return

        try:
            project = await self.sdk.projects.get_by_id(project_id)
            await self.drop_previous_backups(env_id, project.name)
            backup = await self.sdk.backups.create(
                env, project.name,
                backup_type=BackupType.FULL,
                description="Automatic daily backup",
                source=BackupSource.SCHEDULED,
            )
            log.info("Backup completed for env %s (id=%s, size=%d bytes)", env_id, backup.id, backup.size_bytes)
        except Exception:
            log.exception("Backup FAILED for env %s", env_id)

    async def drop_previous_backups(self, env_id: UUID, project_name: str) -> None:
        # Drops file (S3 or local) and marks record DROPPED — record is never deleted
        for backup in await BackupRepository.list_completed_scheduled(env_id):
            try:
                await self.sdk.backups.drop(backup, project_name)
                log.info("Dropped previous backup %s for env %s", backup.id, env_id)
            except Exception:
                log.warning("Failed to drop backup %s for env %s", backup.id, env_id, exc_info=True)

    @staticmethod
    def job_id(env_id: UUID) -> str:
        return f"backup_{env_id}"

    @staticmethod
    def resolve_timezone(timezone: str, env_id: UUID) -> ZoneInfo:
        if not timezone:
            return ZoneInfo("UTC")
        try:
            return ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            log.warning("Unknown timezone %r for env %s — using UTC", timezone, env_id)
            return ZoneInfo("UTC")
