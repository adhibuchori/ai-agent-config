---
description: Fetches a PR's review comments, triages them against project rules, applies what holds up, replies in each review thread, and resolves the threads it settled.
---

<!-- Command: /resolve-pr-review [PR] -->
<!-- Source: _workflow-source/resolve-pr-review.md -->

# /resolve-pr-review — PR Review Resolver

## Step 1: Fetch

```bash
gh pr view {PR} --repo {OWNER/REPO} --json title,url,headRefName,additions,deletions,changedFiles
gh api "repos/{OWNER}/{REPO}/pulls/{PR}/comments" --paginate
gh api "repos/{OWNER}/{REPO}/pulls/{PR}/reviews" --paginate
```

With RTK installed, run the two `gh api` calls as `rtk proxy gh api …`: its rewrite can shorten the
JSON, and every comment's `id` and body is needed. If a reviewer was named, filter to that user. If
there are no comments, say so and stop.

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

Apply in priority order, then re-run `/check-fix` — all gates must pass — and push the fixes.

## Step 5: Reply In Every Thread — Always

Each inline comment gets its answer in its own thread, applied or declined:

```bash
gh api "repos/{OWNER}/{REPO}/pulls/{PR}/comments/{COMMENT_ID}/replies" -f body="<applied in <sha> | declined, and why>"
```

A review summary that has no inline thread gets one PR comment covering it:

```bash
gh pr comment {PR} --repo {OWNER/REPO} --body "<what was applied, what was declined, and why>"
```

Reply even when nothing was applied. A declined suggestion needs a stated reason; silence reads
as an oversight and the next reviewer raises it again.

## Step 6: Resolve What Is Settled

`bash scripts/ops/pr-ready.sh {PR}` counts every unresolved thread as blocking. Resolve a thread
once its fix is pushed or its decline is explained; leave one open only when it waits on the
reviewer, and say which.

```bash
gh api graphql -F owner={OWNER} -F repo={REPO} -F pr={PR} -f query='query($owner: String!, $repo: String!, $pr: Int!) { repository(owner: $owner, name: $repo) { pullRequest(number: $pr) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { databaseId } } } } } } }'
gh api graphql -F thread=<thread id> -f query='mutation($thread: ID!) { resolveReviewThread(input: { threadId: $thread }) { thread { isResolved } } }'
```

The first query maps each thread to the `databaseId` of its first comment, the `{COMMENT_ID}` of
Step 5.
