# `git apply --check` passes, then the patch deletes the files

**Applies to:** any patch built with `git diff --no-index`
**Status:** Permanent (how `git diff --no-index` writes its headers)

## Symptom

`git apply --check patch` exits 0. `git apply patch` reports nothing wrong — and then `git status`
shows:

```
 D AGENTS.md
 D SSOT.md
?? var/
```

The files you meant to edit are gone, and copies of them appear under a folder named after the
machine's temp path.

## Root cause

`git diff --no-index a b` writes the **literal paths it was given** into the diff header. Build a
patch by copying a file to a temp folder and diffing against it, and you get:

```
--- a/SSOT.md
+++ b/var/folders/.../T/tmpXXXX/SSOT.md
```

`git apply` reads that as one instruction: delete `SSOT.md`, create `var/folders/.../SSOT.md`. It
is not a malformed patch — it is a valid patch for a rename you did not intend, so nothing warns
you. Rewriting the `a/` side but missing the long `b/` side is easy, because it scrolls off.

## Why `--check` does not save you

`git apply --check` answers "can this patch be applied cleanly?", not "is this the change you
meant?" A delete-and-recreate applies perfectly cleanly. **A green `--check` is a conflict test,
not a safety net.** That is the whole trap: the natural precaution is taken, it passes, and the
outcome is still destructive.

## What to do

1. **Do not build patches with `git diff --no-index`.** Edit the target file directly, asserting
   first that the anchor text exists exactly once. It is simpler, and it cannot silently become a
   rename.
2. If you must apply a patch, read its `+++ b/` lines first. Every one should be a repo-relative
   path.
3. Whatever the route, run `git status` **after** applying and read it. The post-state is the
   confirmation; a passing `--check` is not.

## Recovery, if it already happened

Nothing is lost when the files were tracked and committed:

```bash
git checkout -- SSOT.md AGENTS.md                         # restore them from HEAD
git clean -fd -- var                                      # scoped: only the stray tree
git diff --quiet HEAD -- SSOT.md AGENTS.md && echo restored
```

Scope the `clean` to the stray folder. A bare `git clean -fd` also removes untracked work that
belongs to someone else, which in a checkout shared by several sessions is the more expensive
mistake of the two.
