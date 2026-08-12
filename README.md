<div align="center">

# ai-agent-config

**A complete, runnable AI agent configuration layer for a Python/FastAPI service.**

Rules, a scoped reviewer subagent, slash commands, a quality gate with a pinned secret scan, and a
pipeline that strips the entire layer out of production branches.

Not advice about writing rules. The rules themselves, in the form that executes.

[Setup](SETUP.md) · [Rationale](docs/RATIONALE.md) · [Backend](https://github.com/adhibuchori/be-agent-config) · [Frontend](https://github.com/adhibuchori/fe-agent-config) · [Docs site](https://github.com/adhibuchori/docs-agent-config)

</div>

---

## Table of contents

- [The problem this solves](#the-problem-this-solves)
- [What ships](#what-ships)
- [Why this template and not be-agent-config](#why-this-template-and-not-be-agent-config)
- [Repository structure](#repository-structure)
- [Quick start](#quick-start)
- [What is deliberately excluded](#what-is-deliberately-excluded)
- [GitHub repository configuration](#github-repository-configuration)
- [Requirements](#requirements)
- [Adapting it to your stack](#adapting-it-to-your-stack)
- [Design decisions worth knowing before you edit](#design-decisions-worth-knowing-before-you-edit)
- [FAQ](#faq)
- [License](#license)

---

## The problem this solves

Most AI agent configuration is prose. You write `AGENTS.md`, list your conventions, and hope the
agent reads it. Some days it does.

Prose has no failure mode. When a rule is ignored, nothing reports it — the code just lands. So the
rule quietly becomes a suggestion, and the document becomes something people stop maintaining
because it stopped mattering.

A Python service wrapping an LLM or another vendor API has its own version of the backend problem:
a mistake here does not just render wrong, it can silently deliver a safety refusal as a broken
answer, or drift a read-only schema mirror out of sync with the repo that owns it. **This is why
the layer here leans on a machine-checked import-boundary contract and a numbered rulebook, not
just a document that advises.**

Every convention here is attached to something that exits non-zero — a CI step, an import-linter
contract, or an explicitly labelled `advisory` when no mechanism exists yet. Nothing sits in
between, unenforced and assumed.

---

## What ships

### Machine-checked layer boundaries

`routes → handlers → service → (repository)` isn't advisory here — three
`[[tool.importlinter.contracts]]` blocks in `pyproject.toml` fail CI on a violation. Run it
locally with `uv run lint-imports`. This is the one thing a Python template can do that most
backend templates in other languages can't do as cheaply.

### The provider pattern

Every external dependency (LLM, embedding, any vendor SDK) is a `Protocol` plus a default adapter,
never called directly from a service. `.claude/rules/backend/providers.md` is the deeper reference;
`AGENTS.md` §D is the enforced, numbered version — including the two rules that exist because of a
real failure mode: streaming by default, and checking the completion status before trusting
accumulated text as an answer.

### Rules — 2 tiers

```
.claude/rules/
├── common/     8 files   language-agnostic — transfers as is
└── backend/    3 files + 1 optional   FastAPI, performance, testing, + pipeline.example.md
```

### Reviewer subagent — one, not several

`ai-reviewer` checks layer boundaries, the error contract, provider indirection, and code quality
against the numbered rules in `AGENTS.md`. One agent with a real rulebook beats several with
overlapping mandates.

### Quality gate — request-serving baseline, pipeline extras documented separately

The baseline gate (`quality-gate.sh`) models a FastAPI request-serving service: install, format,
lint, type-check, import-boundaries, unit tests, security audit (`pip-audit`), a pinned gitleaks
secret scan, `.env`-not-committed, rule-drift check, workflow-mirror check, and a Docker build.
Two more steps — **Migration Drift Check** and **Docs Drift Check** — are documented as a
commented block in the same file, wired only if your repo owns a schema and runs Alembic. See
[Why this template and not be-agent-config](#why-this-template-and-not-be-agent-config).

### Slash commands — 9, maintained once

Sources live in `_workflow-source/` and are mirrored into `.claude/commands/` and
`.agent/workflows/` by `scripts/sync-workflows.sh`, with drift detection in `--check` mode.

### AI-config strip pipeline

Scripts that remove this entire layer from the production branch. `strip-paths.sh` is the single
source of truth for what gets removed; the other scripts source it rather than copying it.

---

## Why this template and not be-agent-config

Two Python repos in the fleet this template is drawn from differ in kind, not just detail: one is a
pure request-serving FastAPI service with no database write role, the other owns a schema and runs
Alembic migrations plus a worker/CLI pair. Rather than genericize both shapes into one document
neither fits well, this template commits to the **request-serving shape as its baseline** — the
same "one concrete stack, not `{{GENERIC}}`" philosophy `be-agent-config` uses — and ships the
pipeline shape as `.claude/rules/backend/pipeline.example.md`: rename it in if you own a schema,
delete it if you don't.

`be-agent-config` itself is TypeScript/Bun/Hono/Drizzle — a different language entirely. If your
service is Python, start here even if it looks more like a pipeline than a request-server; the
`.example.md` swap is a few minutes of work, and it's far less than porting the whole layer from a
different language's idioms.

---

## Repository structure

```
ai-agent-config/
├── CLAUDE.md                    Router — what to read for which task
├── AGENTS.md                    Guardrail — numbered rules + compliance status table
├── SSOT.md                      Contract — module structure, layer rules, environment
├── SETUP.md                     Ordered installation guide
├── LICENSE                      MIT License
├── .mcp.json                    MCP servers, neutral env-var names
│
├── .claude/
│   ├── settings.json            Hook wiring, permission allow/deny lists
│   ├── rules/                   common/ + backend/ (+ pipeline.example.md)
│   ├── agents/                  ai-reviewer.md + INDEX.md
│   ├── anti-patterns/           2 documented failures + INDEX.md
│   ├── hooks/                   safety-check, auto-format, auto-lint + lib.sh
│   ├── commands/                9 slash commands (generated)
│   └── *.example.md             3 optional shared docs — fill in or delete
│
├── .agent/workflows/            Command mirror for a second tool (generated)
├── _workflow-source/            9 command sources + INDEX.md — edit here
│
├── scripts/
│   └── sync-workflows.sh        Mirror commands, with --check drift mode
│
├── .github/
│   ├── workflows/               quality-gate · ci · ci-cd · strip-ai-on-pr
│   │                            deepseek-review · dependabot-lockfile
│   ├── scripts/                 quality-gate.sh · strip-paths.sh · strip-ai.sh
│   │                            verify-strip.sh · back-merge-prod.sh
│   │                            check-comment-blocks.sh · trigger-deploy.sh
│   ├── dependabot.yml           uv + github-actions + docker, weekly
│   ├── CODEOWNERS
│   └── PULL_REQUEST_TEMPLATE/   dev.md · promotion.md
│
├── pyproject.toml               ruff, mypy, pytest, coverage, import-linter — fill and go
│
└── docs/RATIONALE.md            Why the odd-looking parts are shaped that way
```

**No application source code.**

---

## Quick start

```bash
git clone https://github.com/adhibuchori/ai-agent-config.git
cd your-project

CFG=../ai-agent-config
cp -R "$CFG"/{.claude,.agent,_workflow-source,.github,scripts} .
cp "$CFG"/{CLAUDE.md,AGENTS.md,SSOT.md,.mcp.json,pyproject.toml,.gitignore} .

# Placeholders are named, never blank — this is your complete to-do list
grep -rn '<[a-zA-Z][a-zA-Z -]*>' CLAUDE.md AGENTS.md SSOT.md .mcp.json .claude/ pyproject.toml

chmod +x .claude/hooks/*.sh .github/scripts/*.sh
```

Then follow **[SETUP.md](SETUP.md)**.

> **Do this before you rely on any rule.** Fill in the Compliance Status table at the top of
> `AGENTS.md`, marking each section Enforced, Partial, or Not met. It is fifteen minutes and it is
> what keeps the whole document trustworthy — an agent that cites a rule, follows it to a file that
> does not exist, and wastes a session will discount every other rule in the file afterwards.
>
> **Then decide: request-serving or pipeline?** If this repo will own a database schema and run
> Alembic migrations, rename `.claude/rules/backend/pipeline.example.md` to `pipeline.md`, fill it
> in, and wire its two extra `quality-gate.sh` steps. If it reads a schema someone else owns —
> or has no database at all — delete that file and leave `AGENTS.md` Rule 13 as written.

---

## What is deliberately excluded

**No application source.** No `src/`, no `pyproject.toml` dependency list beyond the tooling
section, no `Dockerfile`, no Alembic scaffold. This is configuration, not a starter project.

**No secrets, and none required.** Every credential in `.mcp.json` is an environment-variable
reference.

**No `.agents/skills/` mirror.** Design skills have nothing to do in a repository with no browser
interface, so the directory is absent rather than empty.

`.agent/workflows/` **is** included — a command mirror for a second tool that reads from that path.
Deleting it is a legitimate choice, covered in `SETUP.md`. Decide knowingly rather than inheriting
it.

---

## GitHub repository configuration

Everything the workflows need. **Nothing here is required to clone and read the layer** — this is
for when you wire the gate into a real repository.

**Everything required to make this layer work is free.** The one thing that costs money on a
private repository (not a public one) is branch protection / rulesets — Actions minutes, secrets,
Dependabot, and `CODEOWNERS` auto-review-request are all free regardless of visibility on GitHub's
current plans; check GitHub's pricing page before concluding otherwise, since limits change.

**One secret needed:** `DEEPSEEK_CODE_REVIEW_TOKEN`, only if you keep `deepseek-review.yml`.
Everything else the gate needs is a dummy value set directly in `quality-gate.yml`'s `env:` block —
see [SETUP.md](SETUP.md) for the full walkthrough (branches, secrets, variables, and the optional
branch-protection ruleset).

---

## Requirements

Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and `gh` for the setup steps that create branches
and secrets. Nothing else is required to read the layer.

---

## Adapting it to your stack

This is written against a concrete stack — FastAPI, uv, ruff, mypy, SQLAlchemy async — deliberately.
A rule genericised into `{{FRAMEWORK}}` is unusable until filled in, and most people never fill it
in. If your service uses a different web framework or ORM, expect to rewrite `AGENTS.md` §B–§D and
`.claude/rules/backend/fastapi.md`'s content, not just find-and-replace names — the layer boundaries
and error contract are the part worth keeping; the specific framework calls are not.

---

## Design decisions worth knowing before you edit

- **Rule numbering is fixed once you fill it in.** `AGENTS.md`'s header says so: append new rules,
  never renumber existing ones — every citation elsewhere (hooks, `ai-reviewer.md`, this README's
  checklist) depends on the number staying put.
- **The provider `Protocol` pattern is not optional even for a one-vendor service.** The payoff is
  testability (fake the `Protocol` in unit tests, never mock the vendor SDK) as much as it is
  swappability.
- **`AI_SERVICE_TOKEN`-style auth, not end-user auth, is the default assumption.** If your service
  is consumed by browsers rather than other backend services, say so explicitly in `AGENTS.md` §F
  and `SSOT.md` — that's a real design decision, not a gap.

---

## FAQ

**Is this repo itself Python?** No — it ships configuration for a Python repo, but the config
files themselves (YAML, Markdown, shell, TOML) don't require Python to read or edit.

**Do I have to adopt all of it?** No. The hooks, the reviewer subagent, and the slash commands are
each independently deletable. The one piece worth keeping even if you strip everything else is the
`Protocol`-based provider pattern — it's what makes a vendor-dependent service testable at all.

**Should I use this or `be-agent-config`?** The test: is the service Python? If yes, this one —
even if your service looks more like `be-agent-config`'s TypeScript backends in shape (owns a
schema, serves an HTTP API to other services). Porting rule *content* across languages is more work
than swapping this template's own request-serving/pipeline archetype.

**What about a documentation-site repo?** Use [`docs-agent-config`](https://github.com/adhibuchori/docs-agent-config)
instead — it ships ready to clone rather than requiring you to delete most of this one.

**Will cloning this run any GitHub Actions?** No — workflows only trigger on `dev`/`prod` branches,
which don't exist on `main`.

---

## License

MIT License. See [LICENSE](LICENSE).
