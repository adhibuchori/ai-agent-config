---
paths:
  - 'src/app/db/**'
  - 'alembic.ini'
---

# Alembic and the Schema

`AGENTS.md` Rule 13 (rewritten as the schema owner's version) and the migration rules in §H are the
enforced versions — read them first. **This repo is the only writer to its database and the only
one with migrations.** A reader service keeps a byte-for-byte mirror of `src/app/db/models.py`.

## Where things live

```
src/app/db/models.py                  source of truth for the schema
src/app/db/migrations/env.py          Alembic scaffolding — shapes every future revision
src/app/db/migrations/script.py.mako  revision template
src/app/db/migrations/versions/       generated revisions — never hand-edited
src/app/db/session.py                 @lru_cache'd async engine, one per process
```

## The workflow, in order

```bash
# 1. edit the model
$EDITOR src/app/db/models.py

# 2. generate the revision
uv run alembic revision --autogenerate -m "<what changed>"

# 3. read the generated revision before committing it; this step is not optional
$EDITOR src/app/db/migrations/versions/<new>.py

# 4. apply it and confirm no drift remains
uv run alembic upgrade head
uv run alembic check
```

The model change and its revision land in the **same PR**. A model without its revision passes
ruff and mypy and fails only at runtime, in whichever environment migrates next.

Step 3 exists because `--autogenerate` is a first draft, not an answer. It misses server-side
defaults, does not infer index intent, and will emit a column drop for what you meant as a rename.
Review the revision before you commit it: once it exists, the hook refuses edits to it.

## Never hand-edit a generated revision

`.claude/hooks/migration-guard.sh` blocks writes under `migrations/versions/` for two reasons:

- The SQL drifts from `models.py`, and nothing notices until `alembic check` runs in the gate.
- A revision that has already run somewhere cannot be corrected by editing the file: that
  database's `alembic_version` already points past it. The fix is always a new forward revision.

`env.py` and `script.py.mako` are scaffolding, not generated output. Editing them is legitimate
but affects every future revision, so `post-edit.sh` notes the edit instead of blocking it.

## Never downgrade

`safety-check.sh` refuses `alembic downgrade` in a repo that has `alembic.ini`. A downgrade drops
columns and the data in them, including data a reader service is querying, and embedded chunks
cannot be rebuilt without a full re-embed that costs quota. Roll forward with a new revision, even
when that feels like the longer path.

## The embedding dimension is schema

A `vector(N)` column fixes `N` when it is created. Switching to an embedding model with a different
output dimension is **schema-breaking**, not a config change. It needs, together:

1. a revision that recreates the column **and its vector index** at the new dimension,
2. a full reindex of every document,
3. the same change in the reader service's configuration, from the same constant.

Skip one and the failure surfaces at query time as a dimension mismatch. The app boots fine, so
nothing catches it until someone asks a question. Declare `N` once, in
`core/settings/constants.py`, and import it in `models.py` and the embedding adapter (the one-home
rule); the reader's parity test compares the two checkouts.

## Indexes

A vector index (HNSW, say) is created by a revision, and **its operator class must match the
distance operator the reader queries with**. A mismatch does not error: Postgres falls back to a
sequential scan, and retrieval just gets slower as the corpus grows. Change the metric on both
sides together.

Any column newly used in a `WHERE`, an `ORDER BY` or a join gets its index in the same revision.

## Migration drift in the gate

`uv run alembic upgrade head && uv run alembic check` runs in the quality gate whenever a database
is reachable. `check` reports a difference between `models.py` and the revision chain, so a
non-empty result means a model change shipped without its revision. It is the one gate that
catches the most expensive mistake in this repo: never silence it with an empty revision.

## The reader's role

The reader connects with a read-only role. Provision it once, after `alembic upgrade head` has
created the tables, and keep the statement in `SSOT.md`:

```sql
CREATE ROLE <readonly-role> WITH LOGIN PASSWORD '<password>';
GRANT CONNECT ON DATABASE <database-name> TO <readonly-role>;
GRANT USAGE ON SCHEMA public TO <readonly-role>;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO <readonly-role>;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO <readonly-role>;
```
