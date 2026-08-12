# Pipeline / Migration-Owning Service — Template

> **Template.** This whole file is conditional on one fact: does this repo run Alembic migrations
> and own the schema a sibling read-only service (if any) mirrors? If yes, rename this file to
> `pipeline.md`, fill in every `<placeholder>`, delete AGENTS.md Rule 13's "conditional" framing
> and write it as unconditional fact instead, and wire the two extra `quality-gate.sh` steps this
> file describes. If no — delete this file entirely. An unfilled template is worse than an absent
> one; nobody should be reading Alembic rules for a service that has no migrations.

## Why this is split from the request-serving baseline

The baseline `AGENTS.md`/`quality-gate.sh` this template ships models a **request-serving FastAPI
service** — no Alembic, no worker, no generated docs. A batch/pipeline service that ingests,
transforms, and writes data is a genuinely different shape: it owns a schema, runs on a schedule or
a queue rather than per-request, and often ships both a CLI and a long-running worker that must
agree on behaviour. Rather than genericizing both shapes into one template neither fits well, this
file is the second shape's rules — bolt them onto the baseline, do not try to merge them into it.

## Migrations

**Rule — every schema change is a migration, committed in the same PR as the model change it
implements.** `alembic revision --autogenerate -m "<description>"`, then read the generated file —
autogenerate misses some changes (server-side defaults, some index types) and silently produces an
empty migration for others. Enforcement: `alembic check` in CI (see below), which fails if the
current models disagree with the latest migration.

**Rule — a vector/embedding column's dimension is schema, not config.** Once a migration fixes a
column's width, changing an embedding model with a different output dimension needs a coordinated
migration and a full reindex — never a config-only change. Say in `SSOT.md` exactly which model
and dimension the current migration assumes.

**Rule — never edit a migration that has already been applied anywhere outside your own branch.**
Add a new migration instead, even to fix a mistake in the last one. An edited migration silently
diverges from what production already ran.

**Rule — record every pipeline run**, success or failure, in a `<runs-table>` (start time, end
time, row counts, error if any). A pipeline with no run history cannot be debugged after the fact —
this is the pipeline-repo equivalent of a request log.

## Worker / CLI parity

If this repo ships both a CLI (`typer`, `click`, or similar) and a long-running worker (e.g.
`arq`, `celery`), both must call the **same service functions** — never duplicate the pipeline
logic between them. The CLI exists for manual runs and debugging; the worker exists for scheduled
or queued runs. A CLI-only bug fix that the worker never sees is the classic failure mode here.

## Idempotency and partial failure

A pipeline step that can be re-run (retried, replayed after a crash) must not double-write. Prefer
upserts keyed on a stable natural key over blind inserts, and make each step's "has this already
run" check explicit rather than relying on the caller never retrying.

## Docs generation (if this repo generates committed docs from code)

If a script generates markdown or other docs from source (e.g. `scripts/generate_docs.py`), the
generated output is committed, and CI verifies it is not stale:

```bash
uv run python scripts/generate_docs.py
git diff --exit-code docs/
```

A diff here means someone changed the source without regenerating docs — fail the gate, do not
warn.

## Wiring these into `quality-gate.sh`

Add both steps after "Production Build" in the baseline script, gated the same way "Run Integration
Tests" already is — skip cleanly when `DATABASE_URL` is unset, so a fresh clone with no database
running doesn't fail the gate for a reason unrelated to the code:

```bash
if [ -n "${DATABASE_URL:-}" ]; then
  run "Migration Drift Check" bash -c "uv run alembic upgrade head && uv run alembic check"
fi

run "Docs Drift Check" bash -c "uv run python scripts/generate_docs.py && git diff --exit-code docs/"
```

## Hook: guard the schema file

If a sibling read-only service mirrors this repo's model file, add a `PreToolUse` hook here that
**warns** (never blocks — mirroring a landed change here is the sanctioned edit on that side) when
`src/app/db/models.py` is touched, and a separate guard in `safety-check.sh` that **blocks** any
`alembic downgrade` outright (a forward-only migration policy is much easier to reason about than
one that allows rollback). This is the mirror image of the read-only repo's stricter guard, which
blocks *any* `alembic` subcommand since it should never run migrations at all.
