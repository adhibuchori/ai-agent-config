#!/usr/bin/env bash
# Runs the checks quality-gate.yml runs, for promotions that cannot use CI.
# Usage: quality-gate.sh [base-ref]   default origin/dev. See README § CI/CD.
set -uo pipefail

cd "$(dirname "$0")/../.."

BASE="${1:-origin/dev}"
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

run "Install Dependencies" uv sync --frozen
run "Format & Lint" bash -c "uv run ruff format --check src tests && uv run ruff check src tests"
run "Type Check" uv run mypy src
run "Import Boundaries" uv run lint-imports
run "Unit Tests" uv run pytest tests -q --cov
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

step "Check .env Not Committed"
if git diff "$BASE"...HEAD --name-only | grep -E "^\.env(\.|$)" | grep -qvE "^\.env(\.[a-z]+)?\.example$"; then
  echo "::error::.env file committed"
  failed=$((failed + 1))
else
  echo "Clean"
fi

# Inserting a rule renumbers AGENTS.md and silently breaks every citation.
step "AI Config Rule Drift Check"
if [ ! -f AGENTS.md ] || [ ! -d .claude ]; then
  echo "AGENTS.md or .claude/ not present on this branch - skipping"
else
ai_stale=0
for f in *.md; do
  [ -f "$f" ] || continue
  for n in $(grep -oE "Rule [0-9]+" "$f" | grep -oE "[0-9]+" | sort -u); do
    if ! grep -qE "Rule $n[^0-9]" AGENTS.md; then
      echo "::error file=$f::cites Rule $n, which does not exist in AGENTS.md"
      ai_stale=1
    fi
  done
done
if [ "$ai_stale" -ne 0 ]; then
  failed=$((failed + 1))
else
  echo "All cited rule numbers exist in AGENTS.md"
fi
fi

run "Comment Block Length Check" bash .github/scripts/check-comment-blocks.sh

# A stale copy under .claude/commands/ still reads as valid, and INDEX.md is what an agent
# consults to discover the commands at all. Skipped on prod, where the strip removed the source.
step "Workflow Mirror Drift Check"
if [ ! -d _workflow-source ] || [ ! -f scripts/sync-workflows.sh ]; then
  echo "_workflow-source/ not present on this branch - skipping"
elif ! bash scripts/sync-workflows.sh --check; then
  echo "::error::workflow mirror or INDEX.md has drifted"
  failed=$((failed + 1))
fi

run "Production Build" docker build -t <repo-name> .

# ── Pipeline extras (optional) ──
# This gate models a request-serving FastAPI service, not a migration-owning
# pipeline/worker. If your repo owns a schema (Alembic revisions) or generates
# committed docs from code, add two more steps here — do not bolt them onto
# the ones above:
#
#   run "Migration Drift Check" bash -c "uv run alembic upgrade head && uv run alembic check"
#   run "Docs Drift Check" bash -c "uv run python scripts/generate_docs.py && git diff --exit-code docs/"
#
# Gate "Migration Drift Check" on the same DATABASE_URL check below, same as
# "Run Integration Tests" — a fresh clone with no database running should skip,
# not fail. See .claude/rules/backend/pipeline.example.md before adding either.

# Locally these come from `docker compose up -d` against this repo's own compose
# file. Skip when that stack (DATABASE_URL) isn't up.
if [ -n "${DATABASE_URL:-}" ]; then
  step "Run Integration Tests"
  RUN_INTEGRATION_TESTS=1 uv run pytest tests -q -m integration
  pytest_rc=$?
  # Exit code 5 = "no tests collected" — expected on a fresh template with no
  # integration tests written yet, not a failure. Delete this tolerance once
  # you have at least one.
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
