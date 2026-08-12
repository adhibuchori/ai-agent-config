# Testing Conventions

`AGENTS.md` §E (Rules 16–18) is the enforced version; the tiers, coverage floor, and loop-scope
constraint are in [../common/testing.md](../common/testing.md). This file covers how to test each
layer.

## Layout

```
tests/unit/test_<module>_service.py   service logic, providers faked
tests/unit/test_<kind>_<vendor>.py    provider adapters, transport faked
tests/                                route tests via httpx.ASGITransport
```

## Service tests — fake the Protocol, not the vendor

A service takes providers as default parameters, so a test passes its own implementation of the
`Protocol`. No `patch`, no mocking library:

```python
class FakeLLMProvider:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    async def generate(self, prompt: str) -> str:
        return self._reply


async def test_answer_includes_expected_content() -> None:
    result = await answer_question("What is it?", llm=FakeLLMProvider("It teaches Python."))
    assert "Python" in result.answer
```

If a service cannot be tested this way, the dependency is imported at module scope instead of taken
as a parameter — fix the signature (§B Rule 5), do not reach for `patch`.

## Route tests — use the real app

Import the real `app` from `main.py` and drive it with `httpx.ASGITransport` (§E Rule 18):

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.post(
        "/v1/chat/completions",
        json={"question": "hi"},
        headers={"X-Service-Token": settings.service_token},
    )
```

This is deliberate: it exercises the real exception handler from `core/problems.py`. A route test
that declares its own error mapper proves nothing about production behaviour — the two drift and the
test keeps passing.

Assert the problem+json **shape**, not just the status: `type`, `title`, `status`, `detail`. A
regression that swaps the envelope while keeping the status code is exactly what §C guards against.

## Provider adapter tests

Test the translation layer, never the vendor:

- A vendor exception becomes `UpstreamProviderError`
- A non-success completion status becomes an error, not an answer (§D Rule 15) —
  `test_llm_<vendor>.py` owns this; it is the one test most worth keeping green
- A timeout becomes `ServiceUnavailableError`

Never a live vendor call and never a real API key, including in an integration test.

## Auth tests

`test_auth_middleware.py` covers §F Rule 19 (if applicable): missing header → 401, wrong token →
401, correct token → passes through. Keep the wrong-token case comparing against a value of the
same length — that is what makes it a test of `hmac.compare_digest` rather than of a length check.

## Integration tests

Marked `@pytest.mark.integration`, gated by `RUN_INTEGRATION_TESTS=1`, run against real
Postgres + Redis. Containers come from `docker compose up -d` — either this repo's own compose
file, or a sibling repo's if Rule 13 applies and that repo owns the database.

If this service holds a read-only role (§D Rule 13), stay read-only, always: a test that needs to
seed rows either uses fixtures created through the schema owner's own tooling, or belongs in that
repo.

## What not to test

- `main.py` — composition only, omitted from coverage by design
- Vendor SDK behaviour — that is their test suite
- Exact LLM output text — assert on structure and on error handling, never on generated prose
