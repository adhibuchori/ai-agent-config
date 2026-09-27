## Summary

<!-- What changed and why, in 1-3 sentences. -->

## How to Verify

<!-- The command or request that shows this working, and what a correct result looks like. Run
     `mypy` and `pytest` as `env -u PYTHONPATH uv run …`: an inherited PYTHONPATH resolves a
     different tree than CI does and hides the failure being looked for. -->

## Checklist

The Quality Gate already ran on this PR. `scripts/check/gates.list` and
`.github/scripts/quality-gate.sh` are the list; copying it here only makes a second one to keep in
step, and the copy is what goes stale. Nothing the gate decides is repeated below: what follows is
the part it cannot decide.

### Boundaries and contract
- [ ] Handler is thin glue with no provider/DB import; the logic lives in a service
      (AGENTS.md §B Rules 4–5)
- [ ] Errors are raised as a `DomainError` and mapped centrally — no error body
      hand-built in a handler (§C)
- [ ] A new module is added to all three `[[tool.importlinter.contracts]]` blocks
      in `pyproject.toml`: `lint-imports` cannot check a module no contract names (§B)
- [ ] The route's `responses` map lists every status the handler can return

### Providers
- [ ] A new external dependency is a `Protocol` + adapter, taken as a default
      parameter — not called directly from a service (§D Rule 12)
- [ ] Long-running generation calls stream by default (§D Rule 14)
- [ ] Completion status is checked before accumulated text is treated as an
      answer (§D Rule 15)
- [ ] A change to retrieval or prompting was compared with the previous behaviour on the same
      question, not only asserted in a unit test

### Cross-repo contract (delete if not applicable)
- [ ] `src/app/db/models.py` unchanged, or changed only to mirror a landed
      migration in the schema-owning repo, linked here (§D Rule 13)
- [ ] No write operation issued against a database this repo holds only a
      read-only role against

### This repo owns its schema and the models changed (delete otherwise)
- [ ] Migration generated with `alembic revision --autogenerate`, committed here, and read by
      hand: autogenerate misses renames, server defaults and index changes
- [ ] `alembic upgrade head` run against a local database, not only generated
- [ ] The downgrade path works, or the migration says in a comment why it is one-way
- [ ] Each reader service mirrors the model change in a follow-up PR, linked here

### Security
- [ ] `.env.<target>.example` updated if a new variable was added
- [ ] No secret, stack trace, or upstream provider body reaches `detail` (§C Rule 11)
- [ ] Application code logs through `structlog`, with no `print()` left behind (§G Rule 23)
