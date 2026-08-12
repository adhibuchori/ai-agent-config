# <Project Name> — Claude Code Config

> Router only — points at detail, does not restate it. Behavioral protocol → AGENTS.md §A.
> Layer boundaries → AGENTS.md §B. Load SSOT.md for architecture/env-var facts.

---

## Project Snapshot

Python 3.12 + FastAPI, async throughout. `<one or two sentences: what this service does, what it
reads/writes, who calls it — not browsers, if that's true for you>`. RFC 9457
`application/problem+json` error contract everywhere.

Dev port: `<port>` · `uv run uvicorn app.main:app --reload --port <port>` · Docs: `/docs` (Scalar) ·
Spec: `/openapi.json`

---

## Quality Gates

Must pass before marking any task done:

```bash
uv run ruff format --check src tests && uv run ruff check src tests
uv run mypy src
uv run lint-imports          # import-linter — module-boundary rules, see AGENTS.md §B
uv run pytest tests -q --cov
RUN_INTEGRATION_TESTS=1 uv run pytest tests -q -m integration   # needs docker compose up -d
```

---

## Task → Section Routing

| Task                                      | Read                                    |
| ------------------------------------------ | ---------------------------------------- |
| New route / handler / service              | SSOT.md §Structure + AGENTS.md §B, §C   |
| Error handling / new DomainError            | AGENTS.md §C                            |
| Adding an LLM/embedding/other provider      | AGENTS.md §D                            |
| Tests (unit/route/integration)              | AGENTS.md §E                            |
| Env vars / secrets                          | SSOT.md §Env Variables, AGENTS.md §F    |
| CI / pipeline                               | `.github/workflows/*`                   |

---

## Naming Conventions

| Type              | Convention                          | Example                    |
| ------------------ | ------------------------------------ | ---------------------------- |
| Module files       | `<name>.py` inside `modules/<mod>/` | `chat/service.py`          |
| Domain error class | `PascalCase` ending in `Error`      | `ChatCompletionError`      |
| Provider protocol  | `PascalCase` ending in `Provider`/`Retriever` | `LLMProvider`, `Retriever` |
| Pydantic schema    | `PascalCase` ending in `Schema`     | `ChatRequestSchema`         |
| Test file          | `test_<unit>.py`                    | `test_chat_service.py`     |
| Directories        | `snake_case`                        | `src/app/modules/chat/`    |

---

## Language Convention

All code artifacts — identifiers, comments, commit messages, PR descriptions — are English.

---

## Commit Format

```
type: description
```

Types: `feat` · `fix` · `refactor` · `chore` · `docs` · `style` · `perf` · `test`. Lowercase,
imperative, no trailing period.

---

## Branching

| Branch                       | Purpose                                    |
| ----------------------------- | ------------------------------------------- |
| `internal/{scope}`           | Experiments, proof of concept, scoped work |
| `dev`                        | Active development — all scopes merge here first |
| `prod`                       | Stable, deployed code                      |

Merge order: `internal/{scope}` → `dev` → `prod`. Never push directly to `dev` or `prod`.

---

## Protected Files

Never edit directly:

```
.env.development / .env.production  ← secrets; the .example templates document the schema
src/app/db/models.py     ← if Rule 13 applies, must stay a byte-for-byte mirror of the schema
                            owner's copy — see AGENTS.md §D
.github/settings.json (if present)
```

---

## Notes

- If this service has no migrations and no write role to its database, say so here explicitly and
  point at AGENTS.md §D Rule 13 — a task that seems to need a schema change belongs in whichever
  repo owns that schema, not here.
- `strip-ai-on-pr.yml` removes `.claude/`, `AGENTS.md`, `CLAUDE.md`, `SSOT.md` from `prod` on
  every merge.

---

## Optional Shared Docs

Three templates ship in `.claude/` as `*.example.md`. Each covers a capability this config can use
but does not require. **Fill one in, rename it to drop `.example`, then uncomment its import line
below.** Delete the ones you do not need — an unfilled template is worse than an absent one.

| Template                            | Covers                                                         | Delete it if                        |
| ------------------------------------ | ---------------------------------------------------------------- | ------------------------------------- |
| `DATABASE.example.md`               | Database access over MCP — topology, tunnel, production rules  | You give agents no database access  |
| `OPENPANEL.example.md`              | Read-only analytics access                                     | You have no analytics backend       |
| `SERENA-WORKSPACE.example.md`       | Umbrella Serena workspace spanning several repos                | You run a single repo, not a fleet  |

<!-- @.claude/DATABASE.md -->
<!-- @.claude/ANALYTICS.md -->
<!-- @.claude/SERENA-WORKSPACE.md -->

A fourth, `pipeline.example.md` under `.claude/rules/backend/`, covers Alembic migrations and
worker/CLI parity — only relevant if this service owns a schema rather than reading one. See
AGENTS.md §D Rule 13.
