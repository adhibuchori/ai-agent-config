# Testing Requirements

`AGENTS.md` §E (Rules 16–18) is the enforced, numbered version. Layer-specific detail lives in
[../backend/testing.md](../backend/testing.md).

## Two tiers

| Tier | Command | Touches |
| --- | --- | --- |
| Unit | `uv run pytest tests -q --cov` | nothing external — providers mocked, no DB, no Redis |
| Integration | `RUN_INTEGRATION_TESTS=1 uv run pytest tests -q -m integration` | real Postgres + Redis (if this repo uses either) |

Integration tests are marked `@pytest.mark.integration` (registered in `pyproject.toml`) and gated
by `RUN_INTEGRATION_TESTS=1` (§E Rule 17). Locally the containers come from `docker compose up -d`
against this repo's own compose file, or a sibling repo's if Rule 13 applies and that repo owns
the database; CI uses service containers.

## Coverage: 80% minimum

`fail_under = 80` in `[tool.coverage.report]`, measured over `src/app` with `src/app/main.py`
omitted — composition-only code is excluded deliberately rather than left silently untested. Raise
the floor when it is comfortably exceeded; never lower it to make a PR pass.

## Async fixtures — do not change the loop scope

`pyproject.toml` pins both `asyncio_default_fixture_loop_scope` and
`asyncio_default_test_loop_scope` to `session`. If your engine module `@lru_cache`s a
process-lifetime connection pool the way a real production app should, a function-scoped loop
would reuse that pool across event loops and fail with `Event loop is closed`. If a test needs
isolation, give it its own engine — do not flip the scope.

## Test-Driven Development

1. Write the test first (RED)
2. Run it — it must fail
3. Write the minimal implementation (GREEN)
4. Run it — it must pass
5. Refactor (IMPROVE)
6. Check coverage (80%+)

## Mocking: default-parameter override, no mocking library

Services take providers as default parameters (§B Rule 5), so a test overrides them by passing an
argument. No `unittest.mock.patch`, no DI container:

```python
async def test_answers_from_retrieved_context() -> None:
    # Arrange
    fake_llm = FakeLLMProvider(reply="A worked example answer.")

    # Act
    result = await answer_question("What does it teach?", llm=fake_llm)

    # Assert
    assert "worked example" in result.answer
```

## Test Structure (AAA)

Arrange–Act–Assert, with names that state the behaviour under test:

```python
def test_returns_empty_list_when_no_chunks_match_query() -> None: ...
def test_raises_when_service_token_is_missing() -> None: ...
def test_treats_safety_finish_reason_as_an_error_not_an_answer() -> None: ...
```

## Troubleshooting failures

1. Check test isolation — shared session-scoped state is the usual cause here
2. Verify the fake provider actually matches the `Protocol` it stands in for
3. Fix the implementation, not the test — unless the test encodes the wrong expectation

## Never in a test

- A live vendor call or a real API key (§E Rule 16)
- A route test that re-declares its own exception handler instead of importing the real `app`
  (§E Rule 18) — that silently diverges from production
- Writing to a database this service holds only a read-only role against (§D Rule 13, if
  applicable). A test that needs write access belongs in the schema owner's repo.
