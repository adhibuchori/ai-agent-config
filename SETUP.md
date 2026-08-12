# Setup

Ordered by dependency, not by importance. Each step is verifiable before the next one starts.

Budget about an hour. Steps 1–6 are the useful minimum; 7–8 are opt-in.

> **Read this first: the workflows arrive disarmed.**
>
> Every workflow in `.github/workflows/` triggers on `dev` or `prod` only. This repo ships with
> just `main`, so nothing runs, and no secrets are needed. They activate when you create those two
> branches in your own repo — deliberately, because a quality gate has nothing to guard until there
> is a branch to promote into.

---

## 1. Copy the layer in

Copy everything except this file, `README.md`, and `docs/RATIONALE.md`:

```bash
CFG=/path/to/ai-agent-config
cp -R "$CFG"/{.claude,.agent,_workflow-source,.github,scripts} .
cp "$CFG"/{CLAUDE.md,AGENTS.md,SSOT.md,.mcp.json,pyproject.toml,.gitignore} .
```

Then **read `.gitignore`.** `.claude/settings.local.json` and any `.env*` must be ignored before
your first commit, not after.

---

## 2. Fill in every placeholder

```bash
grep -rn '<[a-zA-Z][a-zA-Z -]*>' CLAUDE.md AGENTS.md SSOT.md .mcp.json .claude/ pyproject.toml
```

| File | What to replace |
| --- | --- |
| `CLAUDE.md` | Project name, one-line description, dev port |
| `AGENTS.md` | **The Compliance Status table — see §3, do this before anything else** |
| `SSOT.md` §What, §Stack | Scaffolding; replace wholesale |
| `SSOT.md` §Structure onward | Module structure, layer rules, env vars — edit in place |
| `pyproject.toml` | `name`, `description`, dependencies, import-linter container names |
| `.mcp.json` | Environment-variable names for tokens; delete servers you do not use |

Three optional shared docs ship as `.claude/*.example.md`. Fill one in, rename it to drop
`.example`, and uncomment its import line at the bottom of `CLAUDE.md`. **Delete the ones you do
not need.**

`DATABASE.example.md` deserves a real read rather than a skim. It is the only place recording
which production database operations are permitted, and on a service with any write access that
distinction is the difference between a debugging session and a data-loss incident.

**Decide your archetype now:** if this service will own a database schema and run Alembic
migrations, rename `.claude/rules/backend/pipeline.example.md` to `pipeline.md`, fill it in, and
wire its two extra `quality-gate.sh` steps (§6 below). If it reads a schema someone else owns, or
has no database at all, delete that file.

---

## 3. Fill in the Compliance Status table — before you use the rules

Most repos adopt rules **after** growing a real domain, so some sections will describe what the
code already does and others a target it has not reached.

Say which is which, in the table at the top of `AGENTS.md`. This is the highest-value fifteen
minutes in this setup, and the step most often skipped.

The failure it prevents is specific: an agent cites a rule, follows it to a file that does not
exist, wastes a session — and from then on treats every rule in the document as unreliable. One
inaccurate row costs you the whole file's authority.

Three conventions that make the table work:

- **Three states, not two.** "Partial" carries most of the value.
- **Say what to do in the meantime.** A section marked Not met should name the shape to follow
  until the migration lands, or each contributor invents a third one.
- **Record deliberate oddities.** A read-only service with no Alembic migrations is the kind of
  thing someone "fixes" without knowing it was intentional — write down why.

---

## 4. Agent tooling — MCP servers, wrappers, plugins

This is what the agent actually reaches for on every task. Hooks stop bad edits; **this decides how
well it works in the first place**, so it is worth ten minutes even though nothing breaks if you
skip it.

### The servers in `.mcp.json`

**Most projects should delete most of them.** Every connected server spends context on its tool
definitions before you have asked anything, so an unused server is a permanent tax.

