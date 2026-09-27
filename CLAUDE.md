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

## Agent Tooling

- Serena symbol search: scope every call with `relative_path`. In a multi-repo workspace, read
  `.claude/SERENA-WORKSPACE.md` first.
- Library APIs: check the current docs through Context7 before relying on training data; vendor
  SDKs change across minor versions.
- Python tools run through `uv run`. Run mypy and pytest as `env -u PYTHONPATH uv run …` when a
  harness may export its own `PYTHONPATH`.

**Command wrapper.** If you route terminal commands through a wrapper — an output filter, a
sandbox, a recorder — declare it here as a hard rule and prefix every command in this file with
it; a wrapper mentioned only in passing gets dropped the moment a task gets busy. It wraps the
whole invocation (`<wrapper> uv run pytest …`), not just `uv`. List it under `commandWrappers` in
`.claude/agent-config.json` too, so the safety hook judges the command it wraps, and read diffs and
check results unfiltered. With no wrapper, the commands below are already correct.

---

## Quality Gates

Must pass before marking any task done:

```bash
uv run ruff format <your files>   # format only what you touched
bash scripts/check/gates.sh       # every gate in scripts/check/gates.list, read-only
RUN_INTEGRATION_TESTS=1 env -u PYTHONPATH uv run pytest tests -q -m integration   # needs docker compose up -d
```

`scripts/check/gates.list` is the list, and the commit hook runs the same set
(`uv run pre-commit run --all-files`); read the list rather than a copy of it here. `--only <text>`
runs the gates whose command contains the text. A repo that owns its schema adds
`uv run alembic upgrade head && uv run alembic check` (`.claude/examples/pipeline/README.md`).

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
| Test file          | `test_<source file>.py` at the source's mirror path | `tests/unit/modules/chat/test_service.py` |
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
imperative, no trailing period. `git add -A` is used only inside `/ship`, which states its own
guards; everything else, `/checkpoint` included, stages and commits by pathspec.

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
.env.development / .env.production  ← secrets; locked (see below), the .example files document
                                      the schema
src/app/db/models.py     ← if Rule 13 applies, must stay a byte-for-byte mirror of the schema
                            owner's copy — see AGENTS.md §D
```

**Secrets and production writes are locked, and only the user opens them** (`docs/unlock.md`).
Read an env file with `bash scripts/env/show.sh <file>` (secrets masked, missing keys listed).
Change a value only while `env` is unlocked:
`printf '%s' "$VALUE" | bash scripts/env/set.sh <file> <KEY>`. When locked, ask the user to run
`! ./scripts/ops/unlock.sh env` (or `db`; `status` and `off` too). Never run it yourself: the
hooks refuse it, and asking in the chat opens nothing.

---

## Notes

- If this service has no migrations and no write role to its database, say so here explicitly and
  point at AGENTS.md §D Rule 13 — a task that seems to need a schema change belongs in whichever
  repo owns that schema, not here.
- `strip-ai-on-pr.yml` removes `.claude/`, `AGENTS.md`, `CLAUDE.md`, `SSOT.md` from `prod` on
  every merge.

---

## On-demand References

Nothing below loads automatically. Read the file when its row matches the task. A `*.example.*`
file is a template: copy it to the path in the row and fill it in, and delete the rows and
templates you do not use — an unfilled template is worse than none.

| Read when | File |
| --- | --- |
| Hooks, GitHub and CI traps, reviews, MCP pins, deploys | `.claude/OPERATIONS.md` (from `OPERATIONS.example.md`) |
| CI runner pools and their variables | `.claude/CI-RUNNERS.md` (from `CI-RUNNERS.example.md`) |
| Postgres through `db-dev`/`db-prod`: topology, tunnel, production rules | `.claude/DATABASE.md` (from `DATABASE.example.md`) |
| The read-only analytics API | `.claude/ANALYTICS.md` (from `ANALYTICS.example.md`) |
| One Serena workspace spanning several repos | `.claude/SERENA-WORKSPACE.md` (from `SERENA-WORKSPACE.example.md`) |
| Reviewing a change, before any commit | `.claude/docs/code-review-checklist.md` |
| Known traps — scan the triggers before debugging | `.claude/anti-patterns/INDEX.md` |
| A hook refused something, or its per-repo settings | `.claude/hooks/README.md` |
| Unlocking `.env*` files or production writes | `docs/unlock.md` |
| This repo owns its schema: Alembic, worker, CLI | `.claude/examples/pipeline/README.md` |
| A rarely used MCP server, loaded with `claude --mcp-config` | `.claude/mcp/<name>.json` (from `*.example.json`) |
