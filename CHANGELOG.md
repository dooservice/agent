# Changelog

All notable changes to `dooservice-agent` are documented here.

## [1.7.1] — 2026-06-01

### Changed
- Updated `dooservice/core` dependencies to `1.8.1` — picks up the `/web/health` readiness check fix (prevents 404 on first load when re-creating an instance)

---

## [1.7.0] — 2026-06-01

### Changed
- Updated `dooservice/core` dependencies to `1.8.0` — picks up `EnvironmentService.wait_for_ssl()` and the new SSL readiness progress step in provision and clone job handlers

---

## [1.6.0] — 2026-05-26

### Added
- `secondary_domains: list[str]` support — agent reads `[sdk.proxy] secondary_domains` from config and passes it to `AgentTransport`, which includes it in every heartbeat so the orchestrator learns the full set of root domains served by this agent
- `agent.example.toml` documents the new `secondary_domains` field with an inline example
- Updated `dooservice/core` dependencies to `1.7.0`

---

## [1.5.0] — 2026-05-24

### Added
- `HeartbeatSender.collect_metrics()` now also reads `mem.used` and `mem.total` from `psutil.virtual_memory()` and sends them as `mem_used_gb` / `mem_total_gb` in every heartbeat
- Updated `dooservice-transport` dependency to `1.6.0`

---

## [1.4.0] — 2026-05-24

### Added
- `HeartbeatSender.collect_metrics()` now reads `cpu_percent`, `mem_percent`, `disk_used_gb`, `disk_total_gb` via `psutil` and includes them in every heartbeat
- Updated `dooservice/core` dependency to `1.5.0` — requires `AgentHeartbeat` with the 4 new resource fields

---

## [1.3.1] — 2026-05-24

### Fixed
- Updated `dooservice/core` dependency to `1.4.0` — binary now bundles `BackupRepository.get_latest()` and the updated `AgentTransport.send_heartbeat()` signature required by `HeartbeatSender`

---

## [1.3.0] — 2026-05-23

### Added
- `HeartbeatSender` class: replaces standalone `send_heartbeats` function — encapsulates process uptime tracking (`time.monotonic`) and backup status collection before every heartbeat publish
- Heartbeat now includes `uptime_seconds`, `last_backup_at`, `last_backup_ok` — orchestrator persists and exposes these for the admin health drill-down
- Updated `dooservice/core` dependency to `1.4.0`

---

## [1.2.0] — 2026-05-22

### Added
- Agent heartbeat now includes `base_domain` so the orchestrator can construct environment URLs per agent
- Updated `dooservice/core` dependency to `1.3.0`

---

## [1.1.2] — 2026-05-22

### Fixed
- Capture container now starts in release mode (`GIN_MODE=release`)
- Updated `dooservice/core` dependency to `1.2.2`

---

## [1.1.1] — 2026-05-22

### Fixed
- `--help` and `--version` now show the correct version instead of `0.0.0`

---

## [1.1.1] — 2026-05-22

### Fixed
- Capture container now creates correctly on `bootstrap start` / `bootstrap rebuild`
- Updated `dooservice/core` dependency to `1.2.1`

---

## [1.1.0] — 2026-05-22

### Added
- Bootstrap now starts a **Capture** container (`ghcr.io/bluewave-labs/capture:latest`) as part of `bootstrap start`
- Capture domain is `{hostname}.{base_domain}` — unique per agent server, avoiding conflicts across multi-agent setups
- DNS A record for the capture domain is created automatically in Cloudflare on `bootstrap start`
- `bootstrap status` table now includes the capture service row with its domain
- `agent.toml` template and `agent.example.toml` include `capture_api_secret` and `capture_hostname` fields

### Changed
- Updated `dooservice/core` dependency to `1.2.0`

---

## [1.0.1] — 2026-05-22

### Changed
- Updated `dooservice/core` dependency to `1.1.0`
- Odoo containers now enforce swap disabled (`memswap_limit = mem_limit`) and CPU shares proportional to worker count via `OdooResourceLimits`
- Memory cap rounds up to the nearest GB instead of raw MB

---

## [1.0.0] — 2026-05-22

### Added
- **Backup scheduler**: daily automatic backups at 03:00 per-environment timezone for production environments only
  - Per-environment asyncio lock prevents concurrent scheduled + manual backup collisions
  - Up to `max_concurrent_backups` (default 3) backups in parallel across all environments
  - Previous day's backup file deleted (S3 or local) before creating the new one
  - DB records marked `DROPPED`, never deleted — permanent audit history
  - Invalid timezone strings fall back to UTC with a warning instead of crashing the agent
  - Graceful shutdown: waits up to 120 s for in-flight backups before releasing DB connections
  - Auto-unregisters environments that transition out of ACTIVE/PRODUCTION on the next cron fire
- **Interactive installer** (`install.sh`): one-command VPS setup with auto-detected Postgres/PgDog settings based on server RAM and CPU cores
- **Bootstrap CLI** (`bootstrap configure|start|stop|rebuild|status`): full infrastructure stack management
- **Proxy configuration** moved to `bootstrap configure` — single entry point for VPS setup
- Config auto-created from bundled template if no `agent.toml` is found at startup
- Standalone binary distribution via PyInstaller + GitHub Releases

### Changed
- CLI binary renamed from `doos-agent` to `dooservice-agent`
- Config env var renamed from `DOOS_AGENT_CONFIG` to `DOOSERVICE_AGENT_CONFIG`
- Default data directory: `~/.local/share/dooservice` → `/var/lib/dooservice`
- Repository split: shared packages moved to `dooservice/core`; agent repo now contains only the daemon

### Fixed
- Silent backup failures: exceptions are now logged with full context and the backup record is marked `FAILED` in DB
- Archived/deleted environments: scheduler auto-unregisters jobs on the next cron fire instead of attempting backup
- `asyncio.create_task` references now stored to prevent garbage collection before completion
