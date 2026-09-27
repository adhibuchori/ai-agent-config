# Hooks that silently do nothing on macOS

**Applies to:** any `.claude/hooks/*.sh` that calls a project tool (`ruff`, `mypy`, `pytest`) or
`timeout`, written against a Linux CI runner's assumptions
**Status:** Fixed in `.claude/hooks/lib.sh` (`resolve_tool`, `run_capped`); kept so a new hook
does not reintroduce either half

## Symptom

A hook exits 0 every time and looks healthy in every log, but the file it should have formatted or
linted is never touched. Exit code alone looks fine, so nothing announces the failure.

## Root cause

Two independent traps, both silent:

1. **The tool is not on the hook's `PATH`.** `uv sync` installs `ruff`, `mypy` and `pytest` into
   `.venv/bin/`, which a hook's `PATH` never includes. A hook guarded with
   `command -v ruff &>/dev/null` always misses, and the guard skips the rest of the hook: no
   error, no output.
2. **`timeout` does not exist on macOS.** GNU `timeout` ships with coreutils, which macOS does not
   include. `timeout 5 ruff format "$FILE" 2>/dev/null || true` fails with exit 127 (command not
   found), `|| true` swallows it, and the hook reports success having formatted nothing.

Both produce the same observable behaviour: exit 0, no visible error, no work done.

## Fix

- `resolve_tool` looks in `node_modules/.bin`, then `.venv/bin`, then `PATH`, and fails when none
  has the tool, so the caller skips it on purpose. It never falls back to a package runner
  (`uvx`, `npx`, `bunx`): a hook must not download and run an unpinned package.
- `run_capped` uses `timeout` or `gtimeout` when one exists; otherwise a background timer stops the
  command at the cap. Running uncapped is not an option for a guard: one still running when Claude
  Code's own hook timeout fires lets the call through.

## Verification — prove the hook fires

Never trust exit code 0 alone. Feed the hook the JSON Claude Code sends on stdin, for a file inside
the repo that you broke on purpose:

```bash
printf 'import os\nx   =    { "a":1 }\n' > zz-probe.py
printf '{"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"%s/zz-probe.py"}}' "$PWD" \
  | bash .claude/hooks/post-edit.sh
cat zz-probe.py && rm zz-probe.py
```

The file must come back formatted (`x = {"a": 1}`), and the unused import must be reported as an
`additionalContext` JSON line on stdout. A file still broken means the hook did nothing: check that
`.venv/bin/ruff` exists (`uv sync`). For the input contract itself, see
`hooks-read-env-vars-never-set.md`.

## When to revisit

If every machine that runs these hooks guarantees GNU coreutils and a `PATH`-exposed venv, this
class of failure stops being possible — but verify by running the probe above before deleting this
entry.
