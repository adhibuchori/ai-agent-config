## Description

<!-- What is being promoted. Link the dev PR. -->

## Commits

<!-- Paste `git log origin/prod..origin/dev` so the scope is visible without
     reading the diff. -->

## Expected Diff Noise

This PR's diff will look far larger than the commit list above — `strip-ai-on-pr.yml`
removes `.claude/`, `.agent/`, `AGENTS.md`, `CLAUDE.md`, `SSOT.md` and related AI
config from `prod` on every merge, so those files reappear as "new" on every single
promotion. This is expected noise, not a sign of scope creep — do not treat a large
file count as a red flag on its own.

## Checklist

- [ ] Quality Gate passed on the dev PR (this promotion PR does not re-run it)
- [ ] `git merge --no-commit --no-ff origin/dev` dry run against `prod` is clean
- [ ] Any behaviour or API-contract change is called out above, not buried in the
      commit list
- [ ] Deployment confirmed after merge — a green Actions run is not proof the
      deploy happened
