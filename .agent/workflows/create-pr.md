---
description: Detects the branch context, runs the gates, drafts a PR title and a body from the repo's PR template, and opens the PR into dev after confirmation.
---

<!-- Command: /create-pr -->
<!-- Source: _workflow-source/create-pr.md -->

# /create-pr — Create Pull Request

## Step 0: Detect Context

```bash
git branch --show-current
git log dev..HEAD --oneline
git diff dev..HEAD --stat
```

With RTK installed, run the `git log` and `git diff` lines as `rtk proxy git …`: its rewrite drops
merge commits from `--oneline` and reshapes `--stat`, and the PR body lists both.

The base branch is **`dev`**, never `main` — this repo promotes `internal/{scope}` → `dev` →
`prod`. A pull request into `prod` is `/promote`'s job. Stop when the current branch is `dev`,
`prod` or the default branch: a pull request starts from a work branch.

## Step 1: Gate First

Run `bash scripts/check/gates.sh`. Do not open a PR from a red gate: CI runs the same list and
fails it again, a runner's minutes later.

## Step 2: Collect What Is Missing

Ticket ID (optional), a one-sentence description, any model, provider or env change, and whether a
companion docs repo needs its own pull request. Ask for everything missing in one question.

## Step 3: Draft

**Title:** `type: description` — the types in CLAUDE.md § Commit Format, lowercase after the colon,
imperative, under 70 characters.

**Body:** `.github/PULL_REQUEST_TEMPLATE/dev.md`, filled in. Write Summary and How to Verify, tick
only the checklist lines that hold for this diff, and delete the conditional blocks that do not
apply. Do not add the gate's checks back in: the Quality Gate is the list.

## Step 4: Confirm

Show title and body in a fenced block. Ask whether they are correct before creating; on "no", ask
what to change, redraft, and show it again.

## Step 5: Create

```bash
gh pr create --title "<title>" --body "<body>" --base dev
```

Output the PR URL.
