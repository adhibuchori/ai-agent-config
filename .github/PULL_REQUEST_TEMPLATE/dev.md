## Description

## Type of Change
- [ ] feat: new feature
- [ ] fix: bug fix
- [ ] refactor: code refactor
- [ ] chore: dependency update / config change
- [ ] docs: documentation update
- [ ] test: tests

## How to Verify

<!-- The command or request that shows this working, and what a correct result
     looks like. "CI is green" is not a verification step — the gate already
     runs formatting, linting, type-checking, import boundaries, tests and the
     build, so do not repeat them here. -->

## Checklist

### Boundaries and contract
- [ ] Handler is thin glue with no provider/DB import; the logic lives in a service
      (AGENTS.md §B Rules 4–5)
- [ ] Errors are raised as a `DomainError` and mapped centrally — no error body
      hand-built in a handler (§C)
- [ ] A new module is added to all three `[[tool.importlinter.contracts]]` blocks
      in `pyproject.toml`, not just imported and left unchecked (§B)
- [ ] The route's `responses` map lists every status the handler can return

### Providers
- [ ] A new external dependency is a `Protocol` + adapter, taken as a default
      parameter — not called directly from a service (§D Rule 12)
- [ ] Long-running generation calls stream by default (§D Rule 14)
- [ ] Completion status is checked before accumulated text is treated as an
      answer (§D Rule 15)

### Cross-repo contract (delete if not applicable)
- [ ] `src/app/db/models.py` unchanged, or changed only to mirror a landed
      migration in the schema-owning repo (§D Rule 13)
- [ ] No write operation issued against a database this repo holds only a
      read-only role against

### Security
- [ ] `.env.<target>.example` updated if a new variable was added
- [ ] No secret, stack trace, or upstream provider body reaches `detail` (§C Rule 11)
- [ ] No `.env` or credential committed
