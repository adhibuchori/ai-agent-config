#!/usr/bin/env bash
# Runs ruff check on modified Python files after every write. Advisory only —
# CI's quality-gate is the blocking equivalent, so this never exits non-zero.
# mypy is deliberately NOT wired here: it is a whole-project check and slow per
# keystroke. CI owns type-checking (AGENTS.md §G Rule 24).

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

FILE="${CLAUDE_TOOL_INPUT_FILE_PATH:-}"

if [[ -z "$FILE" ]] || [[ ! -f "$FILE" ]]; then
  exit 0
fi

case "${FILE##*.}" in
  py)
    if RUFF="$(resolve_tool ruff)"; then
      # shellcheck disable=SC2086 -- RUFF may be "uv run ruff", word splitting intended
      run_capped 15 $RUFF check "$FILE" 2>&1 || true
    fi
    ;;
  json)
    if command -v python3 &>/dev/null; then
      python3 -c "import json,sys; json.load(sys.stdin)" < "$FILE" 2>/dev/null \
        && echo "[auto-lint] $FILE JSON valid" \
        || echo "[auto-lint] WARNING: $FILE has JSON syntax errors" >&2
    fi
    ;;
esac

exit 0
