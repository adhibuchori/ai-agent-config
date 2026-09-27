# Pipeline shape — a service that owns its schema

> **Not loaded by Claude Code.** Nothing under `.claude/examples/` is a rule until you copy it into
> `.claude/rules/`. Adopt this folder only if this repo ingests, transforms and writes data on a
> schedule or a queue, and owns the schema it writes, with Alembic migrations here. A
> request-serving service that reads a schema owned elsewhere keeps the baseline and deletes this
> folder.

## Why a second shape

The baseline `AGENTS.md` and quality gate model a **request-serving FastAPI service**: no Alembic,
no worker, no generated docs. A pipeline that ingests, transforms and writes data is a different
shape. It owns a schema, runs on a schedule or a queue instead of per request, and usually ships a
CLI and a long-running worker that must behave the same. Rather than one template that fits
neither shape, this folder is the second shape's rules: bolt them onto the baseline, do not merge
them into it.

## What is here

| File | Copy to | Loads while you touch |
| --- | --- | --- |
| `pipeline.md` | `.claude/rules/backend/pipeline.md` | `src/app/pipeline/**`, `src/app/worker/**`, `src/app/cli.py` |
| `alembic.md` | `.claude/rules/backend/alembic.md` | `src/app/db/**`, `alembic.ini` |
| `pipeline-testing.md` | `.claude/rules/backend/pipeline-testing.md` | `tests/**`, `pyproject.toml` |

Each file opens with `paths:`, so none of them adds to the always-loaded budget that
`scripts/check/ai-config.sh` enforces.

## Adopting it

1. **Rules.** Copy the three files above. If the repo serves no HTTP, delete
   `.claude/rules/backend/fastapi.md`, `performance.md` (the request-path budget; the batch budget
   is in `pipeline.md`) and `testing.md`. Keep `providers.md` for the embedding provider.
2. **`AGENTS.md`.** Rewrite Rule 13 as the schema owner's version and append the §H rules below,
   numbered from the next free number. Never renumber an existing rule: `ai-config.sh` fails on a
   citation that no longer resolves. The copied rule files cite §H by rule name, so the numbers
   you choose are free.
3. **`SSOT.md`.** Add the sections below, and describe the layout (`pipeline/`, `worker/`,
   `cli.py`, `db/migrations/`) in § Structure.
4. **`pyproject.toml`.** Add `src/app/cli.py` to `[tool.coverage.run] omit` beside `main.py` (both
   are composition only). Add an import-linter independence contract on `app.pipeline.*` and a
   forbidden contract so `app.core` never imports `app.pipeline` or `app.db`.
5. **Quality gate.** Add the steps under "Gate additions".
6. **Hooks.** Nothing to wire; see "Hooks" for what switches on by itself.
7. **Reviewer.** Add the checks under "Review additions" to `.claude/agents/ai-reviewer.md` and to
   the `review-checks` block of `.claude/docs/code-review-checklist.md`.
8. Delete this folder once its content lives where it belongs.

## `AGENTS.md` — Rule 13 and §H

**Rule 13, rewritten:** this repo owns the schema. `src/app/db/models.py` is the source of truth,
and every change ships with its Alembic revision in the same PR. A reader service keeps a
byte-for-byte mirror of `models.py` and connects with a read-only role. Enforcement:
`alembic upgrade head && alembic check` in the gate.

Append a `§H. Pipeline` section with these rules, each numbered from the next free number:

- **Stages are pure.** `normalize`, `chunk` and the batching logic in `embed` take data and return
  data: no database, no network. Only `sources/*` and `load.py` do I/O. Enforcement: advisory
  (code review — a stage that opens a session or a client is the tell).
- **Stages talk only through their package `__init__.py`.** Enforcement: import-linter
  independence contract on `app.pipeline.*`.
- **Loading is idempotent, keyed on the content hash.** Unchanged content writes nothing and
  leaves `indexed_at` alone; changed content replaces the document's chunks in one transaction,
  delete then insert. Enforcement: the three idempotency tests.
- **Generated revisions are never hand-edited.** `alembic revision --autogenerate`, read the
  result, commit it with the model change. Enforcement: `migration-guard.sh`, and
  `alembic check` in the gate.
