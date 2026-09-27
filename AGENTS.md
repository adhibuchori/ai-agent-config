# AGENTS.md — <repo-name>

> Numbered, citable rules. Each has an **Enforcement** column naming the CI step or the literal
> tag `advisory` when nothing does yet. Cite rules by number (`Rule 12`) in review comments —
> `scripts/check/ai-config.sh` (pre-commit and CI) fails when a cited number is not defined here.
>
> **If several repos share this numbering, say so here and never renumber locally — only
> append.** Written against a concrete stack — FastAPI, uv, Postgres, an LLM/embedding provider —
> deliberately. A rule genericised into `{{PROVIDER}}` everywhere is unusable until filled in, and
> most people never fill it in. Replace the bracketed vendor/service names below with your real
> ones and delete this paragraph.

## Compliance Status

Fill this in once the codebase exists — a template has nothing to be compliant *with* yet.

| Section | Status | Notes |
| --- | --- | --- |
| §A Protocol | `<Enforced / Partial / Not met>` | `<what applies as written>` |
| §B Layer Boundaries | `<status>` | |
| §C Errors | `<status>` | |
| §D Providers | `<status>` | |
| §E Testing | `<status>` | |
| §F Security | `<status>` | |
| §G Code Quality | `<status>` | |

**Tracked follow-up work:**

1. `<e.g. "no automated drift check between this repo and the schema owner yet">`

Record known behaviour that looks like a bug and is not — that saves the next person from
re-discovering it.

---

## §A. Protocol

