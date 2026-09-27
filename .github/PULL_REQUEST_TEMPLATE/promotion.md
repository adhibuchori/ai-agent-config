## Promotion: dev → prod

<!-- Filled in from `git log origin/prod..origin/dev`. Re-check the commit list against that
     range before editing it by hand. -->

### Commits Being Promoted

<!-- One line per commit: short SHA — subject. -->

### Local Merge Verification

- [ ] Ran `git merge --no-commit --no-ff origin/dev` locally against `prod` before
      opening this PR
- Result: <!-- clean / conflicts found and how they were resolved / not run -->

## Expected Diff Noise

This PR's diff looks larger than the commit list above. `strip-ai-on-pr.yml` removes the AI
configuration from `prod` on every merge; the exact set is `STRIP_PATHS` in
`.github/scripts/strip-paths.sh`, and every path in it reappears as "new" on every promotion. That
is expected noise, not scope creep.

## Before Merging

The Quality Gate runs on this PR too; the checks below are what it cannot see.

- [ ] Every behaviour or API-contract change is called out above, not buried in the commit list
- [ ] The production env matches `.env.production.example`, and any migration this promotion
      needs is already live (`/promote` Phase 2)

## Post-Merge Checks

A green Actions run is not proof the deploy happened.

- [ ] `ci-cd.yml` fired, the deploy platform accepted the webhook, and a deployment was created
      after the merge
- [ ] `GET /health` on the deployed instance answers
- [ ] One real request answered end to end: `/health` proves the process is up, not that a
      provider key, the vector store or the model is reachable
- [ ] If this promotion carried a `models.py` change, the schema owner's matching migration is
      already live in production

<!-- A worker with no HTTP surface: replace the two request checks with "the worker is running and
     connected to its queue" and "one job processed end to end after the deploy". -->
