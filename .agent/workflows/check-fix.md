---
description: Runs the quality gates (format, lint, types, import boundaries, dead code, dependencies, folder shape, coverage policy, tests) and fixes what they report. Edits source files; never commits.
---

<!-- Command: /check-fix -->
<!-- Source: _workflow-source/check-fix.md -->

# /check-fix — Quality Check & Fix

`scripts/check/gates.list` is the list; run it rather than a copy of it:

```bash
uv run ruff format <your files>   # format only what you touched; CI runs ruff format --check .
bash scripts/check/gates.sh       # every gate, read-only; --only <text> re-runs one
```

Fix each failure at its cause:

1. **Lint** (`ruff check .`): add `--fix` for the auto-fixable subset. Never silence with a bare
   `# noqa`: fix the cause, or narrow it to the rule with its reason on the same line (AGENTS.md
   Rule 25). `TID251` and `ANN401` mean an explicit `Any` (Rule 26).
2. **Types** (`mypy .`): always `env -u PYTHONPATH uv run mypy .`. An inherited `PYTHONPATH` can
   shadow the project's venv and silently disable the Pydantic plugin, which produces a wall of
   errors that do not reproduce in CI (`.claude/anti-patterns/pythonpath-breaks-mypy-plugin.md`).
3. **Import boundaries** (`lint-imports`): a layer reached into one it must not know about
   (AGENTS.md §B). Fix the dependency direction, never the contract.
4. **Dead code and dependencies** (`vulture`, `deptry src`): delete what is unused. Something only
   a framework or a caller outside `src/` reads goes in `scripts/vulture/whitelist.py`, with who
   reads it (`.claude/rules/python/dead-code.md`).
5. **Folder shape and coverage policy**: `.claude/rules/common/folder-shape.md` and
   `.claude/rules/python/coverage.md` name the rule each message cites.
6. **Tests** (`pytest tests -q --cov`, 100% of lines and branches): no `--env-file`, matching CI.
   A gap gets a test or a fake, never an exclusion.

Integration tests need the repo's own compose stack:

```bash
docker compose up -d
RUN_INTEGRATION_TESTS=1 env -u PYTHONPATH uv run pytest tests -q -m integration
```

If `AGENTS.md` Rule 13 applies, `src/app/db/models.py` mirrors the schema owner's copy and is never
edited here directly: a task that needs a schema change belongs in the repo that owns the schema.

Output: PASS/FAIL per gate, with what was fixed and what remains.