**Rule 1** — Read the relevant module before editing it. Find an existing pattern (a sibling
module's routes/handlers/service) and follow it rather than inventing a new shape. Enforcement:
advisory.

**Rule 2** — Minimal, surgical changes. Do not refactor code outside the task's scope in the
same commit. Reuse before writing, in this order: this codebase, the Python standard library,
FastAPI's and Pydantic's built-ins, a dependency already in `pyproject.toml`; only then add a
dependency or new code. Enforcement: advisory (code review).

**Rule 3** — Commit format `type: description` (lowercase, imperative, no trailing period).
Branch prefix `internal/{scope}` off `dev`. Enforcement: advisory.

---

## §B. Layer Boundaries

Every module under `src/app/modules/<domain>/` follows:

```
routes.py       FastAPI APIRouter + response_model bindings. No business logic, no DB/provider
                calls of its own — delegates to handlers.
handlers.py     Thin HTTP glue, ≤15 lines/fn. Reads the validated request, calls exactly one
                service function, shapes the response. No provider/DB imports.
service.py      Business logic. Raises DomainError subclasses. Providers injected via default
                parameter — no DI container, no mocking library.
schemas.py      Pydantic v2 request/response models.
errors.py       Module-specific DomainError subclasses.
__init__.py     Barrel — the only cross-module import surface.
```

**Rule 4 — Handler is HTTP glue only.** No provider or DB import in `handlers.py`. Domain errors
propagate to the global exception handler (see §C) — no try/except around them here.
Enforcement: `import-linter` layers contract (`routes -> handlers -> service -> (repository)`)
in `pyproject.toml`.

**Rule 5 — Service is pure business logic.** Never imports FastAPI's `Request`/`Response`.
Dependencies injected by **default parameter**: `llm: LLMProvider = <vendor>_llm_provider`.
Raises `DomainError` subclasses from `<module>/errors.py`, never returns an ad-hoc
`{"success": False}` shape. Enforcement: advisory (code review — a service importing `fastapi`
request/response types is the tell).

**Rule 6 — Repository is escalation-only, not mandatory.** Default is `handler → service →
provider`. Add `<module>/repository.py` only when the service coordinates multiple queries, needs
a transaction, or the same query bundle is reused elsewhere. Enforcement: advisory.

**Rule 7 — Cross-module imports go through `<module>/__init__.py` only.** Never reach into
another module's `handlers.py` / `service.py` / `schemas.py` / `errors.py` directly. Enforcement:
`import-linter` independence contract on `app.modules.*`.

**Rule 8 — `app.core` and `app.providers` must not import `app.modules`.** Dependencies flow
modules → core/providers, never the reverse. Enforcement: `import-linter` forbidden contract.

### Recipe — adding a new module

```python
# src/app/modules/widgets/errors.py
from app.core.errors.errors import DomainError


class WidgetNotFoundError(DomainError):
    status = 404
    title = "Not Found"

    def __init__(self, widget_id: str) -> None:
        super().__init__("Widget not found.", instance=widget_id, code="WIDGET_NOT_FOUND")


# src/app/modules/widgets/schemas.py
from pydantic import BaseModel


class WidgetSchema(BaseModel):
    id: str
    name: str


# src/app/modules/widgets/service.py (no repository — single provider call, not escalated)
from app.modules.widgets.errors import WidgetNotFoundError
from app.modules.widgets.schemas import WidgetSchema
from app.providers.llm.base import LLMProvider
from app.providers.llm.<vendor> import <vendor>_llm_provider


async def get_widget(widget_id: str, llm: LLMProvider = <vendor>_llm_provider) -> WidgetSchema:
    ...
    if not found:
        raise WidgetNotFoundError(widget_id)
    return WidgetSchema(id=widget_id, name="...")


# src/app/modules/widgets/handlers.py
from app.modules.widgets.schemas import WidgetSchema
from app.modules.widgets.service import get_widget


async def get_widget_handler(widget_id: str) -> WidgetSchema:
    return await get_widget(widget_id)


# src/app/modules/widgets/routes.py
from fastapi import APIRouter

from app.modules.widgets.handlers import get_widget_handler
from app.modules.widgets.schemas import WidgetSchema

router = APIRouter(prefix="/widgets", tags=["widgets"])
router.add_api_route(
    "/{widget_id}", get_widget_handler, methods=["GET"], response_model=WidgetSchema
)

# src/app/modules/widgets/__init__.py
from app.modules.widgets.routes import router as widgets_router

__all__ = ["widgets_router"]
```

Then in `api/router.py`: `api_router.include_router(widgets_router, prefix="/v1")` — nothing else
changes. **Also add the new container to every `[[tool.importlinter.contracts]]` block in
`pyproject.toml`** — miss one and that module's layering goes unchecked while CI stays green. Its
tests mirror the source path: `tests/unit/modules/widgets/test_service.py` and
`tests/routes/modules/widgets/test_routes.py` (`.claude/rules/common/folder-shape.md`).

---

## §C. Errors — RFC 9457

**Rule 9 — Services raise `DomainError` subclasses, never construct a response.**
`src/app/core/errors/errors.py` defines `DomainError` and only the subclasses a service raises
today (typically `ValidationError`, `ServiceUnavailableError`, `UpstreamProviderError`). Each
subclass sets `status` and `title` as class attributes, as the recipe above does. Add a status
class when the first service needs it, not before: an unraised class is dead code that vulture
reports. Enforcement: advisory (code review — a service returning a raw dict/response is the
tell); vulture for unraised classes.

**Rule 10 — A single FastAPI exception handler maps every error to a response.**
`src/app/core/errors/problems.py#domain_error_handler`, registered once in `main.py`. Serializes
`DomainError`, Pydantic `ValidationError`, and any unhandled exception to
`application/problem+json`: `{type, title, status, detail, instance, code?}`. Enforcement: wired
once in `main.py`; a handler with its own try/except around a domain error is a review finding.

**Rule 11 — `DomainError.detail` is client-safe; `cause`/internal context are logs-only.** Never
put a stack trace, an API key, or an internal upstream error body into `detail`. Enforcement:
advisory.

---

## §D. Providers — the "wrapping API" layer

**Rule 12 — Every external dependency (LLM, embedding, or any other vendor call) is a `Protocol`
plus a default adapter, never called directly from a service.** `src/app/providers/<kind>/base.py`
defines the `Protocol`; `src/app/providers/<kind>/<vendor>.py` implements it. A service takes the
protocol type as a default-parameter dependency — see the Recipe above. This is what lets a stub
implementation become a real one in one line, with no service-layer change. Enforcement: advisory
(code review — a service calling the vendor SDK directly, instead of through the `Protocol`, is
the tell).

**Rule 13 — Conditional: if this service reads a database schema it does not own** (a sibling
pipeline/worker repo runs the migrations), keep the read-side model file a byte-for-byte mirror of
that repo's copy, and hold no migration tooling here. If this service owns its own schema
instead, rewrite this rule as the schema owner's version and adopt the pipeline shape from
`.claude/examples/pipeline/README.md`. Enforcement: advisory (no automated drift check
across repos yet — candidate for a future CI job that diffs both model files, if applicable).

**Rule 14 — Streaming is the default for any long-running generation call**, e.g.
`providers/llm/<vendor>.py` uses the vendor's streaming API, never a bare non-streaming call, to
avoid HTTP timeouts on longer generations. Enforcement: advisory.

**Rule 15 — A non-success completion status is checked before reading accumulated text as an
answer.** Some LLM vendors' safety filters can decline a request while still streaming partial
text; the check must happen before that text is treated as usable content, or a refusal reaches
the user as a broken answer instead of a normal error. Enforcement: advisory (code review;
regression test in `tests/unit/providers/llm/test_<vendor>.py`).

---

## §E. Testing

**Rule 16 — Every service gets unit tests** in `tests/unit/modules/<module>/test_service.py`,
mocking providers via the default-parameter override — no live vendor call, no DB, no Redis.
Enforcement: `pytest --cov` in pre-commit and CI; coverage threshold in `pyproject.toml` (100% line
and branch, `.claude/rules/python/coverage.md`).

**Rule 17 — Integration tests are marked `@pytest.mark.integration`, gated by
`RUN_INTEGRATION_TESTS=1`.** Run via `pytest -m integration` against real Postgres/Redis —
`docker compose up -d` locally, service containers in CI. Enforcement: "Run Integration Tests" in
`.github/scripts/quality-gate.sh`, with Postgres and Redis service containers added to
`quality-gate.yml` together with the first integration test (SETUP.md § 6).

**Rule 18 — Route tests use `httpx.ASGITransport` against the real `app` from `main.py`,
importing the real exception handler rather than re-declaring a mapper.** Enforcement: advisory
(code review — a route test with its own inline error handler has silently diverged from
production).

---

## §F. Security

**Rule 19 — Every route under `/v1/*` requires a service-token header, verified against
`<SERVICE>_SERVICE_TOKEN` with `hmac.compare_digest`.** If this service has no end-user auth and
its consumers are backend services rather than browsers, say so here explicitly — that is a
deliberate design choice, not an omission. Enforcement: `api/middleware.py`; regression test in
`tests/unit/api/test_middleware.py`.

**Rule 20 — `core/settings/config.py` is the only file allowed to read `os.environ` directly.**
Everything else imports `settings`. Enforcement: advisory (candidate for a future
`flake8-forbidden-import`-style Ruff rule).

**Rule 21 — `.env` / `.env.local` are never committed; `.env.<target>.example` documents the
schema and must be kept in sync with `core/settings/config.py`.** Enforcement: `.env` committed
check in `quality-gate.sh` (diff-based) + gitleaks secret scan.

**Rule 22 — Service tokens must be at least 32 characters.** Enforcement: `core/settings/config.py`
pydantic validator — the process refuses to boot otherwise.

---

## §G. Code Quality

**Rule 23 — No bare `print()` outside the logging bootstrap (`core/observability/logging.py`).**
Use `structlog` (or your structured logger of choice) everywhere else. Enforcement: Ruff `T20`
(candidate — not yet enabled; advisory for now).

**Rule 24 — `mypy --strict` passes with zero ignores added without a comment explaining why.**
Enforcement: `mypy .` in pre-commit and CI — tests and scripts included, because a fake that does
not match the protocol it stands in for is exactly what strict typing is there to catch.

**Rule 25 — No `# noqa` / `# type: ignore` without a one-line justification comment on the same
line.** Enforcement: advisory (code review).

**Rule 26 — No explicit `Any`.** No `typing.Any` in an annotation or anywhere else, tests included.
JSON you build is `dict[str, object]` or a `TypedDict`; JSON you receive is validated into a
Pydantic model or read through `TypeAdapter`; a value of unknown shape is `object`, narrowed with
`isinstance`. A vendor SDK that returns `Any` is narrowed right where it is called. Enforcement:
Ruff `TID251` (banned `typing.Any`) and `ANN401`, in pre-commit and CI; mypy's
`disallow_any_explicit` stays off because it flags the `__init__` the Pydantic plugin generates
(`.claude/rules/python/types.md`).

**Rule 27 — One home per identifier.** A value another place must spell the same way — an
embedding dimension, a source name, the API version prefix, a provider id — is declared once and
imported everywhere, tests included, so renaming it is one edit. A value that both `core` and `db`
need lives in `src/app/core/settings/constants.py`, a module that imports nothing, so neither layer
has to import the other to reach it. A vendor's vocabulary stays literal (an API version string, a
stream sentinel such as `"[DONE]"`, the set of stop reasons it sends): centralising a value you do
not own makes a second source of truth for something you cannot update. A generated Alembic
revision is frozen and keeps its own copy. Enforcement: advisory (code review). Where a sibling repo
must agree on a value (Rule 13), a parity test reads the sibling checkout by relative path and
reports SKIPPED, never passed, when that checkout is absent.

