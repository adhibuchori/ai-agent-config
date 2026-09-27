"""Names vulture reports as unused that something outside `src/` reads.

Each entry is an attribute access vulture counts as a use. The imports are real, so mypy fails the
moment an entry names something that no longer exists. Never add real dead code here: delete it.
Every entry says who reads it (.claude/rules/python/dead-code.md).
"""

# A bare attribute access is how a vulture whitelist marks a use, so B018 does not apply here.
# ruff: noqa: B018

import logging

from fastapi import FastAPI

# Framework-read: FastAPI calls `app.openapi()`, logging writes to `Logger.handlers`.
FastAPI.openapi
logging.Logger.handlers

# Add your own below, grouped by who reads them. For example:
#
# from app.modules.widgets.schemas import WidgetSchema
#
# # Response models: FastAPI serialises every field into the JSON body.
# WidgetSchema.name
#
# from app.db.models import Widget
#
# # ORM columns define the table even when no Python code reads them.
# Widget.created_at
