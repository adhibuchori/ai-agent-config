---
description: Produces an implementation plan before any AI-service code is written — scope, tasks, contracts, risks and open questions. Reads code and docs only; writes nothing and stops for confirmation.
---

<!-- Command: /plan [feature] -->
<!-- Source: _workflow-source/plan.md -->

# /plan — Implementation Plan

## Step 1: Research Before Designing

Read the existing modules under `src/app/modules/` and providers under `src/app/providers/`, then
the FastAPI, Pydantic and vendor SDK docs through Context7. For a provider integration, prefer
extending the existing `Protocol` over adding a parallel abstraction.

## Step 2: Read The Relevant Sections

`SSOT.md` for architecture and env facts, `AGENTS.md` §B for module boundaries, §C for the error
contract, §D for provider protocols and, where Rule 13 applies, the schema this repo reads but does
not own.

## Step 3: Output

```markdown
# Plan: {title}

## SCOPE
- Modules affected:
- Provider protocols touched:
- Env vars added or changed (and their `.env.<target>.example` lines):

## TASKS
- [ ] [module] [verb] [file] — what and why, with the test that mirrors it

## CONTRACTS
- Schema or model changes, and who owns them
- New DomainError types, raised where, and their problem+json mapping
- Values another place must spell the same way, and their one home

## RISKS
- Only risks that could actually block or break something

## CONFIRMATION
- Questions that need an answer before starting
```

Scopes in this repo: `<module>`, `providers`, `routes`, `config` — replace with your own.

Do not start implementing until the plan is confirmed.
