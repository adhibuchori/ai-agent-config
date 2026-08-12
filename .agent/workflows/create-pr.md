---
description: Detect branch context, draft a PR title and description, and open the PR.
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

The base branch is **`dev`**, never `main` — this repo promotes `internal/{scope}` → `dev` →
`prod`.

## Step 1: Collect What Is Missing

Ticket ID (optional), one-sentence feature description, any breaking change or migration note.

## Step 2: Draft

**Title:** `feat(scope): [TICKET-ID] {Description In Title Case}` — under 70 characters.

**Description:**

```
**📝 Description**
[What problem does this solve?]

**🛠️ Technical Implementation**
[Layers touched, key files, architectural decisions.]

**✅ Testing**
[How this was verified.]

**📋 Checklist**
- [ ] Format + lint passed (`uv run ruff format --check src tests && uv run ruff check src tests`)
- [ ] Type check passed (`uv run mypy src`)
- [ ] Import boundaries passed (`uv run lint-imports`)
- [ ] Production build succeeds (`docker build -t <repo-name> .`)
- [ ] Migration generated and committed, if this repo owns its schema and it changed
- [ ] Every new module added to all three `[[tool.importlinter.contracts]]` blocks in `pyproject.toml`
```

## Step 3: Confirm

Show title and body. Ask whether they are correct before creating.

## Step 4: Create

```bash
gh pr create --title "<title>" --body "<body>" --base dev
```

Output the PR URL.
