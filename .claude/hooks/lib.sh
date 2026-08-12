#!/usr/bin/env bash
# Shared helpers for the hooks in this directory. Source it, don't execute it.

# Resolves a tool from the project venv first. Python tooling here is installed by
# `uv sync` into .venv/ and is NOT on PATH, so a bare `command -v ruff` guard — the
# idiom the TS repos use for oxfmt/oxlint — always misses and turns the hook into a
# silent no-op. Falls back to `uv run`, then to PATH.
resolve_tool() {
  local tool="$1" root
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

  if [[ -x "$root/.venv/bin/$tool" ]]; then
    printf '%s' "$root/.venv/bin/$tool"
    return 0
  fi
  if command -v uv &>/dev/null; then
    printf 'uv run %s' "$tool"
    return 0
  fi
  if command -v "$tool" &>/dev/null; then
    printf '%s' "$tool"
    return 0
  fi
  return 1
}

# Runs a command under a timeout when one is available. macOS ships no `timeout`
# and no `gtimeout` unless coreutils is installed, and `timeout 5 x || true`
# swallows the resulting 127 — which is why the TS repos' format/lint hooks do
# nothing on this machine. Degrade to running bare rather than silently skipping.
run_capped() {
  local secs="$1"; shift
  local to
  to="$(command -v timeout || command -v gtimeout || true)"

  if [[ -n "$to" ]]; then
    "$to" "$secs" "$@"
  else
    "$@"
  fi
}