- **An embedding dimension is schema, not config.** Changing it means a revision that recreates
  the column and its vector index, a full reindex, and the same change in the reader, all from one
  constant. Enforcement: advisory (code review), plus the reader's parity test.
- **Every run is recorded, success or failure.** Enforcement: `run_pipeline()` writes the run row
  in a try/except; the failure-path test.
- **The worker and the CLI call the same function.** Enforcement: advisory (code review), plus a
  worker test that asserts it calls `run_pipeline()`.
- **A source that reads public content stays unauthenticated.** Enforcement: advisory (code
  review).

## `SSOT.md` additions

```
## Pipeline stage pattern
Each stage is a pure function or async generator; only sources/* and load.py do I/O. A bad answer
then traces to "chunking produced the wrong boundaries" (test chunk alone) or "similarity is off"
(test embed alone), never a vague "something in the pipeline".

## Database schema (owned here)
documents      id, source, external_id, url, title, content_hash, metadata JSONB, indexed_at
chunks         id, document_id FK ON DELETE CASCADE, ordinal, text, token_count,
               embedding vector(<N>), metadata JSONB   -- vector index: <operator class>
pipeline_runs  id, source, started_at, finished_at, status, docs_seen, chunks_written, error

## Provisioning the reader's read-only role
<the statement from alembic.md § The reader's role, with your names>
```

## Gate additions

Add both after the build, and skip the drift check cleanly when no database is reachable, so a
fresh clone without one does not fail for a reason unrelated to the code. In
`.github/scripts/quality-gate.sh`:

```bash
if [ -n "${DATABASE_URL:-}" ]; then
  run "Migration Drift Check" bash -c "uv run alembic upgrade head && uv run alembic check"
fi

run "Docs Drift Check" bash -c "uv run python scripts/generate/docs.py && git diff --exit-code docs/"
```

List the same two commands in `scripts/check/gates.list` (and `.pre-commit-config.yaml`) so
`bash scripts/check/gates.sh` runs them by hand, and name the migration check in CLAUDE.md
§ Quality Gates.

**Generated docs.** When a script generates committed docs from code (the CLI reference, the data
contract), CI regenerates them and fails on any diff: a diff means the source changed without its
docs. Fail the gate; do not warn.

## Hooks

Everything is already wired in `.claude/settings.json`; the layout switches it on:

- **`migration-guard.sh`** refuses Write, Edit and Serena writes under a migrations folder that
  exists. The defaults in `migrationsDirs` include `src/app/db/migrations/versions`,
  `alembic/versions` and `migrations/versions`; set `migrationsDirs` in
  `.claude/agent-config.json` if yours lives elsewhere. With `alembic.ini` present, its message
  names `alembic revision --autogenerate`.
- **`safety-check.sh`** refuses `alembic downgrade` once `alembic.ini` exists.
- **`post-edit.sh`** notes an edit to `env.py` or `script.py.mako`, which shape every future
  revision.

Prove the guard fires once `alembic.ini` and the versions folder exist (it should print the refusal
and exit 2):

```bash
printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/src/app/db/migrations/versions/x.py"}}' "$PWD" \
  | bash .claude/hooks/migration-guard.sh; echo "exit $?"
```

## Review additions

- A stage that imports `app.db`, `sqlalchemy`, `httpx` or a provider, or opens a session, a client
  or a file — BLOCK (stages are pure)
- A provider constructed inside `embed` instead of injected
- A change to `load.py` that skips the content-hash check, updates rows in place, splits delete
  and insert across transactions, or touches `indexed_at` for unchanged content — and any weakened
  idempotency test, including the fewer-chunks case
- A `models.py` change with no new revision in the same diff, or an edited existing revision —
  BLOCK
- A revision whose SQL does not match the model change (a drop where a rename was meant, a missing
  server default, a missing index)
- `alembic downgrade` anywhere — BLOCK
- An embedding model or dimension change without the revision, the reindex and the reader's
  change — BLOCK; a vector index whose operator class does not match the reader's distance
  operator
- A failure path that returns or re-raises without writing the run row, or a swallowed exception
- Pipeline logic written into `worker/tasks.py` or `cli.py` instead of `run_pipeline()`
- Credentials added to a public-content source — BLOCK
- A full-corpus list built from `source.fetch()`, one embedding call per chunk, a transaction that
  spans documents or an embedding call, an unbounded retry, or an engine created per document
