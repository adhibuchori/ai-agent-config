---
description: Create a safety commit of all current changes with an ISO timestamp.
---

<!-- Command: /checkpoint -->
<!-- Source: _workflow-source/checkpoint.md -->

# /checkpoint — Safety Commit

Stage all current changes.
Commit with message: `chore: checkpoint — {description} [{ISO timestamp}]`
Output: commit hash and the files staged.

Use before any change that would be painful to unwind by hand.
