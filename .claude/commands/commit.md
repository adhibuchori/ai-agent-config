---
description: Runs the quality gates, inspects the staged change, and drafts a commit message in this repo's format. Stages by name and drafts only; never commits or pushes.
---

<!-- Command: /commit -->
<!-- Source: _workflow-source/commit.md -->

# /commit — Quality Gate & Commit Message

1. **Quality gate**: run `/check-fix` first. Do not proceed from a broken state.

2. **Inspect**: `git status --short` and `git diff --staged`, read whole (with RTK installed,
   `rtk proxy git status --short` and `rtk proxy git diff --staged`: its rewrite condenses both).
   - **Never stage**: an env file other than the `.env.<target>.example` templates, `.coverage`,
     anything under `.venv/`.
   - `.claude/settings.json` is tracked, and a change to it is its own commit, together with the
     hooks it wires; never fold one into an unrelated change.

3. **Stage explicitly**, by name: `git add -- <paths>`. Staging everything is `/ship`'s alone,
   because only `/ship` runs the guards that make it safe (CLAUDE.md § Commit Format). Name any
   changed file you did not write and leave it out.

4. **Draft the message**:

   ```
   type: description

   [Optional body: what changed and why, wrapped at 72 characters]
   ```

   - **Types**: `feat` · `fix` · `refactor` · `chore` · `docs` · `style` · `perf` · `test`
   - Lowercase, imperative, no trailing period (CLAUDE.md § Commit Format)
   - Add whatever attribution trailer your harness or team requires; never hard-code a model name.

Output the drafted message and the pathspec it covers. Do not run the commit itself.
