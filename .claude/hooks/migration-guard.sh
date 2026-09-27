#!/usr/bin/env bash
# PreToolUse(Write|Edit|MultiEdit and Serena's writes): generated migrations change only through
# their generator (drizzle-kit, Alembic autogenerate). The folders are migrationsDirs in
# .claude/agent-config.json; a folder the repo does not have guards nothing, so the hook turns
# itself off in a repo without migrations. Optional: wire it in backends and data pipelines.
#
# A symlink is judged as named and as the file it points to, since a write lands there.
#
# Fails closed: a payload it cannot read, a folder list it cannot load, a symlink it cannot
# follow, or a replace_in_files whose reach it cannot work out (no python3, or over 5 s) refuses
# the call.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
hook_start guard "[migration-guard]"

# migrationsDirs of the repo ROOT names. A key that neither python3 nor jq can read refuses the
# call rather than guarding nothing.
dirs() {
  local list d
  list="$(hook_config migrationsDirs)" || hook_fail "migrationsDirs could not be read."
  DIRS=()
  DIRS_ROOT="$ROOT"
  while IFS= read -r d; do
    d="${d%/}"
    [[ -n "$d" ]] && DIRS+=("$d")
  done <<<"$list"
}
dirs

# replace_in_files names a folder, or the whole project, rather than the file it rewrites. A folder
# that does not exist holds no file, so it never matches.
if [[ ${#DIRS[@]} -gt 0 ]] && hook_scope_hits "${DIRS[@]}"; then
  block "[migration-guard] BLOCKED: this replace_in_files reaches generated migrations (migrationsDirs)." \
    "Narrow relative_path, or add paths_exclude_glob, so they are not touched."
fi

# $1, an absolute path: refused when it is a generated migration of its repo. Workspace mode: a
# file in another repo follows that repo's configuration.
judge() {
  local rel d
  hook_adopt_repo "$1"
  in_project "$1" || return 0
  rel="${1#"$ROOT"/}"
  [[ "$ROOT" == "$DIRS_ROOT" ]] || dirs
  for d in ${DIRS[@]+"${DIRS[@]}"}; do
    [[ -d "$d" && "$rel" == "$d"/* ]] || continue
    if [[ "$rel" == *.py && -f alembic.ini ]]; then
      block "[migration-guard] BLOCKED: $rel is an Alembic revision. Change the models, run" \
        "'alembic revision --autogenerate -m \"<description>\"' (through the project's runner), then review the generated revision."
    elif compgen -G 'drizzle.config.*' >/dev/null; then
      block "[migration-guard] BLOCKED: $rel is drizzle-kit output. Change the schema and run drizzle-kit generate" \
        "(through the project's script); a data fix goes in a new custom migration."
    else
      block "[migration-guard] BLOCKED: $rel is a generated migration ($d in migrationsDirs)." \
        "Generate a new migration with the project's tool instead of editing this one."
    fi
  done
}

FILE="$(hook_file)"
[[ -n "$FILE" ]] || exit 0
SESSION_ROOT="$ROOT"
judge "$FILE"
# A write to a symlink lands in the file it points to, a dangling one included: that is judged too.
TARGET="$(hook_target "$FILE")"
[[ -n "$TARGET" ]] || hook_fail "$FILE is a symbolic link that could not be followed (no realpath, readlink or python3)."
if [[ "$TARGET" != "$FILE" ]]; then
  ROOT="$SESSION_ROOT"
  cd "$ROOT" || hook_fail "the project folder $ROOT cannot be entered."
  judge "$TARGET"
fi

exit 0
