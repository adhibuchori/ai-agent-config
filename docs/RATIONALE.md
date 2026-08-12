# Rationale

Why the odd-looking parts of this configuration are shaped the way they are.

Every entry below is something that cost someone real time to discover, in the fleet this template
is drawn from. Several look like clutter and are load bearing — this file exists so you can tell
which is which before you tidy anything.

**One rule while reading: if a pattern here looks needlessly complicated, do not simplify it.**
Each one is followed by what breaks when you do.

---

## 1. `PreToolUse` blocks; everything else only complains

The single most important thing to understand about hooks.

| Hook | Non-zero exit means |
| --- | --- |
| `PreToolUse` | **The tool call does not happen.** This is a real guardrail |
| `PostToolUse` | Reported, then ignored. The write already landed |

So a rule that must not be violated belongs in `PreToolUse`. Put it in `PostToolUse` and you get a
guard that appears installed, logs complaints, and prevents nothing.

**Corollary: test a guard by triggering it.** A guard whose pattern does not match your actual code
never fires and never complains. Reading the script tells you what it intends; only triggering it
tells you what it matches.

---

## 2. Two silent hook failure modes on macOS — and why they compound

`.claude/hooks/lib.sh`'s `resolve_tool` and `run_capped` exist because of two independent traps,
documented in full in `.claude/anti-patterns/hooks-silent-noop-on-macos.md`:

- `ruff`/`mypy`/`pytest` live in `.venv/bin/`, not on `PATH` — a bare `command -v ruff` guard
  always misses.
- macOS ships no `timeout` by default — `timeout 5 ruff format "$FILE" || true` fails with exit
  127, and `|| true` swallows it.

Both produce the same observable behavior: exit 0, no error, no actual work done. That's why they
get one shared helper file instead of two separate one-line "fixes" — a fix to one half without the
other still silently does nothing.

---

## 3. An inherited `PYTHONPATH` breaks mypy's pydantic plugin

Documented in full in `.claude/anti-patterns/pythonpath-breaks-mypy-plugin.md`. The short version:
some agent harnesses export a `PYTHONPATH` that shadows your project's `.venv/`, and mypy's
pydantic plugin fails to import its compiled extension as a result — with an error that reads
exactly like a broken virtual environment. It is not. `env -u PYTHONPATH uv run mypy src` is the
first thing to try, not a full `uv sync --reinstall`.

---

## 4. `--check` mode, and why write mode cannot replace it

Mirror scripts run in two modes. Only one detects drift:

```bash
bash scripts/sync-workflows.sh           # write
bash scripts/sync-workflows.sh --check   # verify — this is the CI mode
```

A write-mode run **overwrites staleness before it can observe it**. Run it in CI and the mirrors
are always in sync, because the check just fixed them — a check that always passes is not a check.

---

## 5. The provider `Protocol` pattern is about testability first, swappability second

It's easy to read "every external dependency is a `Protocol` plus a default adapter" as premature
abstraction for a service that only ever talks to one vendor. It isn't, for a reason that has
nothing to do with swapping vendors: a service that takes its provider as a default parameter can
be unit-tested with a fake that returns a controlled reply, with zero mocking library and zero live
network calls. A service that imports the vendor SDK at module scope cannot be tested that way at
all without `unittest.mock.patch`, which tests that you called the SDK correctly, not that your
business logic behaves correctly.

---

## 6. Checking the completion status before trusting streamed text is the highest-value single check in this template

Some LLM vendors' safety filters can decline a request **while still streaming partial text** — the
stream doesn't just stop, it can complete with content that looks like a normal (if oddly short)
answer, tagged internally with a non-success status. Accumulating that text and returning it
delivers a refusal to the user as a broken answer instead of a clean, recognizable error. The check
has to happen before the accumulated text is treated as content, not after — "after" is exactly the
bug. Keep whatever regression test pins this down; it is worth more than most of the rest of the
test suite combined, because the failure mode it prevents is silent and plausible-looking rather
than a crash.

---

## 7. A pinned gitleaks binary with a checksum, not "gitleaks" on PATH

`quality-gate.sh`'s secret-scan step downloads a specific gitleaks version and verifies its SHA256
before running it, falling back to a PATH install only if the pinned download fails. This is not
paranoia: a scanner whose ruleset silently changed between CI and a contributor's machine can pass
locally and fail in CI, or the reverse — worse, it can pass in both places while looking at
different rules. Pin the binary, verify the checksum, and the scan means the same thing everywhere
it runs.

---

## 8. The cross-repo schema mirror (if Rule 13 applies) is a deliberate manual step, not a bug waiting for automation

If a read-only service keeps `db/models.py` as a hand-synced copy of a schema-owning sibling repo's
file rather than a shared package, that's not an oversight — a shared package would need its own
release/version process for what is, in practice, a rare change. The manual mirror is a documented,
enforced-by-hook trade-off: cheap most of the time, and a `diff` command away from being verified
whenever you're unsure it's still accurate. If the mirror starts drifting often enough to hurt,
that's the signal to build the shared package — not a reason to stop mirroring in the meantime.

---

## 9. Import-linter contracts, not code review, own the layer boundary

`AGENTS.md` §B's `routes → handlers → service → (repository)` boundary is enforced by three
`[[tool.importlinter.contracts]]` blocks in `pyproject.toml`, checked by `uv run lint-imports` in
CI — not by asking a reviewer to notice a stray import. The cost of this is real: every new module
must be added to all three contract blocks, and forgetting one leaves that module's layering
unchecked while CI stays green. The alternative — trusting a human to notice a boundary violation
in a diff — has a worse failure mode: it degrades silently as the codebase grows and reviewers get
busier, exactly when the check matters most.