| Server | What it gives the agent | Needs | Keep it if |
| :-- | :-- | :-- | :-- |
| `serena` | Semantic code search and edit over a language server — find a symbol, its references, its implementations, rename it safely | `uvx` ([Astral uv](https://github.com/astral-sh/uv)) — you already need uv for this repo anyway. No token | **Almost always** |
| `context7` | Current library documentation, fetched live | `npx`. No token | You use libraries that moved recently — vendor SDKs especially |
| `github` | Pull requests, issues, reviews, and branches from inside a session | `GITHUB_PERSONAL_ACCESS_TOKEN` | You want the agent to open and read pull requests |
| `db-dev` · `db-prod` | Query and inspect a database — schema, health, index advice, query plans | `DB_DEV_URI` / `DB_PROD_URI`, plus a tunnel if the port is not public | You have a database, even read-only. Read `DATABASE.example.md` first |
| `dokploy-mcp` | Deployment platform control — applications, deploys, logs, backups | `DOKPLOY_URL`, `DOKPLOY_API_KEY` | You deploy with Dokploy. Otherwise **delete** |
| `cloudflare` | DNS, Workers, and account resources | OAuth in an interactive session | You use Cloudflare. Otherwise **delete** |
| `hostinger-hosting` · `-domains` · `-dns` · `-vps` | VPS, domain, and DNS management | `HOSTINGER_API_TOKEN` | You host with Hostinger. Otherwise **delete all four** |

Deleting a server is just removing its object from `.mcp.json`. Nothing else references them.

> **The four infrastructure servers are vendor-specific and are the first things to cut.** Replace
> them with your own provider's server, or run with none — the gate, the hooks, and the rules do
> not care.

### Serena — install it, or delete the rules that assume it

`CLAUDE.md` and `SERENA-WORKSPACE.example.md` (if you fill it in) assume Serena is installed and
used for code files. If it is not installed, that instruction is telling your agent not to read
your code efficiently — it degrades to built-in tools rather than deadlocking, but you get a
confused agent until you fix it.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # gives you uvx; also what this repo needs anyway
```

**Or** delete the Serena-specific instructions from `CLAUDE.md` and the `serena` entry from
`.mcp.json`, together.

### If you work across several repositories at once

`.claude/SERENA-WORKSPACE.example.md` covers running one Serena project spanning several repos, so
symbol search reaches all of them. Genuinely useful on a multi-repo product — e.g. this repo plus a
sibling that owns the database schema — and pure overhead on a single repo.

### AI code review on pull requests — DeepSeek

`.github/workflows/deepseek-review.yml` posts an AI review comment on pull requests into `dev`,
using [`hustcer/deepseek-review`](https://github.com/hustcer/deepseek-review) — which accepts any
OpenAI-compatible endpoint, so the provider is your choice despite the name.

Add a `DEEPSEEK_CODE_REVIEW_TOKEN` secret and it runs. Details in
**README § GitHub repository configuration**.

Fill in the `sys-prompt`'s bracketed sections before relying on it — it needs one or two sentences
naming what this repo actually does (reads a schema someone else owns? owns it? no database at
all?) so it does not invent findings against an architecture you don't have.

**Never add `actions/checkout`.** The workflow runs under `pull_request_target`, which puts your
repository secrets in scope so it can comment on fork pull requests. Checking out and executing the
pull request's code under that trigger hands your secrets to anyone who opens one. The action reads
the diff over the API instead.

**`dev` only, and no `synchronize`.** A `dev → prod` diff re-adds the entire AI config the strip
pipeline removed and can exceed the provider's diff limit. And without `synchronize`, a push does
not stack another review — re-run on demand by commenting `/ask-deepseek`.

---

## 5. Wire the hooks

```bash
chmod +x .claude/hooks/*.sh .github/scripts/*.sh
```

**The distinction that matters:** `PreToolUse` hooks can **block** — `exit 1` stops the tool call
before it happens. `PostToolUse` hooks are advisory; a non-zero exit is reported and ignored. So
anything that must not happen belongs in `PreToolUse`.

`safety-check.sh` (PreToolUse `Bash`) blocks `rm -rf` on protected paths, `git push` straight to
`dev`/`prod`, and shell redirects into `.env`. `auto-format.sh`/`auto-lint.sh` (PostToolUse) run
`ruff format`/`ruff check` on every Python file written — never blocking, CI's gate is the blocking
equivalent.

**Two Python-specific traps these hooks already work around** — see
`.claude/anti-patterns/hooks-silent-noop-on-macos.md` and `pythonpath-breaks-mypy-plugin.md` before
you "fix" `lib.sh`'s `resolve_tool`/`run_capped` helpers; they exist because the obvious version
silently does nothing on macOS and because an inherited `PYTHONPATH` breaks mypy's pydantic plugin
in a way that looks like a broken venv.

**If your archetype is the pipeline shape** (§2 above), add a schema-file guard now — see
`pipeline.example.md`'s "Hook: guard the schema file" section — and test it by asking the agent to
edit `db/models.py` directly; confirm it warns (or blocks, on the write side).

---

## 6. Make the gate runnable

```bash
uv sync
uv run pytest tests -q --cov   # 0 tests is fine for now; the command must succeed
```

`.github/scripts/quality-gate.sh` runs `uv sync --frozen`, so `uv.lock` must exist and be
committed. If you have not run `uv lock` yet, do that before your first PR.

Run the whole gate locally before opening any pull request:

```bash
bash .github/scripts/quality-gate.sh origin/dev
```

If your archetype is the pipeline shape, uncomment the two extra steps described in
`pipeline.example.md` — Migration Drift Check and Docs Drift Check — into `quality-gate.sh` after
"Production Build", gated the same way "Run Integration Tests" already is.

### On dependency audits

If `pip-audit` reports a transitive dependency, **check where the advisory comes from before
accepting an ignore flag.** They frequently all arrive through a single parent dependency, in which
case two things genuinely fix it:

1. Upgrade the parent. If that is a breaking major, do it as its own change — not folded into a CI
   change.
2. Pin the transitive dependency to a patched release directly in `dependencies`/`dev`.

An ignore flag left behind after the problem is fixed is not untidiness. It will hide the next
report for a completely different vulnerability.

---

## 7. Slash commands and their mirrors — optional

```bash
bash scripts/sync-workflows.sh           # write the mirrors
bash scripts/sync-workflows.sh --check   # verify without writing — this is the CI mode
```

`--check` is the mode that catches drift, and the reason is worth internalising: a write-mode run
**overwrites staleness before it can observe it**. Wire `--check` into your gate; wire the write
mode into nothing.

`.agent/workflows/` exists for a second tool that reads commands from that path. Keeping it is
cheap and automatic; deleting it is cleaner but must be restored if the habit changes. Neither is
wrong — what matters is knowing which applies, because until then nobody can judge whether running
a drift check over it is worth anything.

---

## 8. The AI-config strip pipeline — last, and only if you want it

**This is the only part that deletes files. Everything else should be working before you touch it.**

| Script | Role |
| --- | --- |
| `strip-paths.sh` | **The single source of truth** for what gets removed. The other scripts source it |
| `strip-ai.sh` | Removes those paths on the production branch |
| `verify-strip.sh` | Asserts they are gone from `prod` **and still present on `dev`** |
| `back-merge-prod.sh` | Merges `prod` back into `dev` so the branches do not diverge |

Three things that are not obvious, each of which has already cost someone a debugging session:

**One list, sourced — never copied.** When the path list was duplicated across scripts, updating
one and not the others made the strip half-land: production kept part of the config and nothing
reported an error.

**Verify both directions.** Checking only that `prod` lost the files misses the failure where `dev`
lost them too. Only the second assertion catches that.

**Merge, never rebase, on the way back.** Rebasing rewrites the strip commit and the branches
diverge permanently.

Adopt it in this order:

1. Run `strip-ai.sh` on a throwaway branch and inspect what disappeared.
2. Run `verify-strip.sh` and confirm it fails when you deliberately skip a path.
3. Only then wire it into `strip-ai-on-pr.yml`.

---

## Verify the whole thing

```bash
grep -rn '<[a-zA-Z][a-zA-Z -]*>' CLAUDE.md AGENTS.md SSOT.md   # nothing unfilled
bash .github/scripts/check-comment-blocks.sh                   # exits 0
bash scripts/sync-workflows.sh --check                         # mirrors in sync
bash .github/scripts/quality-gate.sh origin/dev                # the real gate
```

Then the test no script performs: open a session and ask the agent to make a change you know
violates a rule — e.g. call a vendor SDK directly from a service instead of through a `Protocol`.
If nothing objects, the rule is prose rather than a guardrail — check whether `ai-reviewer.md`
actually gets invoked in your workflow, and treat that as the general remedy whenever a rule is not
holding.
