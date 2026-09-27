# Setup

Ordered by dependency, not by importance: each step can be verified before the next one starts.
Budget about an hour. Steps 1 to 6 are the useful minimum; 7 and 8 are optional.

> **The workflows arrive disarmed.** Nothing in `.github/workflows/` runs on a push or on a
> schedule; every workflow starts from a pull request. The gate, deploy, strip and review workflows
> wait for pull requests into `dev` or `prod`, so they start only once you create those branches.
> Dependency review and CodeQL run on any pull request and skip themselves on a private repository
> until `CODE_SECURITY` is set (§ 6); Workflows Lint runs when a pull request changes `.github/`.

## Before you start: tools

| Tool                                              | Needed for                                                                                                                                                                                       |
| :------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python 3.12+ and [uv](https://docs.astral.sh/uv/) | the service, every `uv run` command, and `uvx` for the Serena and database MCP servers                                                                                                           |
| python3 3.8+                                      | the hooks' command analyzer, `db-guard.sh`, `unlock.sh` and the env helpers                                                                                                                      |
| bash 3.2+ and git                                 | the hooks and scripts; macOS `/bin/bash` is enough                                                                                                                                               |
| macOS, Linux or WSL2                              | the Bash sandbox `.claude/settings.json` turns on; Linux and WSL2 also need `bubblewrap` and `socat`, and WSL1 or native Windows has none (Claude Code then warns and runs commands unsandboxed) |
| Node.js 20+                                       | `folder-shape.mjs`, `coverage-policy.mjs`, and `npx` for Context7                                                                                                                                |
| gitleaks                                          | the commit hook's secret scan                                                                                                                                                                    |
| SkillSpector                                      | the skill scan; `bash scripts/check/skills.sh` prints the pinned install command                                                                                                                 |
| Docker                                            | the gate's production build                                                                                                                                                                      |
| `gh`                                              | `scripts/ops/pr-ready.sh` and the commands that open, merge and promote PRs                                                                                                                      |
| jq                                                | optional: faster hook payload reads, and a fallback reader without python3                                                                                                                       |

Install uv from its [installation guide](https://docs.astral.sh/uv/getting-started/installation/)
rather than by piping a script into a shell.

---

## 1. Copy the layer in

Copy everything except `README.md`, `README.id.md`, this file, `docs/RATIONALE.md` and
`docs/assets/`:

```bash
CFG=/path/to/ai-agent-config
cp -R "$CFG"/{.claude,.agent,_workflow-source,.github,scripts} .
cp "$CFG"/{CLAUDE.md,AGENTS.md,SSOT.md,.mcp.json,pyproject.toml,.gitignore} .
cp "$CFG"/{.pre-commit-config.yaml,.gitleaks.toml,.dockerignore,.skillspector-baseline.yaml} .
mkdir -p docs && cp "$CFG"/docs/unlock.md docs/
chmod +x .claude/hooks/*.sh .github/scripts/*.sh scripts/*/*.sh
```

**In a project that already exists,** merge rather than overwrite:

- `pyproject.toml`: keep your `[project]` table and dependencies, and take the `[tool.*]` sections
  and the dev dependency group from the template.
- `.gitignore`: add the template's lines to yours. `.claude/settings.local.json`, `.claude/state/`
  and every real `.env*` must be ignored before your first commit, not after.
- `.github/`: `cp -R` replaces a workflow or script of yours that has the same file name. If you
  already have some, copy the template's into a scratch folder first and merge by hand.

---

## 2. Fill in every placeholder

Placeholders are named, never blank. This lists every one in the files to fill first:

```bash
grep -rn -e '<[A-Za-z]' -e 'your-github-handle' \
  CLAUDE.md AGENTS.md SSOT.md pyproject.toml .claude/agents .github
```

| File                                    | What to replace                                                                                                                                                 |
| :-------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CLAUDE.md`                             | `<Project Name>`, the one-or-two-sentence snapshot, `<port>`                                                                                                    |
| `AGENTS.md`                             | `<repo-name>`, **the Compliance Status table (§ 3, do this first)**, the follow-up list, the vendor and service names in the rules                              |
| `SSOT.md` § What, § Stack               | scaffolding: replace it whole                                                                                                                                   |
| `SSOT.md` § Structure onward            | module structure, layer rules, env vars: edit in place                                                                                                          |
| `pyproject.toml`                        | `name`, `description`, dependencies, and `app.modules.<example>` in both import contracts; add `readme` once that file exists                                   |
| `.claude/agents/ai-reviewer.md`         | `<Project Name>`                                                                                                                                                |
| `.github/CODEOWNERS`                    | `@your-github-handle`                                                                                                                                           |
| `.github/workflows/quality-gate.yml`    | `<user>`, `<password>` and `<database-name>` in `DATABASE_URL`, and the `<PROVIDER>_API_KEY` and `<SERVICE>_SERVICE_TOKEN` names your settings module validates |
| `.github/scripts/quality-gate.sh`       | `<repo-name>` in the Production Build step                                                                                                                      |
| `.github/workflows/deepseek-review.yml` | the two bracketed sentences in `sys-prompt`, if you keep the workflow (§ 4)                                                                                     |
| `.mcp.json`                             | nothing: delete the servers you do not use (§ 4)                                                                                                                |

Some matches are shapes, not blanks, and stay as written: argument and path shapes in examples
and command syntax, such as `<file>`, `<your files>`, `<KEY>`, `<name>`, `<module>` and `<kind>`.

**Fill these when you adopt the part they belong to:**

- **On-demand references.** Five ship as `.claude/*.example.md`. Copy one to the path its row
  names in `CLAUDE.md` § On-demand References and fill it in; nothing imports it. Delete the ones
  you do not need, and their rows. `DATABASE.example.md` deserves a real read: it is the one place
  that records which production database operations are allowed.
- **The deploy target.** Before the first `/promote`, fill "This repo's deploy target" and the
  deploy adapter at the top of `_workflow-source/promote.md` and `_workflow-source/promote-deploy.md`,
  then run `bash scripts/sync/workflows.sh` to regenerate the command mirrors.
- **The pipeline shape**, only if this service owns its schema (§ 3).

---

## 3. Fill in the Compliance Status table, and pick a shape

Most repos adopt rules after growing a real domain, so some sections will describe what the code
already does and others a target it has not reached. Say which is which, in the table at the top of
`AGENTS.md`. It takes fifteen minutes and is the step most often skipped.

The failure it prevents is specific: an agent cites a rule, follows it to a file that does not
exist, wastes a session, and from then on treats every rule in the document as unreliable. One
inaccurate row costs the whole file its authority.

- **Three states, not two.** "Partial" carries most of the value.
- **Say what to do in the meantime.** A section marked Not met should name the shape to follow
  until the migration lands, or each contributor invents a third one.
- **Record deliberate oddities.** A read-only service with no Alembic migrations is the kind of
  thing someone "fixes" without knowing it was intentional: write down why.

**Pick a shape now.** If this service will own a database schema and run Alembic migrations,
follow `.claude/examples/pipeline/README.md`: copy its rules into `.claude/rules/`, rewrite
`AGENTS.md` Rule 13, and wire its two extra gate steps (§ 6). If it reads a schema another repo
owns, or has no database, delete `.claude/examples/pipeline/` and keep Rule 13 as written.

---

## 4. Agent tooling: MCP servers, wrappers, plugins

This is what the agent reaches for on every task. Hooks stop bad actions; **this decides how well
it works in the first place**, so it is worth ten minutes even though nothing breaks if you skip
it.

### Every tool by name, and where it is covered

| Tool                               | What it is                                           | Ships here?                                                     | Covered in                                                     |
| :--------------------------------- | :--------------------------------------------------- | :-------------------------------------------------------------- | :------------------------------------------------------------- |
| **Serena**                         | Semantic code search and edit over a language server | `.mcp.json`                                                     | [below](#serena-install-it-or-delete-what-assumes-it)          |
| **Context7**                       | Live library documentation lookup                    | `.mcp.json`                                                     | [the servers](#the-servers-in-mcpjson)                         |
| **GitHub MCP**                     | Pull requests, issues and reviews inside a session   | `.mcp.json`                                                     | [the servers](#the-servers-in-mcpjson)                         |
| **Postgres MCP**                   | Schema, health and query plans (`db-dev`, `db-prod`) | `.mcp.json`                                                     | [the servers](#the-servers-in-mcpjson) · `DATABASE.example.md` |
| **Cloudflare**                     | DNS, Workers and account resources                   | as an on-demand template, `.claude/mcp/cloudflare.example.json` | [servers you load on demand](#servers-you-load-on-demand)      |
| **Deploy platform · VPS provider** | Deployment and server control                        | as on-demand templates, `.claude/mcp/*.example.json`            | [servers you load on demand](#servers-you-load-on-demand)      |
| **Command wrapper**                | An output filter, sandbox or recorder                | **No**: machine-local                                           | [Command wrappers](#command-wrappers)                          |
| **Plugins**                        | Claude Code plugins                                  | **No**: machine-local                                           | [Plugins](#plugins)                                            |
| **DeepSeek Code Review**           | An AI review comment on pull requests                | `.github/workflows/`                                            | [below](#ai-code-review-on-pull-requests)                      |

react-doctor and impeccable are frontend tools and are deliberately absent: a service with no
browser interface has nothing for either to check.

### The servers in `.mcp.json`

**Most projects should delete most of them.** Every connected server spends context on its tool
definitions before you have asked anything, so an unused server is a permanent tax.

| Server               | What it gives the agent                                                                                                    | Needs                                                                 | Keep it if                                                                                                       |
| :------------------- | :------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------- |
| `serena`             | Find a symbol, its references and implementations, rename it safely                                                        | `uvx`, from uv. No token                                              | **almost always**                                                                                                |
| `context7`           | Current library documentation, fetched live                                                                                | `npx`. No token                                                       | you use libraries that moved recently, vendor SDKs especially                                                    |
| `github`             | Pull requests, issues, reviews and branches from inside a session                                                          | `GITHUB_PERSONAL_ACCESS_TOKEN`, sent to GitHub's hosted MCP endpoint  | you want the agent to open and read pull requests                                                                |
| `db-dev` · `db-prod` | Query and inspect a database: schema, health, index advice, query plans. Both start read-only (`--access-mode=restricted`) | `DB_DEV_URI` / `DB_PROD_URI`, plus a tunnel if the port is not public | you have a database. Read `DATABASE.example.md` first, and `docs/unlock.md` before giving `db-prod` write access |

Deleting a server is removing its object from `.mcp.json`. `.claude/settings.json` still names the
`db-prod` and `github` tools in its guards; with the server gone that wiring never fires, so it can
stay.

Every server started with `uvx` or `npx` is pinned to one release, so a fresh clone runs the code
you reviewed: Serena to the commit its `v1.7.0` tag names (a tag can move; a commit cannot), the
others to a full version (`@4.1.1`, `==0.3.0`). `scripts/check/ai-config.sh` fails on a pin that
can move: a bare name, `@latest`, a range, a major-only `@1` or a major.minor `@1.2`, and
`scripts/check/ai-config-probes.sh` proves that rule both ways. `github` is a hosted endpoint with
nothing to pin. Tool permissions live in `.claude/settings.json`, never in
`.mcp.json`.

### Servers you load on demand

A server you reach for once a month should not cost context in every session. Deploy-platform,
VPS-provider and Cloudflare servers ship only as templates in `.claude/mcp/`:

1. Copy `.claude/mcp/deploy-platform.example.json` to `.claude/mcp/deploy-platform.json`.
2. Put your provider's package in it, pinned to the exact version you verified, and rename the env
   keys to the ones that package reads. Secrets stay `${VARIABLE}` references to your shell.
3. Load it for one session: `claude --mcp-config .claude/mcp/deploy-platform.json`.

`cloudflare.example.json` is Cloudflare's hosted server, with nothing to pin: copy it to
`.claude/mcp/cloudflare.json`, set `CLOUDFLARE_API_TOKEN` in your shell, and load it the same way.

`ai-config.sh` skips the `*.example.json` templates and checks every copy, so a copy that still
says `<pinned-version>` fails until it names a real version. `.claude/OPERATIONS.example.md` §
MCP servers covers redaction, tool groups and multi-server packages. Move a server into
`.mcp.json` only when you use it in most sessions.

### Serena: install it, or delete what assumes it

`CLAUDE.md` § Agent Tooling, and `SERENA-WORKSPACE.example.md` if you fill it in, assume Serena is
installed and used for code files. Without it, the agent falls back to its built-in tools but keeps
reading an instruction it cannot follow. Install uv (which provides `uvx`), **or** delete the
Serena line from `CLAUDE.md` and the `serena` entry from `.mcp.json` together.

`.claude/SERENA-WORKSPACE.example.md` covers one Serena project spanning several repos, so symbol
search reaches all of them: useful on a multi-repo product, such as this service plus the repo
that owns its schema, and pure overhead on a single repo.

### Command wrappers

If you route shell commands through a wrapper (an output filter, a sandbox, an audit
recorder), declare it in `CLAUDE.md` § Agent Tooling **as a hard rule**, prefix every command in
that file with it, and list it under `commandWrappers` in `.claude/agent-config.json` so the safety
hook judges the command it wraps.

None ships with this layer, on purpose: a wrapper is machine-local tooling a fresh clone will not
have, and a rule pointing at a missing binary fails every command. It has to be a hard rule rather
than a note, because a wrapper mentioned in passing gets dropped the moment a task gets busy, and
then half the commands are wrapped and half are not.

> **One Python-specific caveat.** Every command here is a `uv run …` invocation, so a wrapper
> nests: `<wrapper> uv run pytest …`. Confirm your wrapper passes the whole command through rather
> than rewriting only the first word: one that drops `uv`'s arguments fails in a way that looks
> like a test failure, not a tooling failure.

### Plugins

`.claude/settings.json` enables **no plugins**, for the same reason as the wrapper: a plugin
declared but not installed is a startup error for everyone who clones the repo. If the whole team
uses one, it goes in the same file:

```jsonc
{
  "enabledPlugins": { "<plugin>@<source>": true },
  "env": { "<PLUGIN_SETTING>": "<value>" }
}
```

Keep a personal choice in `.claude/settings.local.json` instead, which `.gitignore` excludes. To
get this whole layer as plugins rather than files, see README § Prefer plugins?.

### AI code review on pull requests

`.github/workflows/deepseek-review.yml` posts an AI review comment on pull requests into `dev`,
using [`hustcer/deepseek-review`](https://github.com/hustcer/deepseek-review), which accepts any
OpenAI-compatible endpoint. Add a `DEEPSEEK_CODE_REVIEW_TOKEN` secret and it runs. Fill in the two
bracketed sentences of its `sys-prompt` first, so it does not invent findings against an
architecture you do not have.

**Two triggers, and where the secret is available.** It runs on `pull_request` and on an
`/ask-deepseek` comment (`issue_comment`), never on `pull_request_target`:

| Event                                           | Workflow file from              | `DEEPSEEK_CODE_REVIEW_TOKEN` | This workflow                                                           |
| :---------------------------------------------- | :------------------------------ | :--------------------------- | :---------------------------------------------------------------------- |
| `pull_request` from a branch of this repository | the pull request's merge commit | available                    | reviews                                                                 |
| `pull_request` from a fork                      | the pull request's merge commit | withheld                     | skipped by the job's `if:`                                              |
| `issue_comment` on a pull request               | the default branch              | available                    | reviews, only for `/ask-deepseek` from an owner, member or collaborator |

No step checks out or runs the pull request's code: the action fetches the diff over the API. That
keeps the comment path safe even on a fork's pull request, where it runs with the secret. Never add
`actions/checkout` to this job.

**`dev` only, and no `synchronize`.** A `dev → prod` diff re-adds the whole AI layer the strip
removed and can exceed the provider's diff limit. Without `synchronize`, a push does not stack
another review: comment `/ask-deepseek` to re-run it.

---

## 5. Prove the hooks

`.claude/settings.json` already wires them. Prove they work on your machine:

```bash
bash scripts/check/hook-probes.sh   # about eight minutes; on macOS, /bin/bash proves bash 3.2
```

It ends with `hook probes: <n> passed, 0 failed`, having fed every rule a command it must stop and
one it must let through.

### The hook contract

Five facts decide whether a hook does anything at all:

1. **Input is JSON on stdin.** Claude Code sets no `CLAUDE_TOOL_INPUT_*` variable, so a hook that
   reads one does nothing (`.claude/anti-patterns/hooks-read-env-vars-never-set.md`).
2. **Only exit 2 stops a `PreToolUse` call**, and stderr is the reason Claude reads. A crash,
   `exit 1` or a timeout lets the call through, so every guard here refuses what it cannot parse,
   and `safety-check.sh` also refuses a command whose effect it cannot resolve.
3. **`PostToolUse` cannot undo anything.** Its feedback reaches Claude only through
   `hookSpecificOutput.additionalContext`.
4. **Hooks start in the session's folder**, so `settings.json` runs each as
   `bash "$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.sh"` with a `timeout`.
5. **`SessionStart` and `UserPromptSubmit` hooks end in `|| true`**: an exit 2 there would erase
   the user's prompt.

| Hook                 | Runs on                                | What it does                                                                                                                                                                                                                                                                                                                                                               |
| :------------------- | :------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `safety-check.sh`    | PreToolUse `Bash`                      | Refuses recursive deletes of protected paths, commands that wipe uncommitted work, skipping the commit gate, pushes to or deletion of a protected branch, any shell read or write of a real `.env*` file, `alembic downgrade` where `alembic.ini` exists, the agent running the unlock, git settings that change what git runs or loads, and any command it cannot resolve |
| `db-guard.sh`        | PreToolUse `mcp__db-prod__execute_sql` | Lets one read-only statement through; anything else waits until you unlock `db`                                                                                                                                                                                                                                                                                            |
| `mcp-guard.sh`       | PreToolUse GitHub MCP writes           | Refuses writes onto a protected branch                                                                                                                                                                                                                                                                                                                                     |
| `migration-guard.sh` | PreToolUse write tools                 | Refuses hand edits to generated Alembic revisions; inert until the repo has a `migrationsDirs` folder                                                                                                                                                                                                                                                                      |
| `post-edit.sh`       | PostToolUse write tools                | `ruff format`, then `ruff check`, on the file just written; never blocks                                                                                                                                                                                                                                                                                                   |
| `post-commit.sh`     | PostToolUse `Bash`                     | Shows what a commit carried and warns about paths its pathspec did not name                                                                                                                                                                                                                                                                                                |
| `prompt-intent.sh`   | UserPromptSubmit                       | Points `/debug` at `/rca`, and prunes the state of sessions idle for two days                                                                                                                                                                                                                                                                                              |
| `session-start.sh`   | SessionStart                           | Makes Claude's zsh behave like bash on unmatched globs, `=word` and word splitting                                                                                                                                                                                                                                                                                         |

`.claude/hooks/README.md` lists every rule, each hook's fail mode and the configuration keys. To
change protected branches, protected paths or migration folders, copy
`.claude/agent-config.example.json` to `.claude/agent-config.json` and keep only the keys you
change.

**Several repos in one folder?** Export `AGENT_WORKSPACE_ROOT=<that folder>` in the shell you start
Claude Code from. The hooks then protect the sibling repos there like this one, and a session opened
at that folder follows each file's own repo. Unset, the hooks guard this repo alone
(`.claude/hooks/README.md` § Configuration).

**Secrets and production writes are locked, and only you unlock them.** Claude lists a `.env*`
file with `bash scripts/env/show.sh <file>` (secrets masked) and changes a value with
`scripts/env/set.sh` only after you run `! ./scripts/ops/unlock.sh env`; the lock closes again by
itself. [`docs/unlock.md`](docs/unlock.md) explains both targets (`env`, `db`) and what the lock
does not stop.

**The guards cannot be rewritten from the shell.** Claude's shell may read the hooks,
`scripts/check/hook-probes.*`, `scripts/ops/unlock.sh`, `scripts/env/` and the settings that turn
the guards on, and run the hooks and probes, but not change, move or delete any of them by a route
the analyzer can read. A change goes through the Edit tool, which asks you first, or your own `!`.

**Wrappers and package runners are unwrapped.** `env`, `sudo`, `timeout`, `xargs` and the other
common wrappers, and `npx`, `bunx`, `pnpx` and `npm`/`pnpm`/`yarn`/`bun` `exec`, `dlx` and `x`, are
peeled: the command inside is judged, and a `-c` string or the words of `bun exec` and `yarn exec`
are judged as a script. A wrapper of your own goes under `commandWrappers` in
`.claude/agent-config.json`.

**What the guard cannot resolve, it refuses.** When `safety-check.sh` cannot tell what a command
touches (computed or decoded code, a `$( )` used as the command or as a file name, a path built
through `IFS` or an array, a package runner's command or script built from `$( )` or an unknown
variable, inline code that opens or changes a file or runs a command, and the rest of the list in
[README § What gets blocked](README.md#what-gets-blocked)), it exits 2 with the reason and the hint
to run the command yourself with `!`. So is a git setting that changes what git runs or loads (an
alias, an include, `core.sshCommand`, a credential helper, a proxy, `url.*.insteadOf`), whatever
its value, and so is every command when a guard crashes, runs past its time or cannot read its
input. `!` runs the command as you, with your own access, outside the hooks and (in an ordinary
session) outside the sandbox. That also stops a few ordinary commands, such as `head $(ls -t …)`:
type them with `!` when you mean them. Without python3 only a few plain-text rules stand in
(`.claude/hooks/README.md` § Fail modes), so install it.

**The Bash sandbox is on by default.** `.claude/settings.json` turns on
[Claude Code's sandbox](https://code.claude.com/docs/en/sandboxing) (`sandbox.enabled: true`),
which the operating system enforces for every sandboxed command: it denies reading `.env*` files
(templates excepted) and the `.env` backups, and writing under `.claude/state/unlock/` or
`.claude/hooks/` or to `scripts/ops/unlock.sh`. Only `scripts/env/show.sh` and `scripts/env/set.sh`
run outside it. Its limits, and how to turn it off:

- **Platforms.** macOS needs nothing; Linux and WSL2 need `bubblewrap` and `socat`. WSL1 and native
  Windows are not supported. Where the sandbox cannot start, Claude Code warns and runs commands
  without it unless `sandbox.failIfUnavailable` is `true`; the hooks apply either way.
- **The retry outside it.** When the app itself must read `.env` (a server, a test run that loads
  it), the command fails inside the sandbox and Claude Code asks you before it retries it outside.
  Set `sandbox.allowUnsandboxedCommands` to `false` to forbid every such retry.
- **Your `!` commands** run outside it, except in a background session with
  `allowUnsandboxedCommands: false` and on Linux with `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` set; there,
  run `unlock` in your own terminal.
- **Turning it off.** Set `"sandbox": {"enabled": false}` in `.claude/settings.json`, or in your own
  `.claude/settings.local.json`. The hooks keep running.

**Before you "fix" `lib.sh`.** `resolve_tool` and `run_capped` exist because the obvious versions
silently do nothing on macOS (`.claude/anti-patterns/hooks-silent-noop-on-macos.md`). Separately,
mypy and pytest run as `env -u PYTHONPATH uv run …` everywhere, because an inherited `PYTHONPATH`
breaks mypy's pydantic plugin in a way that looks like a broken venv
(`.claude/anti-patterns/pythonpath-breaks-mypy-plugin.md`).

**In the pipeline shape,** `migration-guard.sh` and the `alembic downgrade` refusal switch on by
themselves once `alembic.ini` and a migrations folder exist; `.claude/examples/pipeline/README.md`
§ Hooks shows how to prove it.

---

## 6. Make the gate runnable

```bash
uv lock && uv sync
git add .claude .agent _workflow-source .github scripts docs/unlock.md CLAUDE.md AGENTS.md \
  SSOT.md .mcp.json pyproject.toml uv.lock .gitignore .pre-commit-config.yaml .gitleaks.toml \
  .dockerignore .skillspector-baseline.yaml
git commit -m "chore: add the claude code layer"
uv run pre-commit install        # the commit hook: .pre-commit-config.yaml
bash scripts/check/gates.sh      # scripts/check/gates.list by hand; four fail until the table below holds
```

**Commit the layer before you install the hook.** The layer's own `.py` files and
`pyproject.toml` start the code gates, and a project with no `src/` or `tests/` yet fails four of
them, so a hook installed first refuses the commit that adds the layer. The pathspec stages only
what § 1 copied, not other work in progress. `.github/scripts/quality-gate.sh` runs
`uv sync --frozen`, so `uv.lock` goes in the same commit.

### What the code gates need from `src/` and `tests/`

The layer ships no application code. Until your first module lands, these four gates fail, each for
its own reason:

| Gate                                             | Passes once                                                                                                                                     | Because                                                                                                                                    |
| :----------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `uv run lint-imports`                            | `app`, `app/core`, `app/providers` and `app/modules` under `src/` are packages, and both contracts name your module for `app.modules.<example>` | the forbidden contract names `app.core` and `app.providers`, and import-linter fails on a module that does not exist                       |
| `uv run vulture`                                 | `src/` exists, and each route is registered with `router.add_api_route`, as in `AGENTS.md` § B                                                  | vulture fails on a missing path, and reports a function that only a decorator such as `@router.get` registers as unused                    |
| `uv run deptry src`                              | each package in `[project] dependencies` except `uvicorn` and `asyncpg` is imported under `src/`                                                | a declared dependency that nothing imports is DEP002. Import it where `SSOT.md` § Structure puts it, or `uv remove` it until code needs it |
| `env -u PYTHONPATH uv run pytest tests -q --cov` | `tests/` covers every line and branch of `src/app`, `main.py` aside                                                                             | `fail_under = 100` with `branch = true` (`.claude/rules/python/coverage.md`)                                                               |

Run the whole CI gate locally before opening a pull request:

```bash
bash .github/scripts/quality-gate.sh origin/dev
```

In the pipeline shape, add the Migration Drift Check and Docs Drift Check from
`.claude/examples/pipeline/README.md` § Gate additions to `quality-gate.sh`, after "Production
Build", gated the way "Run Integration Tests" already is.

### `.env.<target>.example` files

Commit one template per environment, `.env.development.example` and `.env.production.example`,
holding every key with a placeholder value and never a real one. `.gitignore`, `.dockerignore` and
the hooks leave `*.example` files open; every other `.env*` file stays ignored and locked.

- `bash scripts/env/show.sh .env.production` lists the keys the real file lacks compared with its
  template, and exits 1 when one is missing.
- `/promote` and `/promote-deploy` audit production's live configuration against
  `.env.production.example`, and print only key names with a verdict.
- `SSOT.md` § Env Variables documents the same keys, and `AGENTS.md` Rule 21 keeps real files out
  of git.

### PR-only CI, and why there are no schedulers

Every workflow starts from a pull-request event: `pull_request`, a merged pull request (checked
with `github.event.pull_request.merged`), or an `issue_comment`. There is no `push:` trigger, no
`schedule:` and no bot that opens update pull requests.

- A push run repeats the pull request's run and spends minutes to learn nothing new; after-merge
  work (the deploy, the strip) runs on the merged pull request, which is the same moment.
- A scheduled job runs on an idle repository and fails where nobody looks. A bot that opens
  update pull requests on its own timetable is a scheduler too.
- Instead, update on purpose in an ordinary pull request, which `dependency-review.yml` checks:
  `pinact run -u --min-age 7` for actions (the age is a cooldown against a freshly compromised
  release) and `uv lock --upgrade` for Python packages.

`docs/RATIONALE.md` § 12 has the trade-offs, including what OpenSSF Scorecard scores down.

### Service containers, with the first integration test

`quality-gate.yml` starts no database: the unit tier never dials one, and "Run Integration Tests"
collects nothing until an integration test exists. Add Postgres and Redis to the `quality-gate` job
together with that first test, above its `env:` block, with the same `<user>`, `<password>` and
`<database-name>` as its `DATABASE_URL`:

```yaml
    services:
      postgres:
        image: postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24
        env:
          POSTGRES_USER: <user>
          POSTGRES_PASSWORD: <password>
          POSTGRES_DB: <database-name>
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U <user> -d <database-name>"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
      redis:
        image: redis:7-alpine@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
```

Every image carries a digest, like every action carries a commit SHA. To pin another image (say
`pgvector/pgvector:pg17` when embeddings live in Postgres), read its digest with
`docker buildx imagetools inspect <image>`.

### Repository settings

| Setting                               | Where                                      | Why                                                                                                                                                                                                              |
| :------------------------------------ | :----------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Squash merging off**                | Settings → General → Pull Requests         | `/merge-pr` and `/promote` merge with `--merge`, and `/branch-cleanup` can only prove a merge commit merged (RATIONALE § 14)                                                                                     |
| `DEEPSEEK_CODE_REVIEW_TOKEN` (secret) | Settings → Secrets and variables → Actions | only if you keep `deepseek-review.yml`                                                                                                                                                                           |
| `DEPLOY_WEBHOOK_URL` (secret)         | same                                       | your platform's deploy webhook, fired when a pull request into `prod` is merged                                                                                                                                  |
| `CODE_SECURITY=true` (variable)       | same                                       | a private repository with GitHub Code Security; until then dependency review and CodeQL skip                                                                                                                     |
| `CI_RUNNER`, `CI_RUNNER_FAST`         | same, variables, optional                  | runner labels; unset means `ubuntu-latest` (`.claude/CI-RUNNERS.example.md`)                                                                                                                                     |
| Required checks                       | a branch ruleset for `dev` and `prod`      | `Quality Gate`; `Dependency Review` and `Analyze (<language>)` only on a public repository or with `CODE_SECURITY=true`; never `Workflows Lint`, whose path filter keeps it from reporting on most pull requests |

A job skipped by its `if:` reports success, so requiring Dependency Review or CodeQL on a private
repository without Code Security proves nothing. `scripts/ops/pr-ready.sh` does not count a skipped
or neutral check as a pass: it names each one and exits 1. `/merge-pr` and `/promote` show you that
list and pass `--allow-skipped` only after you confirm that every listed check skips by design.

### On dependency audits

If `pip-audit` reports a transitive dependency, **check where the advisory comes from before
accepting an ignore flag.** Advisories often all arrive through one parent dependency, and two
things genuinely fix that:

1. Upgrade the parent. If that is a breaking major, do it as its own change, not folded into a CI
   change.
2. Pin the transitive dependency to a patched release directly in `dependencies` or `dev`.

An ignore flag left behind after the problem is fixed is not untidiness: it will hide the next
report, for a different vulnerability.

---

## 7. Slash commands and their mirrors (optional)

```bash
bash scripts/sync/workflows.sh           # write the mirrors
bash scripts/sync/workflows.sh --check   # verify without writing: the mode pre-commit and CI run
```

Edit commands in `_workflow-source/` only. `--check` is the mode that catches drift: a write-mode
run **overwrites staleness before it can observe it**, so wire `--check` into gates and the write
mode into nothing.

`.agent/workflows/` is a mirror for a second tool that reads commands from that path. Keeping it is
cheap and automatic; deleting it is cleaner. Either is fine, as long as you know which applies.

---

## 8. The AI-config strip pipeline (last, and only if you want it)

**This is the only part that deletes files. Everything else should be working before you touch
it.**

| Script               | Role                                                                       |
| :------------------- | :------------------------------------------------------------------------- |
| `strip-paths.sh`     | **The single source of truth** for what gets removed; the others source it |
| `strip-ai.sh`        | Removes those paths on the production branch                               |
| `verify-strip.sh`    | Asserts they are gone from `prod` **and still present on `dev`**           |
| `back-merge-prod.sh` | Merges `prod` back into `dev` so the branches do not diverge               |

Three things that are not obvious:

- **One list, sourced, never copied.** With the path list duplicated across scripts, updating one
  copy and not the others makes the strip half-land: production keeps part of the layer and
  nothing reports an error.
- **Verify both directions.** Checking only that `prod` lost the files misses the failure where
  `dev` lost them too.
- **Merge, never rebase, on the way back.** Rebasing rewrites the strip commit and the branches
  diverge permanently.

Adopt it in this order:

1. Run `strip-ai.sh` on a throwaway branch and inspect what disappeared.
2. Run `verify-strip.sh` and confirm it fails when you deliberately skip a path.
3. Only then rely on `strip-ai-on-pr.yml`.

---

## Verify the whole thing

```bash
grep -rn -e '<[A-Za-z]' -e 'your-github-handle' \
  CLAUDE.md AGENTS.md SSOT.md pyproject.toml .claude/agents .github   # only shapes remain (§ 2)
bash .github/scripts/check-comment-blocks.sh                         # exits 0
bash scripts/sync/workflows.sh --check                               # mirrors in sync
bash scripts/check/gates.sh                                          # the commit gate, by hand
bash .github/scripts/quality-gate.sh origin/dev                      # the CI gate, locally
```

Then the test no script performs: open a session and ask the agent to make a change you know breaks
a rule, such as calling a vendor SDK directly from a service instead of through a `Protocol`. If
nothing objects, the rule is prose rather than a guardrail: check that `ai-reviewer` actually runs
in your workflow (ask for it by name, or through `/review`), and treat that as the general remedy
whenever a rule is not holding.
