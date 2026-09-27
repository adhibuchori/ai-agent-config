# Agents Index

Subagents live in `.claude/agents/`, and this table is how an agent finds out that one exists. Add
a row when you add a file: a subagent missing from this table is, in practice, never used.

| Agent | Use it for | Checks |
| --- | --- | --- |
| `ai-reviewer` | a modified module, before a commit | `AGENTS.md` Rules 4–27 that the gates cannot see: layer boundaries, the error envelope, provider indirection, the schema mirror, streaming, tests, security, typing past the `Any` ban, one home per identifier, ASGI wiring |

Invoke it deliberately: `/review` delegates its detailed pass to `ai-reviewer`, or ask for the
`ai-reviewer` subagent by name. Its description does not ask to be used proactively, so do not
count on Claude reaching for it unprompted. Its `tools:` line gives it `Read`, `Grep`, `Glob` and
`Bash` (for `git diff`), and no `Write` or `Edit` tool.

Its human counterpart, for what no rule number covers, is `.claude/docs/code-review-checklist.md`.
