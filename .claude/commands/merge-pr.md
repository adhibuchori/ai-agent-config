---
description: Check PR readiness, confirm strategy, and merge.
---

<!-- Command: /merge-pr -->
<!-- Source: _workflow-source/merge-pr.md -->

# /merge-pr — Merge Pull Request

## Step 1: Assess Readiness

```bash
gh pr view {PR} --repo {OWNER/REPO} \
  --json title,url,state,headRefName,baseRefName,mergeable,reviewDecision,statusCheckRollup
```

Block and report if: the PR is not `OPEN`, `mergeable` is `CONFLICTING`, the review decision is
`CHANGES_REQUESTED`, or any required check is failing. A skipped or neutral check is not a pass —
name it as what it is.

## Step 2: Confirm Strategy

**Squash** for a feature branch into `dev`. **Merge commit** for a `dev → prod` promotion, so the
promotion stays legible in history.

## Step 3: Check The Head Branch Before Merging

```bash
gh pr view {PR} --json headRefName
```

- Head is `internal/…` → `--delete-branch` is safe and expected.
- Head is **`dev`**, `prod`, or any long-lived branch → merge **without** `--delete-branch`, no
  exceptions. On a promotion PR the head is `dev` itself; deleting it removes the shared branch
  from the remote and breaks the `strip-ai-on-pr.yml` back-merge. This has happened.

## Step 4: Merge

```bash
gh pr merge {PR} --repo {OWNER/REPO} --squash --delete-branch    # internal/… → dev
gh pr merge {PR} --repo {OWNER/REPO} --merge                     # dev → prod
```

Output the merge result and URL. For a promotion, continue with `/promote` Phase 3 to verify the
deployment actually happened.
