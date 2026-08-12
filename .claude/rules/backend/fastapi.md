# FastAPI Patterns

`AGENTS.md` §B (Rules 4–8, layer boundaries) and §C (Rules 9–11, error contract) are the enforced,
numbered versions — read those first. This file is the deeper reference: the patterns those rules
assume you already know.

## Where things live

```
api/router.py       aggregates every module router under /v1
api/middleware.py   service-token verification (§F Rule 19, if applicable)
api/deps.py         shared FastAPI dependencies
core/config.py      pydantic-settings; the only os.environ reader (§F Rule 20)
core/errors.py      DomainError hierarchy
core/problems.py    the single exception handler (§C Rule 10)
core/openapi.py     schema customisation; Scalar UI at /docs
main.py             app assembly — registers the handler, mounts the router
```

## Route declaration

Routes bind a handler and a `response_model`; they hold no logic:

```python
router = APIRouter(prefix="/chat", tags=["chat"])
router.add_api_route(
    "/completions",
    chat_completion_handler,
    methods=["POST"],
    response_model=ChatResponseSchema,
)
```

Declare the error statuses a route can actually return in its `responses=` map. If the generated
OpenAPI is consumed by another repo, an undeclared 404 or 429 is a broken contract for the caller
even though the code "works".

## Handlers stay HTTP glue

≤15 lines, one service call, no provider or DB import (§B Rule 4). No try/except around a
`DomainError` — let it propagate to `core/problems.py`. A handler that catches and re-shapes an
error has silently created a second error envelope, which is exactly what §C exists to prevent.

## Services own the logic

Providers arrive as default parameters, never module-scope singletons pulled in at import time:

```python
async def answer_question(
    question: str,
    llm: LLMProvider = <vendor>_llm_provider,
) -> AnswerSchema: ...
```

That signature is what makes the function unit-testable with a fake and swappable in production
without touching the service (§B Rule 5, §D Rule 12).

Services must not import `fastapi.Request` / `Response`. If a service needs something from the
request, the handler extracts it and passes it as an argument.

## Errors

Raise, never return. `core/errors.py` provides `NotFoundError`, `ValidationError`,
`UnauthorizedError`, `RateLimitedError`, `ServiceUnavailableError`, `UpstreamProviderError`;
module-specific subclasses live in `<module>/errors.py`.

The response shape is RFC 9457 `application/problem+json`:
`{type, title, status, detail, instance, code?}`. `detail` is client-safe — a provider's raw error
body, a stack trace, or a key never belongs there (§C Rule 11). Put that context in the structlog
event instead.

## Auth

If every `/v1/*` route requires a service-token header (§F Rule 19), compare it with
`hmac.compare_digest`, never `==`. State plainly here whether this service has end-user auth at
all — a service consumed only by other backend services, never by browsers, is a design decision
worth writing down, not leaving implicit.

## Async discipline

- `httpx.AsyncClient` for HTTP, SQLAlchemy's async session for DB — never their sync counterparts.
- If your engine is `@lru_cache`d for the process lifetime, do not create a second engine per
  request; that is what exhausts a limited connection budget.
- Streaming responses must not hold a DB session open across the whole generation — read what you
  need, release, then stream.

## Adding a module

Follow the recipe in `AGENTS.md` §B verbatim, then add the container name to **all three**
`[[tool.importlinter.contracts]]` blocks in `pyproject.toml`. Miss that and the new module's
layering is unchecked — CI stays green while the boundary it was supposed to enforce does not
exist.
