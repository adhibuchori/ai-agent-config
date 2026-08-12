#!/usr/bin/env bash
# Blocks dangerous commands before execution.

COMMAND="${CLAUDE_TOOL_INPUT_COMMAND:-}"

# Block rm -rf on protected paths
if grep -qE 'rm\s+-rf' <<< "$COMMAND"; then
  if grep -qE '(src/|\.claude/|AGENTS\.md|SSOT\.md|CLAUDE\.md|/\s*$|\.\s*$|\.\.\s*$|\*)' <<< "$COMMAND"; then
    echo "[safety] BLOCKED: rm -rf on protected path: $COMMAND" >&2
    exit 1
  fi
fi

# Block git push to dev/prod (this fleet promotes via internal/{scope} -> dev -> prod PRs)
if grep -qE 'git\s+push\s+origin\s+(dev|prod|main|master)\b' <<< "$COMMAND"; then
  echo "[safety] BLOCKED: git push directly to dev/prod is not allowed. Use a internal/{scope} branch." >&2
  exit 1
fi

# Block shell redirection writes to .env files
if grep -qE '>\s*\.env' <<< "$COMMAND"; then
  echo "[safety] BLOCKED: writing to .env files via shell redirection." >&2
  exit 1
fi

exit 0
