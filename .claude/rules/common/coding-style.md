# Coding Style

`AGENTS.md` §G (Rules 23–25) is the enforced, numbered version. This file is the deeper
reference for the habits those rules assume.

## Immutability

Prefer returning new values over mutating arguments:

```python
# WRONG — mutates the caller's object
def add_tag(doc: Document, tag: str) -> None:
    doc.tags.append(tag)

# CORRECT — returns a new value
def add_tag(doc: Document, tag: str) -> Document:
    return doc.model_copy(update={"tags": [*doc.tags, tag]})
```

Pydantic v2 models are the main carrier here: use `model_copy(update=...)` rather than assigning
to fields in place. Never use a mutable default (`list`/`dict`) as a function default — Ruff `B006`
catches it.

## Core Principles

### KISS (Keep It Simple)

- Prefer the simplest solution that actually works
- Avoid premature optimization
- Optimize for clarity over cleverness

### DRY (Don't Repeat Yourself)

- Extract repeated logic into shared functions or utilities
- Avoid copy-paste implementation drift
- Introduce abstractions when repetition is real, not speculative

### YAGNI (You Aren't Gonna Need It)

- Do not build features or abstractions before they are needed
- Avoid speculative generality — Rule 12's `Protocol` + default adapter exists so a provider can
  be swapped later, not so every function grows an injection point today

## File Organization

MANY SMALL FILES > FEW LARGE FILES:

- High cohesion, low coupling. One responsibility per module file, following the layer names in
  §B (`routes` / `handlers` / `service` / `schemas` / `errors`).
- ~100 lines typical. **There is no automated line ceiling in this repo** — Ruff's config
  (`pyproject.toml`) selects `E,F,I,UP,B,SIM,C4,ASYNC,RUF` and has no `max-lines` equivalent, so
  file size is a review judgement, not a gate. Do not cite a hard limit that nothing enforces.
- Handlers are the exception with a real number: ≤15 lines per function (§B Rule 4).

## Formatting and Linting

Both run over `src tests`, and the same commands run in CI:

```bash
uv run ruff format src tests          # writes
uv run ruff format --check src tests  # CI mode
uv run ruff check src tests
```

`line-length = 100` and `quote-style = "double"` are set in `pyproject.toml`. `E501` is
deliberately ignored — the formatter owns line width, so a lint error about it would just be
noise. Let `ruff format` decide wrapping instead of hand-wrapping to please a linter.

## Typing

`mypy --strict` with `disallow_untyped_defs` (§G Rule 24). Every function, including tests'
helpers, carries annotations; `tests.*` is the one relaxed override. A `# type: ignore` or
`# noqa` needs a justification comment on the same line (§G Rule 25) — an unexplained one is a
review finding, and `warn_unused_ignores` will flag it once it stops being needed.

## Async

This service is async end to end. Ruff's `ASYNC` rules are on, so blocking calls inside an async
function get flagged. Two habits that matter more than the linter:

- Never call a sync HTTP/DB client from an async path — use `httpx.AsyncClient` and SQLAlchemy's
  async session, both already wired.
- Do not `await` inside a loop when one batched call would do; `embed`-style batching exists for
  exactly this reason.

## Error Handling

- Raise `DomainError` subclasses from `<module>/errors.py`; never build a response in a service
  (§C Rule 9).
- Never silently swallow an exception. A bare `except Exception: pass` is always a finding.
- `detail` is client-safe. Stack traces, API keys, and raw upstream bodies are logs-only
  (§C Rule 11).

## Logging

`structlog`, never `print()` (§G Rule 23 — the only exception is `core/logging.py`'s bootstrap).
Log with bound key-value context rather than interpolated strings, so entries stay queryable.

## Code Smells to Avoid

### Deep Nesting

Prefer early returns / guard clauses. Ruff's `SIM` rules catch several of these mechanically.

### Magic Numbers

Name thresholds, delays, and limits — especially retry counts and batch sizes, which are the ones
that get tuned later and need to be findable.

### Long Functions

Split into focused pieces. If a service function is hard to unit-test without a live provider,
that is the signal it needs splitting, not mocking.
