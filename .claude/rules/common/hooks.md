# Hooks System

The hooks actually wired in this repo are in `.claude/hooks/`, registered by
`.claude/settings.json`. This file explains the contract they follow and the two portability traps
that make a Python hook silently do nothing.

## Hook Types

- **PreToolUse** — before a tool runs. Exit non-zero to block. Used here for `safety-check.sh`
  (dangerous `Bash`) and `models-mirror-guard.sh` (writes).
- **PostToolUse** — after a tool runs. Advisory. Used here for `auto-lint.sh` then
  `auto-format.sh`.
- **Stop** — session end. Not used in this repo.

## What is wired here

| Hook | Event | Behaviour |
| --- | --- | --- |
| `safety-check.sh` | PreToolUse `Bash` | **blocks** `rm -rf` on protected paths, `git push origin dev\|prod`, shell redirects into `.env`, and any `alembic` subcommand (§D Rule 13 — no migrations, no write role here) |
| `models-mirror-guard.sh` | PreToolUse `Write\|Edit\|MultiEdit` | **warns** on `src/app/db/models.py`, never blocks — mirroring a landed AI-Ingestion change is the sanctioned edit |
| `auto-lint.sh` | PostToolUse | `ruff check` on `.py`, JSON syntax check on `.json`; always exits 0 |
| `auto-format.sh` | PostToolUse | `ruff format` on `.py`; always exits 0 |

`lib.sh` holds the two shared helpers below. It is sourced, never executed.

## Trap 1 — Python tooling is not on PATH

`ruff`, `mypy`, and `pytest` are installed by `uv sync` into `.venv/`, so the guard the TypeScript
repos use — `command -v oxfmt &>/dev/null` — has no Python equivalent that works. A hook written as
`command -v ruff && ruff format "$FILE"` never fires.

`resolve_tool` in `lib.sh` resolves `.venv/bin/<tool>` first, then `uv run <tool>`, then PATH.

## Trap 2 — `timeout` does not exist on macOS

GNU `timeout` ships with coreutils, which macOS does not include. The fleet's TS hooks use:

```bash
timeout 5 oxfmt --write "$FILE" 2>/dev/null || true
```

On a machine without `timeout` that fails with 127, `|| true` swallows it, and the hook exits 0
having formatted nothing. **This is why a hook can look healthy and do nothing.**

`run_capped` in `lib.sh` resolves `timeout` or `gtimeout` and runs the command bare when neither
exists — degrading to "no time cap" rather than "no work done".

## Trap 3 — an inherited `PYTHONPATH` breaks tools that load plugins

If `uv run mypy src` fails with:

```
pyproject.toml:1: error: Error importing plugin "pydantic.mypy":
No module named 'pydantic_core._pydantic_core'
```

the venv is **not** broken. Check `PYTHONPATH` first:

```bash
echo "$PYTHONPATH"                 # must be empty when working in this repo
env -u PYTHONPATH uv run mypy src  # succeeds if this is the cause
```

Some agent harnesses export a `PYTHONPATH` pointing at their own interpreter's `site-packages`.
That directory precedes `.venv/` on `sys.path`, so `pydantic_core/__init__.py` is imported from
*there*, while its compiled `_pydantic_core*.so` is built for that other Python version and is
invisible to this one. The package looks installed and half-imports.

`ruff` is a standalone binary with no plugin loading, so the hooks here are unaffected — this bites
only when running `mypy` by hand.

## Rules for adding a hook here

1. **Prove it fires.** Run it by hand with the env var Claude Code sets, against a file you have
   deliberately broken, and confirm a real change:
   ```bash
   printf 'x   =    { "a":1 }\n' > /tmp/t.py
   CLAUDE_TOOL_INPUT_FILE_PATH=/tmp/t.py bash .claude/hooks/auto-format.sh
   cat /tmp/t.py   # must be reformatted
   ```
   Exit code 0 alone proves nothing.
2. **PostToolUse never blocks.** Always `exit 0`; CI's quality gate is the blocking equivalent.
3. **Do not wire whole-project checks.** `mypy src` and `uv run lint-imports` are cheap in CI and
   slow per keystroke.
4. **Guard generated files, but pick block vs warn deliberately.** Block when hand-editing is never
   correct (AI-Ingestion's `migrations/`); warn when the edit is sometimes the whole point
   (this repo's `models.py`).

## Auto-Accept Permissions

`.claude/settings.json` carries the allow/deny lists. Keep `Write` narrow (`src/**`, `tests/**`) and
keep `.env*`, `SSOT.md`, and `AGENTS.md` denied. Never use a skip-permissions flag.

## TodoWrite

Use it for multi-step work: it surfaces out-of-order steps, missing items, and wrong granularity
early, while they are still cheap to correct.
