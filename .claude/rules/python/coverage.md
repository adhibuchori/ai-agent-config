---
paths:
  - 'src/**'
  - 'tests/**'
  - 'scripts/check/**'
  - 'pyproject.toml'
  - '.pre-commit-config.yaml'
---

# COVER — Test Coverage (Python)

A repo with application logic holds it at 100%: every module that holds logic, including the ones
no test has imported yet. Pre-commit runs `scripts/check/coverage-policy.mjs` and then pytest with
coverage, and the quality gate runs both again on every pull request. A repo with no test runner
configured has nothing to measure.

## What is measured

- Scope: `src/app/**`, through `source =` in `[tool.coverage.run]`, which reports a module no test
  imports at 0%.
- Threshold: `fail_under = 100` with `branch = true`, so every branch counts, not only every line.
- A line exclusion (`exclude_also`) names only lines that never run: a `TYPE_CHECKING` block, an
  abstract or Protocol body. It is a closed list, never a way around a hard test.

## Exempt, and only these

- A package `__init__.py` that only re-exports.
- Generated output: `generated/`, migrations.
- Pure declarations: type-only modules, ORM model modules, and registries a dedicated check already
  asserts.
- Static seed data, listed explicitly: a file, or a folder that holds nothing but data. A new data
  file anywhere else then shows up at 0% and forces a decision.
- Composition roots and raw clients: `main.py`, `cli.py`, the logger, the raw database, cache and
  object-storage clients, and queue and worker wiring. A composition module keeps no logic: a
  closure with a branch moves to a module a test can import.

Each exemption carries its reason in a comment beside it (`omit` in `pyproject.toml`). A module is
never exempted because it is hard to test; it gets a test, or a dependency injected so it can have
one.

## Writing the tests

1. Assert behaviour, never lines. Prove a new guard test by mutating the line it guards, watching
   the test fail, and restoring the line.
2. A defensive branch behind a guard (a handler's own session check) is tested by mounting the
   handler on a bare router without the guard. Never delete the branch to reach 100%.
3. Tests pin every environment value they assert against. Assign it (`monkeypatch.setenv`), never
   default it (`os.environ.setdefault`), so a developer's `.env` cannot change the outcome. The
   suite passes the same with and without a local `.env` file.
4. A time window or a clock is frozen in the test that depends on it, never left to the wall clock.
5. External clients are replaced once, in the shared doubles (`tests/fixtures/`), and steered
   through their controls. Never patch a module from a test file.

## Changing the gate

Lowering a threshold, narrowing the scope, or adding an exemption outside the categories above means
changing this file and `scripts/check/coverage-policy.mjs` together, in one change.
