# CLAUDE.md
## Coding Guidelines

### Style

- **OOP over FP**: prefer classes and methods; avoid loose standalone functions floating outside any class
- **No underscore prefixes**: do not use `_name`, `_variable`, `__method` naming conventions
- **Descriptive names**: every variable, function, and class must have a clear, self-explanatory name; single or two-letter names are not acceptable
- **Simple and direct**: write code that is easy to read at a glance; avoid unnecessary verbosity, redundant comments, or over-engineering
- **No unnecessary validation**: only validate at real system boundaries (user input, external APIs); do not add defensive checks for things that cannot happen internally

### Error handling

- Each package has its own `errors.py` with domain-specific exception classes
- All exceptions inherit from a base error (e.g. `NotFoundError`, `ConflictError`, `DnsError`) so callers can catch by category
- Error classes encode context in `__init__` and produce a readable message via `super().__init__(...)`
- Never raise generic `Exception` or `ValueError` for domain failures — always use a named error class
- Cross-package error mapping lives in its own file (e.g. `cli/errors.py` maps domain errors to exit codes)

### Constants

- All shared constants live in `dooservice_models/constants.py` — ports, image names, container names, paths, timeouts
- Constants are module-level `UPPER_SNAKE_CASE` variables, not magic numbers scattered through the code
- Related exit codes or code groups go in a plain class with class-level attributes (e.g. `class ExitCode`)
- Never hardcode values that already exist in `constants.py`

### Models

- Domain models use `msgspec.Struct` — not dataclasses, not Pydantic
- ORM models (Tortoise) live in `models.py` and are strictly separate from domain structs
- Every ORM model implements `from_struct(cls, ...)` and `to_struct(self)` for clean conversion
- Domain ID types are declared as type aliases: `ProjectId = uuid.UUID`
- State and mode enumerations use `StrEnum`
- Struct methods that mutate state call `self.touch()` to update `updated_at`

### Repository pattern

- Repositories are classes named `XxxRepository` with `@staticmethod` async methods
- They raise domain errors (never return `None` for a missing record — raise `XxxNotFoundError`)
- They do not contain business logic — only persistence operations

### Interfaces and factories

- Contracts are defined as `Protocol` classes (e.g. `DnsManager`)
- Factory functions (`create_xxx`) instantiate the correct implementation from a config/union type using `match`

### General conventions

- `from __future__ import annotations` at the top of every file
- All I/O and service methods are `async`/`await`
- `match`/`case` for dispatch over union types or string tags — no long `if/elif` chains
- CLI output always goes through the `output` object — never raw `print()`
- **All imports at the top of the file** — never inside functions, methods, or classes; local imports are not acceptable under any circumstance
