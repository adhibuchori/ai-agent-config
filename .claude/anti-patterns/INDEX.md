# Anti-Patterns Index

> Lazy-loaded knowledge base, listed in CLAUDE.md's On-demand References. Load only the file(s)
> whose trigger matches the task. Each file is self-contained — symptom, root cause, fix, scope.

## Loading Guide

| Trigger / Task | Load |
| --- | --- |
| `mypy` fails with a `pydantic.mypy` plugin import error; a venv that looks broken but is not | `pythonpath-breaks-mypy-plugin.md` |
| Writing or debugging a hook that calls a project tool or `timeout`, especially on macOS | `hooks-silent-noop-on-macos.md` |
| A hook that never blocks or never fires; writing any new hook | `hooks-read-env-vars-never-set.md` |
| Writing a check, scan or grep gate; a check that has never failed on a real violation | `a-check-that-matches-nothing-passes.md` |
| Several sessions in one checkout; a commit carrying files you did not stage | `shared-git-index-across-sessions.md` |
| Applying a patch built with `git diff --no-index`; files deleted after `git apply` | `git-apply-check-passes-then-deletes.md` |

## When to add a new entry

A new anti-pattern qualifies when **all** of these hold:

- It cost real debugging time (more than 30 minutes) — in this repo, not in theory.
- The root cause is not obvious from reading the code or the docs.
- The same trap is likely to recur (a vendor behaviour, an environment quirk, a tooling gotcha).

A file written from an imagined risk is worse than no file: it costs context on every load and
teaches a trap that may not exist. Good candidates for a service like this one, once they actually
bite: a vendor SDK behaviour change across a minor version, a vector index whose operator class
does not match the query's and silently degrades to a sequential scan, an event-loop scope
interaction with a process-lifetime cached engine.

Rules that look like anti-patterns are not: they belong in `AGENTS.md`, the enforced, numbered
authority. Do not duplicate a rule here.

If the bug gets fixed upstream, **delete the file** — do not leave stale entries. A row here names
only a file that exists.

## File naming convention

`<scope>-<short-description>.md` — kebab-case, descriptive enough to skip without opening.

## Entry template

```markdown
# <Short title>

**Applies to:** which files, tools or versions
**Status:** permanent, fixed (and where), or known trap

## Symptom
What you observed, including the misleading part.

## Root cause
Why it actually happened.

## Fix
The change that resolved it, and how to verify it.

## Scope
Where it applies, and when this file can be deleted.
```
