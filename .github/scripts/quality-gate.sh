#!/usr/bin/env bash
# Runs the checks quality-gate.yml runs, for promotions that cannot use CI.
# Usage: quality-gate.sh [base-ref] [--strict]   default origin/dev. See README § CI/CD.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 2

BASE="origin/dev"
for arg in "$@"; do
  case "$arg" in --strict) ;; *) BASE="$arg" ;; esac
done
failed=0
skipped=""

# On a runner a skipped check is a hole in the gate, so it fails instead.
STRICT=0
[ "${CI:-}" = "true" ] && STRICT=1
case " $* " in *" --strict "*) STRICT=1 ;; esac

step() {
  printf '\n\033[1m── %s\033[0m\n' "$1"
}

run() {
  step "$1"
  shift
  if ! "$@"; then
    echo "::error::$* failed"
    failed=$((failed + 1))
  fi
}

# A check that cannot run here is recorded, never silently passed — the summary
# at the end is what tells you the gate was partial.
skip() {
  skipped="${skipped}"$'\n'"  $1 — $2"
}

git rev-parse --verify "$BASE" >/dev/null 2>&1 || {
  echo "::error::base ref '$BASE' not found; run: git fetch origin"
  exit 1
}

# What scripts/check/gates.list runs (the commit hook runs it too), then the checks only CI runs.
run "Install Dependencies" uv sync --frozen
run "Format & Lint" bash -c "uv run ruff format --check . && uv run ruff check ."
run "Type Check" env -u PYTHONPATH uv run mypy .
run "Import Boundaries" uv run lint-imports
run "Dead Code Check" uv run vulture
run "Dependency Check" uv run deptry src
run "Folder Shape Check" node scripts/check/folder-shape.mjs
run "Coverage Policy Check" node scripts/check/coverage-policy.mjs
run "Unit Tests" env -u PYTHONPATH uv run pytest tests -q --cov
run "Security Audit" uv run pip-audit --skip-editable

step "Secret Scan (gitleaks)"
GITLEAKS_VERSION=8.30.1
GITLEAKS_SHA256=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
GL=""

# The pinned build and checksum, exactly as CI fetches them. Any other binary is
# a different scan, so elsewhere it falls back to whatever is installed.
if [ "$(uname -s)" = "Linux" ] && [ "$(uname -m)" = "x86_64" ]; then
  GL_URL="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
  if curl -sSfL -o gitleaks.tar.gz "$GL_URL" \
      && echo "${GITLEAKS_SHA256}  gitleaks.tar.gz" | sha256sum -c - \
      && tar xzf gitleaks.tar.gz gitleaks; then
    GL=./gitleaks
  else
    echo "::error::could not fetch or verify the pinned gitleaks build"
    failed=$((failed + 1))
  fi
elif command -v gitleaks >/dev/null 2>&1; then
  GL=gitleaks
fi

if [ -n "$GL" ]; then
  if ! "$GL" git . --no-banner --redact --config .gitleaks.toml; then
    echo "::error::gitleaks found findings"
    failed=$((failed + 1))
  fi
elif [ "$failed" -eq 0 ]; then
  echo "gitleaks not installed — brew install gitleaks"
  skip "Secret Scan (gitleaks)" "no pinned build for $(uname -sm), none on PATH"
fi
rm -f gitleaks gitleaks.tar.gz

# Any env file this branch adds or changes, at any depth, except the committed templates.
step "Check .env Not Committed"
if git diff "$BASE"...HEAD --name-only --diff-filter=ACMR | grep -E '(^|/)\.env(\.|$)' | grep -qvE '(^|/)\.env(\.[a-z]+)?\.example$'; then
  echo "::error::.env file committed"
  failed=$((failed + 1))
else
  echo "Clean"
fi

# Rule citations (a new rule renumbers AGENTS.md), the always-loaded budget, hook wiring, MCP pins.
run "AI Config Check" bash scripts/check/ai-config.sh
run "AI Config Pin Probes" bash scripts/check/ai-config-probes.sh
# What each Claude Code hook must block and let through; skips on a branch without the hooks.
run "Hook Probes" bash scripts/check/hook-probes.sh

# SkillSpector scans skills, commands, subagents and hooks; it installs and runs when one changed.
step "Skill Security Scan"
SKILL_PATHS=(.agents/skills .claude/skills .claude/commands .claude/agents .claude/hooks _workflow-source .skillspector-baseline.yaml scripts/check/skills.sh)
if [ ! -d .claude ]; then
  echo ".claude/ not present on this branch - skipping"
elif git diff --quiet "$BASE"...HEAD -- "${SKILL_PATHS[@]}"; then
  echo "No skill, command, subagent or hook changed - skipping"
elif ! command -v uv >/dev/null 2>&1; then
  echo "::error::uv is required to install the pinned SkillSpector"
  failed=$((failed + 1))
else
  if ! command -v skillspector >/dev/null 2>&1; then
    uv tool install --quiet --python 3.12 "git+https://github.com/NVIDIA/skillspector.git@69dcdfb74487d361ba4c811d088cfdea2ff3a9dc"
    PATH="$(uv tool dir --bin):$PATH"
  fi
  bash scripts/check/skills.sh --changed "$BASE" || failed=$((failed + 1))
fi

run "Comment Block Length Check" bash .github/scripts/check-comment-blocks.sh

# A stale copy under .claude/commands/ still reads as valid, and INDEX.md is what an agent
# consults to discover the commands at all. Skipped on prod, where the strip removed the source.
step "Workflow Mirror Drift Check"
if [ ! -d _workflow-source ] || [ ! -f scripts/sync/workflows.sh ]; then
  echo "_workflow-source/ not present on this branch - skipping"
elif ! bash scripts/sync/workflows.sh --check; then
  echo "::error::workflow mirror or INDEX.md has drifted"
  failed=$((failed + 1))
fi

run "Production Build" docker build -t "<repo-name>" .

# A repo that owns its schema adds the Migration and Docs Drift Checks here, after the build
# (.claude/examples/pipeline/README.md § Gate additions has both lines and how to gate them).

# Locally these come from `docker compose up -d` against this repo's own compose
# file. Skip when that stack (DATABASE_URL) isn't up.
if [ -n "${DATABASE_URL:-}" ]; then
  step "Run Integration Tests"
  RUN_INTEGRATION_TESTS=1 env -u PYTHONPATH uv run pytest tests -q -m integration
  pytest_rc=$?
  # Exit 5 = "no tests collected": expected until the first integration test exists.
  # Delete this tolerance once you have one.
  if [ "$pytest_rc" -ne 0 ] && [ "$pytest_rc" -ne 5 ]; then
    echo "::error::Run Integration Tests failed"
    failed=$((failed + 1))
  fi
else
  skip "Run Integration Tests" "DATABASE_URL not set — start this repo's docker compose stack first"
fi

# ── Summary ──
printf '\n\033[1m── Summary\033[0m\n'
if [ -n "$skipped" ]; then
  printf 'Checks that did NOT run:%s\n\n' "$skipped"
fi

if [ "$failed" -gt 0 ]; then
  printf '::error::%d check(s) failed.\n' "$failed"
  exit 1
fi

if [ -n "$skipped" ]; then
  if [ "$STRICT" -eq 1 ]; then
    echo "::error::gate was partial and strict mode is on."
    exit 1
  fi
  echo "All checks that ran passed, but the gate was PARTIAL — see the list above."
  exit 0
fi

echo "Full gate passed."
