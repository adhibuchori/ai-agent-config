# Code Review Checklist

On-demand reference: CLAUDE.md lists it under **On-demand References**, and nothing imports it.
Where the repo has an `AGENTS.md`, a reviewer subagent checks its numbered rules mechanically; this
is the human checklist around it. `/review` reads it, and `/ship` fixes what it finds down to
MEDIUM.

The base below applies to every stack; skip a section the change cannot touch (a docs site runs no
queries). Each stack adds its own checks in the marked section at the end, citing its `AGENTS.md`
rules by number there, where it has them, rather than here.

## When to review

- After writing or modifying code
- Before any commit to a shared branch
- When the diff touches authentication, authorization, user data, the env schema, or anything that
  reads a secret
- When a query, schema or migration changes
- Before merging a pull request

**Before requesting review:** CI is green, conflicts are resolved, and the branch is up to date
with its target.

## Machine first

Run CLAUDE.md § Quality Gates before reading a line. The gates already fail on formatting, lint,
types, dead code, coverage, secrets and folder shape, so flagging those by hand is noise. Spend the
review on what no gate can see: behaviour, contracts, data access, and whether the change is
testable and honest about its failures.

## Checklist

**Boundaries and contract**

- [ ] Each layer does its own job: entry points (handlers, pages, CLI commands) stay thin glue, and
      logic lives where a unit test can reach it without a live service
- [ ] Cross-module access goes through the module's public entry, never into its internals
- [ ] Errors carry a code from the registry and are mapped in one place; no response leaks an ID, a
      path, a stack trace or an upstream provider's message
- [ ] Every status a route can return is declared, and every code a client can receive is mapped
- [ ] Every new route that changes state declares its auth guard explicitly

**Data and performance**

- [ ] Every list read is bounded and paginated; no deep `OFFSET` paging on a growing table
- [ ] Columns are selected explicitly on wide tables
- [ ] No query or remote call inside a loop, directly or through a helper
- [ ] Every newly filtered, sorted or joined column is indexed in the same change; foreign keys
      always
- [ ] Transactions hold only database work: no HTTP, no cache, no queue publish inside one
- [ ] Writes are batched; an upsert is a real upsert, not select-then-insert
- [ ] A new cache entry has a TTL and an invalidation path in the same change

**Tests**

- [ ] New logic ships with tests that meet the coverage rule (`.claude/rules/*/coverage.md`)
- [ ] A new guard's test was proven by mutating the guarded line and watching it fail
- [ ] No test replaces a module that the shared doubles own

**General**

- [ ] Readable and well named; files within the max-lines limit; nesting no deeper than 4 levels
- [ ] No lint-disable comments, no explicit `any`, no double assertion
- [ ] Every ignored error says why, in the code
- [ ] Docs and comments that describe the changed behaviour were updated with it

## Security review triggers

**Stop and read carefully when the diff touches:** authentication or authorization, user input
handling, raw SQL or template interpolation, a redirect, a shell command, a file path built from
input, an outbound request to a URL a user controls, anything that reads a secret, or the env
schema.

## Severity levels

| Level    | Meaning                                  | Action                             |
| -------- | ---------------------------------------- | ---------------------------------- |
| CRITICAL | Security vulnerability or data loss risk | **BLOCK** — must fix before merge  |
| HIGH     | Bug or significant quality issue         | **WARN** — should fix before merge |
| MEDIUM   | Maintainability concern                  | **INFO** — fix now; `/ship` does   |
| LOW      | Style or minor suggestion                | **NOTE** — optional                |

## Common issues to catch

**Security**

- Hard-coded credentials; environment read outside the one env module
- SQL injection: interpolation into a raw query outside the data-access layer
- Error responses leaking internals
- A new endpoint outside the rate limit or request budget the rest of the API sits behind
- CORS without an origin allowlist
- Unescaped user input rendered as HTML; path traversal; server-side requests to user-supplied URLs

**Correctness**

- An async call that is never awaited: it type-checks and silently discards its result
- A cache key missing an input that changes the answer
- A code-side fallback that turns a missing env key into a quiet wrong address instead of a crash
- A bare catch that swallows the failure; a blocking call on an async path

**Performance**

- N+1 access patterns
- Unbounded reads
- A cache added where an index was missing
- Heavy work repeated on every render or request that could be computed once

## Approval criteria

- **Approve** — no CRITICAL or HIGH issues
- **Warning** — only HIGH issues (merge with caution)
- **Block** — CRITICAL issues found

## Stack checks

<stack-block name="review-checks">

FastAPI service. Rule numbers are this repo's `AGENTS.md`.

- [ ] Handlers stay HTTP glue: at most 15 lines, one service call, no provider or database import
      (Rule 4)
- [ ] Services take providers as default parameters and never import FastAPI's `Request` or
      `Response` (Rule 5)
- [ ] A new module is listed in all three `[[tool.importlinter.contracts]]` blocks in
      `pyproject.toml`; `lint-imports` cannot see a module that no contract names (Rules 7–8)
- [ ] Services raise `DomainError` subclasses, and only `core/errors/problems.py` builds a response;
      `detail` holds no stack trace, key or upstream body (Rules 9–11)
- [ ] A new error class is raised somewhere and sets `status` and `title` on the class (Rule 9)
- [ ] Every vendor call goes through its `Protocol`, carries an explicit timeout and a bounded
      retry, and turns vendor exceptions into `UpstreamProviderError` (Rule 12)
- [ ] `src/app/db/models.py` is unchanged, or mirrors a change that landed in the schema owner
      first; a read-only repo gains no write SQL and no Alembic (Rule 13)
- [ ] Long generations stream, the completion status is checked before accumulated text is used,
      and a safety refusal is never retried (Rules 14–15)
- [ ] Route tests drive the real `app` through `httpx.ASGITransport` and assert the problem+json
      shape, not only the status (Rule 18)
- [ ] A new `/v1/*` route sits behind the service-token check, compared with
      `hmac.compare_digest` (Rule 19)
- [ ] `os.environ` is read only in `core/settings/config.py`, and a new variable reaches
      `.env.<target>.example` in the same change (Rules 20–21)
- [ ] No `typing.Any`; received JSON goes through a Pydantic model or `TypeAdapter` (Rule 26)
- [ ] A value another place must spell the same way is declared once and imported; a vendor's own
      vocabulary stays literal (Rule 27)
- [ ] Every `# noqa` and `# type: ignore` carries its reason on the same line (Rule 25)
- [ ] No database session is held open across a generation, and no `await` sits in a loop where a
      batch call exists (`.claude/rules/backend/performance.md`)
- [ ] Input that reaches an embedding or completion call has a size cap, so one request cannot buy
      an unbounded provider bill
- [ ] A change to the embedding model, chunk size or overlap is treated as a corpus change: a
      dimension migration and a full re-index ship with it, or it fails at query time, not at boot
- [ ] Where the repo owns a pipeline: stages stay pure (no I/O in the transform stages), no stage
      reaches into another's internals, an unchanged re-run writes zero rows, the failure path
      still records the run, and a migration ships with every model change (drift gate:
      `alembic upgrade head && alembic check`)
- [ ] No secret, key or full provider payload reaches a log line

**Machine first, in this stack.** Formatting is ruff's, types are mypy's (strict), layers are
`lint-imports`', dependency advisories are `pip-audit`'s and secrets are gitleaks'; spend the review
on provider behaviour, prompt and response handling, error shapes, and whether a test can run
without the live provider. The reviewer subagent reports rule violations; do not ask it for
refactors.

</stack-block>
