# SSOT.md — <repo-name>

> Every claim below is verified against the source at the time of writing — if you find a
> mismatch, fix this file in the same PR that caused the drift.
>
> Note: `strip-ai-on-pr.yml` deletes this file (and `.claude/`, `AGENTS.md`, `CLAUDE.md`) from
> `prod` on every merge. Anything `prod` genuinely needs belongs in `README.md`.

## What

`<one paragraph: what this service does, what it wraps, and — if this service reads a database it
does not own — what the write side is and where it lives>`.

Consumers are `<backend services / browsers / a queue — pick one and say so>`, authenticated with
`<your auth mechanism>`.

## Stack

Python 3.12 · FastAPI (async) · Pydantic v2 · `<LLM/embedding vendor SDK>` · SQLAlchemy 2.0 async +
asyncpg · Redis (if used) · structlog · Scalar (`/docs`) · uv (package manager).

If this repo has no Alembic migrations, no write path to Postgres, or no embedding call in its hot
path, say so explicitly here and point at the reason — see "Cross-repo contract" below if it's
because a sibling repo owns that responsibility. Add capabilities back alongside the feature that
actually needs them, not speculatively.

## Structure

```
src/app/main.py            bootstrap: import core.config first, mount router, exception
                            handler, lifespan (startup/shutdown), SIGTERM handling
src/app/core/
  config.py                 pydantic-settings — the only file allowed to read os.environ
  logging.py                structlog JSON configuration
  errors.py                 DomainError base + NotFound/Validation/Unauthorized/RateLimited/
                             ServiceUnavailable/UpstreamProvider
  problems.py                DomainError -> RFC 9457 application/problem+json serializer;
                             registered once on the FastAPI app in main.py
src/app/api/
  router.py                  composition ONLY: include_router calls. No routes, no logic.
  deps.py                    provider wiring — default-parameter singletons (AGENTS.md Rule 12),
                              not FastAPI Depends()
  middleware.py               service-token check (Rule 19), request logging, rate limit
src/app/providers/           the "wrapping API" layer — see AGENTS.md §D
  <kind>/base.py               Protocol for one external dependency
  <kind>/<vendor>.py           adapter implementing it
src/app/modules/<domain>/    see AGENTS.md §B for the file pattern
  <example>/                  one route group per module
  meta/                       GET /health, GET /ready
src/app/db/
  session.py                  async engine + session factory
  models.py                   SQLAlchemy models — if Rule 13 applies, must mirror the schema
                               owner's models.py exactly
tests/
  unit/                       service tests, providers mocked via default-param override
  routes/                     httpx.ASGITransport tests against the real app
```

## Module file pattern

See AGENTS.md §B for the full layer-boundary rules and the "adding a new module" recipe. Short
version: `routes.py` (FastAPI router, no logic) → `handlers.py` (HTTP glue, ≤15 lines/fn, no
provider/DB import) → `service.py` (business logic, raises `DomainError`, default-param provider
DI) → `schemas.py` (Pydantic v2) → `errors.py` (module-specific `DomainError` subclasses) →
`__init__.py` (barrel).

## Error contract

RFC 9457 `application/problem+json`: `{type, title, status, detail, instance, code?}`. Single
mapper: the exception handler registered in `main.py` (`core/problems.py#domain_error_handler`).
Pydantic validation failures on request bodies also map to this shape via a FastAPI
`RequestValidationError` handler.

## Cross-repo contract (conditional — delete if this service owns its own schema)

If this service reads a database schema that a sibling pipeline/worker repo owns and migrates,
that boundary is the one place the two repos touch, and it should stay deliberately narrow:

1. **Database.** Both point at the same database. The schema owner runs migrations; this repo
   connects with a read-only role and has no migrations directory at all.
2. **Provisioning the read-only role** (run once against the schema owner's database, after its
   migrations have created the tables):
   ```sql
   CREATE ROLE <readonly-role> WITH LOGIN PASSWORD '<password>';
   GRANT CONNECT ON DATABASE <database-name> TO <readonly-role>;
   GRANT USAGE ON SCHEMA public TO <readonly-role>;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO <readonly-role>;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO <readonly-role>;
   ```
3. **Schema mirror.** `src/app/db/models.py` here must match the schema owner's `src/app/db/models.py`
   field-for-field. A schema change always lands there first (migration + model), then here as a
   follow-up PR (AGENTS.md Rule 13).
4. **Provider/embedding config parity.** If a vector column's dimension or a model name is fixed
   at migration time in the schema owner, that value must be identical across both repos'
   config — changing it is a breaking change requiring a migration and a full reindex there, never
   a config-only change here.
5. **Shared vendor key**, if both repos call the same LLM/embedding vendor — note it here so quota
   is watched in one place, not two.

## Env Variables

Source of truth is `src/app/core/config.py` (pydantic-settings, validated at boot; the process
exits non-zero if invalid). `.env.<target>.example` documents the same schema — keep them in sync.

```
PORT · ENVIRONMENT
<PROVIDER>_API_KEY            <where to get one, and which tier/model the free tier allows>
<PROVIDER>_MODEL               default <model> — note billing tier gotchas if any
DATABASE_URL                   postgresql+asyncpg://<role>:...@host:5432/<database-name>
                                (production; local dev via SSH tunnel uses a different port —
                                see .claude/DATABASE.md if you use it)
DATABASE_POOL_MAX              default 10
REDIS_URL                      redis://host:6379/<db-index> — if this is a shared Redis instance,
                                say which index and never reuse it elsewhere
<SERVICE>_SERVICE_TOKEN         min 32 chars — shared secret, checked via hmac.compare_digest
SENTRY_DSN                     optional
```

## Testing

`pytest tests -q` (unit + route tests, no live Postgres/Redis required) · `pytest -m integration`
(`RUN_INTEGRATION_TESTS=1`, needs `docker compose up -d`). See AGENTS.md §E.

## Branches

```
internal/{scope} -> dev (quality-gate: lint + type-check + import-linter + tests + build)
                  -> prod (quality-gate re-run as a safety net + CI/CD build+deploy + strip-ai)
```