---

## §P. Payload Contract (where adopted)

Only where the repo adopted the module (a `payload.config.json` exists). The full contract and its
threat model: `.claude/PAYLOAD-CONTRACT.md`; the short form loads from
`.claude/rules/common/payload-contract.md`.

**Rule 28 — Every body that crosses a service boundary is sealed**, unless its route is exempted in
`payload.config.json` with a written reason. A half-policy is chosen by what the body needs
(`response-only` for a multipart upload, `request-only` for an event stream), never by how sensitive
it looks.

**Rule 29 — No route path outside the registry.** Routes and their policies live in one registry
dict, and a test walks `app.routes` against it; a route missing from it fails the registry test.

**Rule 30 — Encrypt at the transport only.** `PayloadMiddleware` is added first (it runs innermost),
replays the opened body as one message, and never invents `http.disconnect`. Nothing else imports
`app.core.payload`.

**Rule 31 — Keys are added, never repurposed**: one variable per hop, `<NAME>_NEXT` for rotation,
never public, never printed or committed. Tests use placeholder bytes and the real cipher.

**Rule 32 — The committed switch says `strict`.** Debug with `PAYLOAD_MODE=off` in your own shell;
every service refuses `off` in production.

---

## Core Files — Handle With Care

| File | Why |
| --- | --- |
| `src/app/core/settings/config.py` | Only file allowed to read `os.environ` (Rule 20) |
| `src/app/core/settings/constants.py` | Values several layers must spell the same way (Rule 27) |
| `src/app/core/errors/problems.py` | The one exception handler (Rule 10) |
| `src/app/db/models.py` | Cross-repo mirror if Rule 13 applies |
| `pyproject.toml` `[[tool.importlinter.contracts]]` | The machine-checked version of §B |
