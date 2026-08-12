---
description: Summarise the session: what was done, what is pending, and what comes next.
---

<!-- Command: /checkpoint-summary -->
<!-- Source: _workflow-source/checkpoint-summary.md -->

# /checkpoint-summary — Session Summary

Run every 90 minutes or every 10 tasks. Records **what happened**; for **what should change next
time**, use `/learn-session` instead.

1. COLLECT: files modified, tasks completed, decisions made, problems hit
2. ACTIVE SUMMARY (≤300 tokens): print for the user — branch, what was done, key decisions,
   files changed, what is next
3. FULL LOG: save to `.claude/session-logs/[YYYY-MM-DD]-[domain].md`
4. HAND OFF: note anything a fresh session would need in order to continue
