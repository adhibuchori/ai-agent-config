---
description: Fetch PR review comments, triage them against project rules, and apply what holds up.
---

<!-- Command: /resolve-pr-review -->
<!-- Source: _workflow-source/resolve-pr-review.md -->

# /resolve-pr-review — PR Review Resolver

## Step 1: Fetch

```bash
gh pr view {PR} --repo {OWNER/REPO} --json title,url,headRefName,additions,deletions,changedFiles
gh api "repos/{OWNER}/{REPO}/pulls/{PR}/comments" --paginate
gh api "repos/{OWNER}/{REPO}/pulls/{PR}/reviews" --paginate
```

If a reviewer was named, filter to that user. If there are no comments, say so and stop.

## Step 2: Judge Each Against Project Rules

Cross-check every suggestion against `AGENTS.md`. A reviewer bot does not know this repo's
conventions and is regularly confident and wrong.

- Contradicts a rule → `⚠ Conflicts with Rule {N}`, recommend declining
- Supports a rule → `✓ Aligns with Rule {N}`
- Neither → `—`, judge on merit

## Step 3: Triage Table

| ID | File:Line | Reviewer | Type | Rule | Summary |
| :-- | :-- | :-- | :-- | :-- | :-- |

Ask which to apply. Order the accepted ones: security and bugs first, then correctness, then
maintainability.

## Step 4: Apply and Verify

Apply in priority order, then re-run `/check-fix` — all gates must pass.

## Step 5: Reply On The PR — Always

```bash
gh pr comment {PR} --repo {OWNER/REPO} --body "<what was applied, what was declined, and why>"
```

Reply even when nothing was applied. A declined suggestion needs a stated reason; silence reads
as an oversight and the next reviewer raises it again.
