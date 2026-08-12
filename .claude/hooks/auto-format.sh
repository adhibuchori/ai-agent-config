#!/usr/bin/env bash
# Runs ruff format on modified Python files after every write. Never blocks.

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
      run_capped 10 $RUFF format "$FILE" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0
