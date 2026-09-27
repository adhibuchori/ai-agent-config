# Rationale

Why the odd-looking parts of this configuration are shaped the way they are. Several look like
clutter and are load-bearing; each entry says what breaks when you simplify it, so you can tell
which is which before you tidy anything.

| Area        | Entries                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| :---------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hooks       | [1 exit 2](#1-only-exit-2-blocks-a-pretooluse-call) · [2 macOS](#2-two-silent-hook-failures-on-macos) · [11 parser and probes](#11-a-command-parser-and-probes-not-substring-matching) · [16 unlock](#16-a-lock-only-the-user-can-open) · [17 stdin](#17-hooks-read-json-on-stdin-never-an-environment-variable) · [19 one post-edit hook](#19-format-and-lint-run-in-one-hook) · [20 fail-closed](#20-refuse-what-the-analyzer-cannot-resolve) |
| Python      | [3 PYTHONPATH](#3-an-inherited-pythonpath-breaks-mypys-pydantic-plugin) · [5 providers](#5-the-provider-protocol-is-about-testability-first) · [6 completion status](#6-check-the-completion-status-before-trusting-streamed-text) · [8 schema mirror](#8-the-cross-repo-schema-mirror-is-a-manual-step) · [9 import-linter](#9-import-linter-contracts-own-the-layer-boundary)                                                                 |
| Context     | [10 budget](#10-a-context-budget-and-no-imports) · [13 SkillSpector](#13-skillspector-reads-what-a-reviewer-cannot-see) · [18 MCP pins](#18-mcp-servers-pinned-and-permissions-only-in-settingsjson)                                                                                                                                                                                                                                            |
| Gate and CI | [4 `--check`](#4---check-mode-and-why-write-mode-cannot-replace-it) · [7 gitleaks](#7-a-pinned-gitleaks-build-with-a-checksum) · [12 PR-only CI](#12-ci-starts-only-from-pull-requests) · [14 merge commits](#14-merge-commits-not-squash) · [15 deploy](#15-a-vendor-neutral-deploy)                                                                                                                                                           |

---

## 1. Only exit 2 blocks a `PreToolUse` call

The single most important thing to understand about hooks.

| Hook          | What its exit code does                                                                                            |
| :------------ | :----------------------------------------------------------------------------------------------------------------- |
| `PreToolUse`  | **Exit 2 stops the call**, and stderr is the reason Claude reads. Exit 0, exit 1, a crash or a timeout lets it run |
| `PostToolUse` | Nothing can be stopped: the write already landed. Feedback reaches Claude only through `additionalContext`         |

So a rule that must not be broken belongs in a `PreToolUse` guard that exits 2, and the guard must
decide what happens when it fails. A guard that crashes, or that trips `set -e`, exits 1 and lets
the command through. That is why the guards here fail closed: a payload they cannot parse, an
analyzer that crashes or runs past its time cap, or a command whose effect the analyzer cannot
resolve (§ 20) is refused with exit 2. Put a rule in `PostToolUse` and you get a hook that appears
installed, reports complaints, and prevents nothing.

**Corollary: test a guard by triggering it.** A guard whose pattern does not match your real input
never fires and never complains. Reading the script tells you what it intends; only feeding it the
JSON Claude Code sends tells you what it matches (§ 11).

---

## 2. Two silent hook failures on macOS

`.claude/hooks/lib.sh`'s `resolve_tool` and `run_capped` exist because of two independent traps,
documented in full in `.claude/anti-patterns/hooks-silent-noop-on-macos.md`:

- `ruff`, `mypy` and `pytest` live in `.venv/bin/`, not on the hook's `PATH`, so a bare
  `command -v ruff` guard always misses. `resolve_tool` looks in `node_modules/.bin`, `.venv/bin`,
  then `PATH`, and never falls back to `uvx` or `npx`: a hook must not download and run a package.
- macOS ships no `timeout`, so `timeout 5 ruff format "$FILE" || true` fails with exit 127 and
  `|| true` swallows it. `run_capped` uses `timeout` or `gtimeout` when one exists and a background
  timer otherwise.

Both produce the same observable behaviour: exit 0, no error, no work done. That is why they share
one helper file instead of two one-line fixes: fixing one half still leaves the hook doing nothing.

---

## 3. An inherited `PYTHONPATH` breaks mypy's pydantic plugin

Documented in full in `.claude/anti-patterns/pythonpath-breaks-mypy-plugin.md`. Some agent
harnesses export a `PYTHONPATH` that shadows the project's `.venv/`, and mypy's pydantic plugin
then fails to import its compiled extension, with an error that reads exactly like a broken virtual
environment. It is not one. Every mypy and pytest command here runs as
`env -u PYTHONPATH uv run …`; try that before a `uv sync --reinstall`.

---

## 4. `--check` mode, and why write mode cannot replace it

Mirror scripts run in two modes. Only one detects drift:

```bash
bash scripts/sync/workflows.sh           # write
bash scripts/sync/workflows.sh --check   # verify: the mode pre-commit and CI run
```

A write-mode run **overwrites staleness before it can observe it**. Run it in CI and the mirrors
are always in sync, because the run just fixed them: a check that always passes is not a check.

---

## 5. The provider `Protocol` is about testability first

"Every external dependency is a `Protocol` plus a default adapter" reads like premature abstraction
for a service that only ever talks to one vendor. It is not, for a reason unrelated to swapping
vendors: a service that takes its provider as a default parameter can be unit-tested with a fake
that returns a controlled reply, with no mocking library and no network. A service that imports the
vendor SDK at module scope can only be tested with `unittest.mock.patch`, which tests that you
called the SDK correctly, not that your business logic behaves.

---

## 6. Check the completion status before trusting streamed text

Some LLM vendors' safety filters can decline a request **while still streaming partial text**: the
stream completes with content that looks like a normal, oddly short answer, tagged with a
non-success status. Accumulating that text and returning it delivers a refusal to the user as a
broken answer instead of a clean, recognisable error. The check has to happen before the
accumulated text is treated as content; "after" is exactly the bug (`AGENTS.md` Rule 15). Keep the
regression test that pins this down. The failure it prevents is silent and plausible rather than a
crash, which makes it worth more than most of the suite.

---

## 7. A pinned gitleaks build with a checksum

On a Linux x86_64 runner, `.github/scripts/quality-gate.sh` downloads gitleaks 8.30.1 and verifies
its SHA-256 before running it. If the download or the check fails, the gate fails: it never falls
back to another binary there. On any other machine, where no pinned build is fetched, it uses the
gitleaks on `PATH`, like the commit hook does; with none installed it records the scan as not run,
which fails a `--strict` run.

This is not paranoia. A scanner whose ruleset changed between CI and a contributor's machine can
pass in one place and fail in the other, or pass in both while looking at different rules. Pin the
binary, verify the checksum, and the CI scan means the same thing on every run.

---

## 8. The cross-repo schema mirror is a manual step

If `AGENTS.md` Rule 13 applies, `src/app/db/models.py` is a hand-synced copy of the schema owner's
file rather than a shared package. That is deliberate: a shared package needs its own release and
version process for what is, in practice, a rare change. Enforcement is advisory: nothing diffs the
two files yet, `CODEOWNERS` asks for a review of every change to the mirror, and a `diff` against
the owner's copy settles any doubt. If the mirror starts drifting often enough to hurt, build the
shared package then, and keep mirroring until it exists.

---

## 9. Import-linter contracts own the layer boundary

`AGENTS.md` §B's `routes → handlers → service → (repository)` boundary is enforced by three
`[[tool.importlinter.contracts]]` blocks in `pyproject.toml`, checked by `uv run lint-imports` at
every commit and in CI, not by asking a reviewer to notice a stray import. The cost is real: every
new module must be added to the layers contract's `containers` and the independence contract's
`modules`, and forgetting one leaves that module unchecked while the gate stays green. The
alternative, a human spotting a boundary violation in a diff, degrades silently as the codebase
grows and reviewers get busier, exactly when the check matters most.

---

## 10. A context budget, and no `@imports`

Everything that loads at session start is read on every task, whether it applies or not, and costs
context that the task needs. So only two files load every session: `CLAUDE.md` and
`.claude/rules/common/working-agreements.md`, 11,705 bytes in this template.
`scripts/check/ai-config.sh` fails the commit when that total passes 15,000 bytes.

The rest waits until it is relevant. Every other rule opens with a `paths:` list and loads only
while a matching file is in play; the references (`OPERATIONS`, `DATABASE`, the review checklist,
the anti-patterns) are rows in `CLAUDE.md` § On-demand References that Claude reads when the row
matches; the pipeline shape sits in `.claude/examples/`, which nothing loads. `CLAUDE.md` carries
no `@path` import, because an import loads its file every session and would move the budget out of
sight; the check refuses one even inside an HTML comment, where it is easy to miss.

**What breaks when you simplify it:** drop the `paths:` list from a rule, or import a reference,
and the budget check fails. Raise the budget instead, and every session pays for it.

---

## 11. A command parser and probes, not substring matching

A guard that greps the command text for `push --force` both over-blocks and under-blocks. It
refuses `echo "never push --force"`, which teaches people to switch the hook off, and it misses
`git -C . push origin +main`, `bash -c '…'` and a push hidden in `$( )`. `safety-check.sh` reads a
command the way a shell does instead: quotes, `$'…'`, heredocs, `$( )`, backticks, `bash -c`,
`eval`, aliases, loop and exported variables, and wrappers such as `env`, `sudo`, `timeout` and
`xargs`. Package runners (`npx`, `bunx`, `pnpx`, `npm`/`pnpm`/`yarn`/`bun` `exec`, `dlx` and `x`)
are peeled too, and the shell text a runner takes (a `-c` string, the words of `bun exec '…'`) is
read as a script. Nesting deeper than six levels is refused rather than half read.

`scripts/check/hook-probes.sh` proves every rule in both directions (what it must stop, what it
must let through), plus each hook's fail mode, a linked git worktree and the plugin-mode project
gate: 2,330 probes in this template. It runs at every commit that touches a hook and in CI. A rule
without a probe that fails when the rule is removed is a rule nobody has seen work.

The analyzer reads text, so it cannot follow every path a command builds at run time. It refuses
those instead of guessing (§ 20), and Claude Code's Bash sandbox, which `.claude/settings.json`
turns on by default, enforces the `.env` and unlock denies at the operating-system level for every
sandboxed command. A script file Claude writes and then runs by name is still executed, not read,
and a program the hooks do not know that runs commands of its own (`watch`, `script`, `flock`,
`parallel`) is judged by name only; `docs/unlock.md` lists those and the other limits.

---

## 12. CI starts only from pull requests

No workflow here runs on `push` or on a `schedule`, and no bot opens update pull requests. Allowed
triggers are `pull_request` (including a merged pull request, checked with
`github.event.pull_request.merged`), `issue_comment`, `repository_dispatch` and `workflow_call`.

- **Why no push trigger.** In a flow where every change reaches `dev` and `prod` through a pull
  request, a push run repeats the pull request's run and spends runner minutes to learn nothing
  new. After-merge work (the deploy, the strip) runs on the merged pull request, which is the same
  moment.
- **Why no scheduler.** A scheduled job runs on an idle repository, fails where nobody is looking,
  and keeps spending. A bot that opens update pull requests on its own timetable is a scheduler
  too.
- **Why not `pull_request_target`.** It runs with the repository's secrets while handling a pull
  request, and paired with a checkout of that pull request it is the pattern GitHub is moving to
  block by default. The AI review uses `pull_request` plus an `/ask-deepseek` comment and never
  checks out the pull request's code.

**The trade, accepted on purpose.** Updates happen when someone opens a pull request for them
(`pinact run -u --min-age 7`, `uv lock --upgrade`), and `dependency-review.yml` checks each one.
OpenSSF Scorecard's `Dependency-Update-Tool` check scores 0, and CodeQL never analyses the default
branch by itself, so GitHub has no baseline alert list for it.

**What breaks when you "fix" it:** add `push:` and every merge runs twice; add a schedule and the
repository spends minutes while nobody works on it.

---

## 13. SkillSpector reads what a reviewer cannot see

Commands, the reviewer subagent and the hooks are instructions an agent follows. An instruction
hidden in one (an HTML comment asking the agent to send a file somewhere) does not render on GitHub,
so it survives code review. `scripts/check/skills.sh` runs a pinned SkillSpector build over them at
every commit that touches one and in CI when one changed.

`.skillspector-baseline.yaml` holds the accepted findings, each with its reason. The check also
fails when a file was scanned only in part, unless the baseline names that exact file and reason:
a partial scan that passes is a scan that read nothing. **What breaks when you simplify it:** a
wildcard in the baseline, or a skipped partial scan, hides the next real finding. It is also why
each command keeps its HTML comments to the three header lines.

---

## 14. Merge commits, not squash

`/merge-pr` and `/promote` merge with `--merge`, and squash merging is turned off in the repository
settings. `/branch-cleanup` deletes a branch only when GitHub reports it zero commits ahead of
`dev`, which is exact for a merge commit. After a squash, the branch's own commits are never
ancestors of `dev`, so it always reads as ahead: the cleanup would keep every branch, or a looser
test would delete unmerged work. The strip pipeline relies on merges too: `prod` is merged back
into `dev` after the strip, never rebased, so the strip commit keeps its identity on both branches.

---

## 15. A vendor-neutral deploy

`ci-cd.yml` fires one webhook (`DEPLOY_WEBHOOK_URL`) when a pull request into `prod` is merged, and
the platform builds from git. No image is built in CI and no vendor action runs with deploy
credentials. The deploy-platform, VPS-provider and Cloudflare MCP servers ship only as on-demand
examples (`.claude/mcp/*.example.json`), and `/promote` names the platform in a table you fill once,
with a small adapter (read the live env, latest deployment, trigger, backup) written as your
platform runs it.

A webhook is the one interface every platform offers. **What breaks when you hard-code one:**
every adopter on another platform deletes it first, and a third-party action holding deploy
credentials joins the supply chain of every pull request.

---

## 16. A lock only the user can open

`.env*` files and production database writes are locked. Claude reads an env file only through
`scripts/env/show.sh`, which masks every secret, and changes a value only through
`scripts/env/set.sh` while `env` is unlocked. Any other shell read or write of a real `.env*` file
is refused. `db-guard.sh` holds every production SQL write until `db` is unlocked.

- **Why a command, not a phrase in the prompt.** A phrase that lifts a deny rule can arrive inside
  a file Claude reads, or be typed out of habit. `./scripts/ops/unlock.sh` runs only when the user
  types it with `!` or in their own terminal; the hooks refuse it from Claude by every route they
  can read (a shell, a wrapper, a package runner, a git alias, `find -exec`), including writing the
  unlock files directly.
- **Why it closes by itself.** An unlock is a file holding its end time (default 20 minutes for
  `env`, 15 for `db`). A lock left open by accident is the same as no lock, so it expires without
  anyone remembering to close it.
- **Why a sandbox under the hooks.** The hooks judge a command line; the sandbox judges what the
  process actually opens. `sandbox.filesystem.denyRead` covers every `.env*` shape and the `.env`
  backups, `denyWrite` covers `.claude/state/unlock/`, `.claude/hooks/` and `scripts/ops/unlock.sh`,
  and only `show.sh` and `set.sh` run outside it, so a route the analyzer never saw still cannot
  read a secret, forge an unlock or rewrite a guard. It is on by default (`sandbox.enabled: true`)
  and needs macOS, or Linux or WSL2 with `bubblewrap` and `socat`; WSL1 and native Windows have
  none. Where it cannot start, Claude Code warns and runs commands without it unless
  `sandbox.failIfUnavailable` is `true`, and the hooks alone apply. A command that fails inside it
  may be retried outside through the permission prompt (`sandbox.allowUnsandboxedCommands: false`
  forbids that), and `"sandbox": {"enabled": false}` in `.claude/settings.json` or
  `.claude/settings.local.json` turns it off.
- **Why the database server still starts read-only.** `--access-mode=restricted` is enforced by the
  server, below any hook, and it also stops a function of your own that writes behind a `SELECT`.
  `db-guard.sh` is for a project that deliberately gives the production server write access for
  incidents.

`docs/unlock.md` has the whole mechanism and, just as important, what it does not stop.

---

## 17. Hooks read JSON on stdin, never an environment variable

Claude Code hands a hook the tool call as one JSON object on stdin (`tool_name`, `tool_input`,
`cwd`, `session_id`) and sets no `CLAUDE_TOOL_INPUT_*` variable. A hook written against such a
variable reads an empty string, matches nothing and exits 0 on every call: wired, installed and
inert, with no error anywhere. `lib.sh` reads stdin once and parses it with jq or python3, and a
guard refuses a payload that is not one JSON object (§ 1). `scripts/check/ai-config.sh` fails when
a hook script names a `CLAUDE_TOOL_INPUT_` variable, and
`.claude/anti-patterns/hooks-read-env-vars-never-set.md` has the whole trap.

**What breaks when you simplify it:** a guard rewritten to read `$CLAUDE_TOOL_INPUT_COMMAND` looks
right in review and never blocks anything. Only a probe that pipes a real payload in shows it
(§ 11).

---

## 18. MCP servers pinned, and permissions only in `settings.json`

Every server `.mcp.json` starts with `uvx` or `npx` names an exact release (Serena's `v1.7.0`
commit, `@4.1.1`, `==0.3.0`), and `scripts/check/ai-config.sh` fails on one that does not, in
`.mcp.json` and in each `.claude/mcp/*.json` copy. A major-only `@1` or a major.minor `@1.2` counts
as not pinned, since both move with every release under them, and
`scripts/check/ai-config-probes.sh` runs the check on pinned and movable specs to prove it catches
every one. An unpinned server runs whatever was published last, on every session start, with the
tokens its entry passes it: a fresh clone would run code nobody here reviewed.

Tool permissions for those servers live in `.claude/settings.json` (`mcp__db-prod__execute_sql` is
an `ask` rule, and `db-guard.sh` holds its writes). `.mcp.json` has no permission field that Claude
Code reads: an `alwaysAllow` list copied there from another client's format is ignored, so a rule
written there looks set and does nothing. **What breaks when you simplify it:** drop a pin and the
server upgrades itself under you; move a permission into `.mcp.json` and it silently stops
applying.

---

## 19. Format and lint run in one hook

`post-edit.sh` runs `ruff format`, then `ruff check`, on the file just written, as one script.
Claude Code runs the hooks of one event in parallel, so a formatter and a linter wired as two
`PostToolUse` hooks race on the same file: the linter reads it half rewritten, or reports lines the
formatter is about to move, and the note Claude gets describes a file that no longer exists.

**What breaks when you simplify it:** split the script into a format hook and a lint hook and the
findings turn intermittent, the kind that gets the lint hook switched off.

---

## 20. Refuse what the analyzer cannot resolve

`safety-check.sh` refuses a command when it cannot tell what that command touches, even when the
text names no `.env` file and no unlock: computed or decoded code (`eval`, a decoded payload, text
piped into a shell), a `$( )` or backticks used as the command name or as a file operand, a path
built through `IFS`, `dotglob`, an array or `printf`, a package runner whose command or script is
built from `$( )` or an unknown variable, a recipe read from stdin (`make -f /dev/stdin`), inline
code that opens a file, a copy that lands on `.claude/state/` or a `.env*` file, and `xargs`
feeding a file reader. So is any git setting that changes what git runs, loads or connects to (an
alias, an include, `core.sshCommand`, a credential helper, `protocol.*.allow`, a proxy,
`url.*.insteadOf`, `safe.directory`), whatever its value, and so is every command when the
analyzer crashes, runs past 8 s or cannot read its payload. The refusal names the reason and tells
Claude to hand the command to you to run with `!`. Without python3 only plain-text rules stand in
(protected pushes, recursive deletes, a hard reset or forced clean, a skipped gate, `.env*` names
and the unlock), and Claude is told so.

- **Why not allow what looks harmless.** Each of these forms hides the file name or the command
  until the shell runs it, which is how a command gets past a text check. A guard that allows what
  it cannot read is a guard with a documented way around it.
- **Why the `!` hint.** A refusal with no way forward teaches people to turn the hook off. A `!`
  command runs as you, with your own access, outside Claude's hooks and (in an ordinary session)
  outside the sandbox, so a false refusal costs one retyped command.
- **The one allowance.** `cat $(git ls-files '*.md')` is common and safe: a literal
  `git ls-files <pathspec>` or `git diff --name-only`, with no option before the subcommand and
  pathspecs that cannot match `.env*`, is run read-only to confirm and then allowed.

**What breaks when you simplify it:** allow unresolved commands again and the unlock and the
`.env` lock hold only against commands that name their target in plain text, which is exactly the
kind an instruction hidden in a file avoids.
