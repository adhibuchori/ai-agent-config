# PostToolUse hooks silently do nothing on macOS

**Applies to:** `.claude/hooks/auto-format.sh`, `auto-lint.sh`, or any hook using `timeout` or
`command -v <tool>` written against a Linux CI runner's assumptions
**Discovered:** verified in the source fleet this template is drawn from
**Status:** Fixed by `.claude/hooks/lib.sh`'s `resolve_tool`/`run_capped` helpers — kept as a
reference so a future hook doesn't reintroduce either half

## Symptom

A hook exits 0 every time, looks "healthy" in any log, but the file it should have formatted or
linted is never actually touched. Easy to miss because exit code alone looks fine.

## Root Cause

Two independent traps, both silent:

1. **Tooling not on `PATH`.** `ruff`, `mypy`, `pytest` are installed by `uv sync` into `.venv/`,
   not exposed globally. A hook guarded with `command -v ruff &>/dev/null` always misses, and the
   guard just skips the rest of the hook — no error, no output.
2. **`timeout` doesn't exist on macOS.** GNU `timeout` ships with coreutils, which macOS does not
   include by default. `timeout 5 ruff format "$FILE" 2>/dev/null || true` fails with exit 127
   (command not found), and `|| true` swallows that exit code — so the hook reports success having
   formatted nothing.

Both failure modes produce the same observable behavior: exit 0, no visible error, no actual work
done. That combination is what makes this worth a dedicated anti-pattern entry instead of a
one-line comment — it doesn't announce itself.

## Fix

`resolve_tool` in `.claude/hooks/lib.sh` checks `.venv/bin/<tool>` first, then falls back to
`uv run <tool>`, then bare `PATH`. `run_capped` checks for `timeout` or `gtimeout` and, if neither
exists, runs the command bare rather than silently skipping it — degrading to "no time cap" instead
of "no work done".

## Verification a new hook actually fires

Never trust exit code 0 alone. Run it by hand against a file you've deliberately broken:

```bash
printf 'x   =    { "a":1 }\n' > /tmp/t.py
CLAUDE_TOOL_INPUT_FILE_PATH=/tmp/t.py bash .claude/hooks/auto-format.sh
cat /tmp/t.py   # must be reformatted — if it's still broken, the hook did nothing
```

## When to revisit

If the CI/dev environment guarantees GNU coreutils and a PATH-exposed venv, this class of failure
stops being possible — but verify by hand before deleting rather than assuming it no longer
applies.
