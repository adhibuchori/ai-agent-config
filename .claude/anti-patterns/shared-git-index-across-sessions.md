# One checkout, several sessions, one `.git/index`

**Applies to:** any repo worked by more than one agent session at a time
**Status:** Permanent (git design — the index belongs to the worktree, not to the process)

## Symptom

You stage two files, then `git diff --cached` shows six. Or a commit named for one concern lands
carrying someone else's half-finished work. Or `git status` reports a file staged while
`git diff --cached` comes back empty a moment later.

Each session that hits this tends to conclude the tooling is lying — a pre-commit hook secretly
re-staging, or an output wrapper returning stale reads. Test that before arguing it: a hook that
only runs checks never touches the index, and two reads taken seconds apart can both be correct if
another session committed in between.

## Root cause

`.git/index` belongs to the **worktree**, not to the process. Sessions sharing a checkout share one
index. Every `git add` from every session accumulates in the same place, so `git commit` — which
commits *the index* — sweeps up whatever the others put there.

## Fix

**Pass a pathspec to `git commit`.** It commits those paths from the working tree and leaves the
rest of the index alone, so nothing another session staged can ride along:

```bash
uv run ruff format <paths>                # format only your files, never the whole tree
git add <any new files>                   # a pathspec commit only takes paths git already tracks
git commit -F message.txt -- <paths>
git show --stat HEAD                      # then read the file list
```

Two caveats, both silent:

- A pathspec commits only paths git already tracks. A brand-new file still needs `git add` first,
  or the commit lands without it.
- A pathspec commit takes the working tree as it was when the command started. Keep the commit
  hook read-only — a check that fails, never a formatter that rewrites — so a fix cannot land in
  the tree but miss the commit. Format your own paths before committing.

The last line of the block is the one that binds: everything above it reports intent, and only the
committed file list reports the outcome. `.claude/hooks/post-commit.sh` does it for you: after a
commit it shows what landed and warns about any path the pathspec did not name. Read it before
pushing; after a push the mistake is no longer cheap to fix.

## Scope

Any concurrent-session work on one checkout. It does **not** apply to git worktrees — each has its
own index, which is the structural fix when sessions need to run long and independently.

`git-apply-check-passes-then-deletes.md` has the same shape: a guard that passes up front while
the outcome is still wrong. In both, the only reliable check is reading the state **after** the
action.
