<!-- Source of Truth: _workflow-source/ -->
<!-- Sync: bash scripts/sync/workflows.sh -->

| Category | Command             | When to Use                            | Example                                    |
| -------- | ------------------- | -------------------------------------- | ------------------------------------------ |
| Planning | /plan               | Before every feature                   | /plan stream the chat completion endpoint  |
| Quality  | /check-fix          | Gates fail: fix what they report       | /check-fix                                 |
| Quality  | /review             | Before every commit                    | /review                                    |
| Quality  | /rca                | Bug needs its root cause               | /rca empty answer on long prompts          |
| Safety   | /checkpoint         | Before risky changes                   | /checkpoint before schema refactor         |
| Session  | /checkpoint-summary | Every 90min / 10 tasks                 | /checkpoint-summary chat-endpoint          |
| Session  | /learn-session      | End of a session that taught something | /learn-session                             |
| Workflow | /commit             | After work is done                     | /commit                                    |
| Workflow | /ship               | Review + fix + commit + push           | /ship                                      |
| Release  | /create-pr          | Open the PR into dev                   | /create-pr                                 |
| Release  | /resolve-pr-review  | Triage & apply PR review               | /resolve-pr-review 42                      |
| Release  | /merge-pr           | Check readiness & merge                | /merge-pr 42                               |
| Release  | /promote            | Promote dev to prod through a PR       | /promote                                   |
| Release  | /promote-deploy     | Promote with CI down (no PR)           | /promote-deploy                            |
| Release  | /branch-cleanup     | After a promotion lands                | /branch-cleanup                            |
