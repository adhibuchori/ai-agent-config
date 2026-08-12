# Code Review Standards

## Purpose

Review ensures quality, security, and maintainability before code is merged. The rule set being
reviewed against is `AGENTS.md` — cite it by number.

## When to Review

**Mandatory triggers:**

- After writing or modifying code
- Before any commit to a shared branch
- When touching auth (`api/middleware.py`), `core/config.py`, or a provider
- When the module layout changes (a new module, a new `repository.py`)
- Before merging a pull request

**Before requesting review:** CI is green, conflicts resolved, branch up to date with the target.

## Review Checklist

- [ ] Layer boundaries hold — `uv run lint-imports` passes
- [ ] Handlers are ≤15 lines and import no provider or DB (§B Rule 4)
- [ ] Services raise `DomainError`, never build a response (§C Rule 9)
- [ ] No new error envelope shape (§C Rules 9–11)
- [ ] Providers reached through their `Protocol`, not called directly (§D Rule 12)
- [ ] No secrets, no `os.environ` read outside `core/config.py` (§F Rule 20)
- [ ] No `print()` (§G Rule 23)
- [ ] Every `# noqa` / `# type: ignore` carries a same-line justification (§G Rule 25)
- [ ] Tests exist for new service functions; coverage ≥ 80% (§E Rule 16)
- [ ] `models.py` unchanged, or changed only to mirror a landed AI-Ingestion PR (§D Rule 13)

## Automated gates — do not re-review by hand

These already fail CI, so flagging them manually is noise:

| Concern | Gate |
| --- | --- |
| Formatting, import order, obvious bugs | `ruff format --check` + `ruff check` |
| Types | `mypy src` (strict) |
| Layer boundaries | `uv run lint-imports` |
| Dependency CVEs | `pip-audit` |
| Secrets, full history | gitleaks |
| Migration drift | n/a here — AI-Ingestion owns it |

Spend review attention on what no gate covers: provider behaviour, prompt/response handling,
error-shape drift, and whether a service is still testable without a live provider.

## Severity Levels

| Level | Meaning | Action |
| --- | --- | --- |
| BLOCK | Rule violation, security issue, or data-loss risk | must fix before merge |
| WARN | Bug or significant quality issue | should fix before merge |
| NOTE | Maintainability or style suggestion | optional |

## Common Issues to Catch

### Security

- A secret, token, or key in code or in an error `detail` (§C Rule 11)
- `os.environ` read outside `core/config.py` (§F Rule 20)
- A `/v1/*` route added without service-token verification (§F Rule 19)
- An upstream provider's raw error body forwarded to the client

### Correctness

- A non-`STOP`/`MAX_TOKENS` `finish_reason` treated as a usable answer (§D Rule 15) — a safety
  refusal reaching the user as a broken answer instead of a clean error
- A bare `except Exception: pass`
- A blocking call on an async path
- `await` inside a loop where one batched call would do

### Structure

- A service that cannot be unit-tested without a live provider — the dependency is imported at
  module scope instead of taken as a default parameter (§B Rule 5)
- A cross-module import reaching past `__init__.py` (§B Rule 7)
- `core`/`providers` importing `modules` (§B Rule 8)

## Using the reviewer agent

`.claude/agents/ai-reviewer.md` checks the diff against `AGENTS.md` mechanically. It reports rule
violations only — it will not propose refactors, and it should not be asked to.

## Approval Criteria

- **Approve** — no BLOCK, no WARN
- **Approve with comments** — only NOTE items
- **Request changes** — any BLOCK

## Related

[testing.md](testing.md) · [security.md](security.md) · [git-workflow.md](git-workflow.md)
