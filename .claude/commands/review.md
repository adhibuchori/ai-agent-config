---
description: Reviews staged or branch changes against this repo's AI-service rules and the review checklist, and reports findings by severity. Reads only; changes nothing.
---

<!-- Command: /review -->
<!-- Source: _workflow-source/review.md -->

# /review — AI Service Code Review

Delegate the detailed pass to `.claude/agents/ai-reviewer.md`; this command frames what it looks
at and in what order.

Read `.claude/docs/code-review-checklist.md` first: it is the human checklist around the agent,
keyed to this repo's `AGENTS.md` rules, and it does not load on its own.

## Step 1: Scope

```bash
git diff dev...HEAD --stat
git diff dev...HEAD
```

Read the diff unfiltered. If a command-output wrapper summarises or truncates, bypass it: a line it
drops is a finding nobody sees.

## Step 2: Security First — Block On These

- Hardcoded secrets or credentials, API keys and model credentials included, instead of settings
- Raw SQL string interpolation instead of parameterised SQLAlchemy queries
- A route that reads or writes data without the service-token check (AGENTS.md §F Rule 19)
- Error responses leaking internal detail (stack traces, vendor error bodies) — AGENTS.md Rule 11
- A prompt built by concatenating untrusted input without delimiting it
- An embedding or completion call that accepts input of any size: no cap on its length
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
- Errors handled explicitly, never swallowed (`except Exception: pass` is always a finding)
- Every `# noqa` / `# type: ignore` carries a same-line justification (AGENTS.md §G Rule 25)
- Formatting, types, `typing.Any`, dead code, coverage and layer boundaries are the gates' to fail
  (CLAUDE.md § Quality Gates); do not hand-review what they already refuse

## Step 5: Report

Group findings as CRITICAL / HIGH / MEDIUM / LOW. CRITICAL blocks the merge; HIGH should be
fixed before it. State clearly whether the change is approved, approved with warnings, or
blocked.
