# Contributing to dooservice agent

Thanks for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Coding Standards](#coding-standards)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
Please report unacceptable behavior to <dev@apiservicesac.com>.

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker
- Git

### Setup

```bash
git clone https://github.com/dooservice/dooservice-agent.git
cd dooservice-agent
make install
```

This installs all dependencies and sets up pre-commit hooks.

## Development Workflow

### Running tests

```bash
make test          # All tests with coverage
make test-fast     # Quick tests, stop on first failure
make test-verbose  # Verbose output
```

### Code quality

```bash
make lint          # Run ruff linter
make lint-fix      # Auto-fix linting issues
make format        # Format code with ruff
make check         # Run all quality checks
```

### Type checking

```bash
make typecheck     # Run basedpyright
```

### Building locally

```bash
make compile       # Compile standalone binary with PyInstaller
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`: `git checkout -b feat/my-feature`
3. Make your changes
4. Run quality checks: `make check test`
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add backup compression support`
   - `fix: resolve container cleanup on failed creation`
   - `docs: update CLI usage examples`
   - `refactor: simplify instance lifecycle state machine`
6. Push to your fork and open a Pull Request

### PR Guidelines

- Keep PRs focused on a single concern
- Include tests for new functionality
- Update documentation if needed
- Ensure all CI checks pass

## Reporting Bugs

**Security vulnerabilities**: Do NOT open a public issue. Email <dev@apiservicesac.com> instead.

For regular bugs, open a [GitHub Issue](https://github.com/dooservice/dooservice-agent/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, Docker version
- Relevant logs or error messages

## Suggesting Features

Open a [GitHub Issue](https://github.com/dooservice/dooservice-agent/issues/new?template=feature_request.md) with:

- Description of the feature
- Use case and motivation
- Proposed implementation (optional)

## Coding Standards

### Style

- **Formatter/Linter**: [Ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`)
- **Line length**: 120 characters
- **Type hints**: Required for all public APIs
- **Type checker**: [basedpyright](https://github.com/DetachHead/basedpyright) in standard mode

### Architecture

This project uses a **workspace monorepo** with `uv`. Each package in `packages/` has a single responsibility:

| Package | Responsibility |
|---------|---------------|
| `dooservice-models` | Domain types (msgspec Structs) |
| `dooservice-packet` | JWE encrypted protocol |
| `dooservice-docker` | Docker container management |
| `dooservice-postgres` | PostgreSQL + PgDog lifecycle |
| `dooservice-instance` | Instance lifecycle |
| `dooservice-backup` | Backup/restore operations |
| `dooservice-addons` | GitHub addon management |
| `dooservice-dns` | DNS management |
| `dooservice-health` | Health checks |
| `dooservice-proxy` | Traefik reverse proxy |
| `dooservice-s3` | S3/MinIO storage |
| `dooservice-db-agent` | SQLite persistence |
| `dooservice-sdk` | Unified async facade |
| `dooservice-cli` | CLI interface (cyclopts) |
| `dooservice-agent` | WebSocket agent (main entry) |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

Scope: package name without `dooservice-` prefix (e.g., `instance`, `backup`, `cli`)

## License

By contributing, you agree that your contributions will be licensed under the [LGPL-3.0](LICENSE) license.
