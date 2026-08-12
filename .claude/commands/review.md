---
description: Review staged or branch changes against this repo's backend rules.
---

<!-- Command: /review -->
<!-- Source: _workflow-source/review.md -->

# /review — Backend Code Review

Delegate the detailed pass to `.claude/agents/ai-reviewer.md`; this command frames what it looks
at and in what order.

## Step 1: Scope

```bash
git diff dev...HEAD --stat
git diff dev...HEAD
```

## Step 2: Security First — Block On These

- Hardcoded secrets or credentials
- Raw SQL string interpolation instead of parameterised SQLAlchemy queries
- A route that reads or writes data without the service-token check (AGENTS.md §F Rule 19)
- Error responses leaking internal detail (stack traces, vendor error bodies) — AGENTS.md Rule 11
- A vendor call with no timeout or no bounded retry
- A non-success completion status treated as usable output (AGENTS.md §D Rule 15)

## Step 3: Correctness

- A service calling a vendor SDK directly instead of through its `Protocol` (AGENTS.md §D Rule 12)
- A handler with its own try/except around a `DomainError`, instead of letting it propagate to the
  single exception handler (AGENTS.md §C Rule 10)
- If Rule 13 applies: a schema-mirror file (`db/models.py`) edited without a matching upstream
  migration landing first
- A blocking (sync) call on an async path — `httpx.AsyncClient`/async SQLAlchemy session only

## Step 4: Structure

- Files under 150 lines, functions under 50
- Layer boundaries respected (AGENTS.md §B) — `uv run lint-imports` should already have caught this
- Errors handled explicitly, never swallowed (`except Exception: pass` is always a finding)
- Every `# noqa` / `# type: ignore` carries a same-line justification (AGENTS.md §G Rule 25)

## Step 5: Report

Group findings as CRITICAL / HIGH / MEDIUM / LOW. CRITICAL blocks the merge; HIGH should be
fixed before it. State clearly whether the change is approved, approved with warnings, or
blocked.
