---
paths:
  - '**/*.py'
  - '**/*.pyi'
---

# No `Any` (Python)

When `AGENTS.md` carries a numbered no-`Any` rule, it says the same; this file is what loads while
you edit Python.

- No explicit `typing.Any`, in annotations or anywhere else. Enforced by ruff `TID251` (the name is
  banned) and `ANN401`. mypy's `disallow_any_explicit` stays off on purpose: it flags the
  `__init__` the Pydantic plugin generates for every model.
- JSON you build is `dict[str, object]` or a `TypedDict`; JSON you receive is validated into a
  Pydantic model or read through `TypeAdapter`, never indexed as `Any`.
- `object` plus `isinstance` narrowing replaces `Any` for values of unknown shape. A vendor SDK
  that returns `Any` is narrowed right where it is called.
