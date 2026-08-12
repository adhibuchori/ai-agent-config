<!-- Source of Truth: _workflow-source/ -->
<!-- Sync: bash scripts/sync-workflows.sh -->

| Category | Command             | When to Use                            | Example                                |
| -------- | ------------------- | -------------------------------------- | -------------------------------------- |
| Quality  | /review             | Before every commit                    | /review                                |
| Safety   | /checkpoint         | Before risky changes                   | /checkpoint before schema refactor     |
| Session  | /checkpoint-summary | Every 90min / 10 tasks                 | /checkpoint-summary chat-endpoint      |
| Session  | /learn-session      | End of a session that taught something | /learn-session                         |
| Release  | /create-pr          | Generate + create PR                   | /create-pr                             |
| Release  | /resolve-pr-review  | Triage & apply PR review               | /resolve-pr-review 42                  |
| Release  | /merge-pr           | Check readiness & merge                | /merge-pr 42                           |
| Release  | /branch-cleanup     | After a promotion lands                | /branch-cleanup                        |
