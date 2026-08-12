<!-- Agents live in .claude/agents/ — authoritative list: ls .claude/agents/ -->
<!-- Manual invoke only — no auto-trigger. Call explicitly via the Task tool. -->

| Category | Agent         | Use For                     | Validates / Does                                                     |
| -------- | ------------- | ---------------------------- | ---------------------------------------------------------------------|
| Custom   | `ai-reviewer` | Reviewing a modified module  | Layer boundaries, error envelope, provider indirection, code quality |

One agent today, and the index still earns its place: it is what an agent reads
to discover that any agent exists. Add a row when you add a file — an agent that
is not listed here is, in practice, never invoked.
