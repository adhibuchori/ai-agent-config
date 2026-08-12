# Anti-Patterns Index

> Lazy-loaded knowledge base. Load only the file(s) matching your current task.
> Each file is self-contained — root cause + fix + scope.

## Loading Guide

| Trigger / Task                                              | Load                                   |
| -------------------------------------------------------------- | ----------------------------------------- |
| `mypy` fails with a `pydantic.mypy` plugin import error       | pythonpath-breaks-mypy-plugin.md        |
| Writing or debugging a `.claude/hooks/*.sh` PostToolUse hook  | hooks-silent-noop-on-macos.md           |

## When to add a new entry

A new anti-pattern qualifies when:

- It cost real debugging time (>30 min)
- The root cause is non-obvious from reading code/docs
- Same trap is likely to recur (vendor bug, environment quirk, tooling gotcha)

If the bug gets fixed upstream, **delete the file** — don't leave stale entries.

## File naming convention

`<scope>-<short-description>.md` — kebab-case, descriptive enough to skip without opening.
