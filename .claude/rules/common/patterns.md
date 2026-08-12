# Common Patterns

The concrete, enforced version of everything here is `AGENTS.md`. This file names the patterns this
repo uses and points at where each one is specified.

## Reuse before writing

Before implementing anything non-trivial: check whether an existing module already demonstrates
the shape, check PyPI for a battle-tested library, and check the vendor docs (Context7) for the
API's actual behaviour — vendor SDKs change across minor versions. Prefer adopting a proven
approach over net-new code, but not at the cost of a dependency this repo does not need
(`coding-style.md`, YAGNI).

## Architectural patterns in this repo

| Pattern | Where it is specified |
| --- | --- |
| Modular monolith — feature verticals under `src/app/modules/<domain>/` | `SSOT.md` §Structure |
| `routes → handlers → service → (repository)` | `AGENTS.md` §B Rules 4–6; enforced by the import-linter *layers* contract |
| Repository is escalation-only, not mandatory | `AGENTS.md` §B Rule 6 |
| Dependency injection via default parameters — no container, no mocking library | `AGENTS.md` §B Rule 5; `common/testing.md` |
| Module barrel — `__init__.py` is a module's only public surface | `AGENTS.md` §B Rule 7; import-linter *independence* contract |
| One-way dependency direction: `modules → core/providers`, never the reverse | `AGENTS.md` §B Rule 8; import-linter *forbidden* contract |
| Single error envelope — RFC 9457 `application/problem+json` | `AGENTS.md` §C Rules 9–11 |
| One exception handler for the whole app, registered once in `main.py` | `AGENTS.md` §C Rule 10 |
| Provider = `Protocol` + default adapter, per external dependency | `AGENTS.md` §D Rule 12; `.claude/rules/backend/providers.md` |
| Streaming-by-default for long-running generation calls | `AGENTS.md` §D Rule 14 |
| Service-token auth on `/v1/*`, no end-user auth (if applicable) | `AGENTS.md` §F Rule 19 |
| `settings` as the only reader of `os.environ` | `AGENTS.md` §F Rule 20 |

The layering here is **machine-checked**, not just advisory: the three
`[[tool.importlinter.contracts]]` blocks in `pyproject.toml` fail CI on a violation, so §B is
enforced, not aspirational. Run it locally with `uv run lint-imports`.

## Patterns deliberately NOT used

- **A DI container.** Default parameters cover every case this repo has (§B Rule 5).
- **A generic repository base class.** Repositories appear per module, only when Rule 6's
  escalation threshold is met — most modules have none.
- **Alembic / any migration tooling, if Rule 13 applies to this repo.** A read-only service holds
  no write role; the schema owner runs migrations (§D Rule 13). `safety-check.sh` should block
  `alembic` here on purpose — see `.claude/rules/backend/pipeline.example.md` for the reverse case.
- **A second error envelope.** There is exactly one, and `core/problems.py` is the only place that
  builds it. A handler with its own try/except around a `DomainError` is the drift to catch.
- **Non-streaming vendor calls for long-running generation.** Streaming is the default, to avoid
  HTTP timeouts on long generations (§D Rule 14).
- **A shared `test-utils` package.** Fakes stay module-local until real duplication proves
  otherwise.
