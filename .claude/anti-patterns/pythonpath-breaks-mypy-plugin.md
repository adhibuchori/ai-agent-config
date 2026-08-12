# Inherited `PYTHONPATH` breaks mypy's pydantic plugin

**Applies to:** Any repo running `mypy` with `plugins = ["pydantic.mypy"]` inside a harness or CI
runner that may export its own `PYTHONPATH`
**Discovered:** verified in the source fleet this template is drawn from
**Status:** Known trap — no code fix, only a diagnostic habit

## Symptom

```
pyproject.toml:1: error: Error importing plugin "pydantic.mypy":
No module named 'pydantic_core._pydantic_core'
```

Looks like a broken venv. `uv sync` reports success, `ruff` runs fine (it's a standalone binary
with no plugin loading), and `pydantic_core` is clearly installed if you check `.venv/`.

## Root Cause

Some agent harnesses or CI wrappers export a `PYTHONPATH` pointing at their own interpreter's
`site-packages`. That directory precedes `.venv/` on `sys.path`, so `pydantic_core/__init__.py`
gets imported from *there* instead — but its compiled `_pydantic_core*.so` extension was built for
a different Python version and is invisible to the interpreter actually running `mypy`. The pure-
Python `__init__.py` half-imports; the compiled half does not exist from this interpreter's point
of view.

`ruff` is unaffected because it never loads Python plugins — this bites `mypy` specifically, and
only when a pydantic (or similarly-compiled) mypy plugin is configured.

## Fix

Check `PYTHONPATH` before assuming the venv is broken:

```bash
echo "$PYTHONPATH"                 # should be empty when working in this repo
env -u PYTHONPATH uv run mypy src  # succeeds if this was the cause
```

If a wrapper script or harness needs `PYTHONPATH` for its own purposes, unset it specifically
around the `mypy` invocation rather than working around it in `pyproject.toml` — the plugin
mechanism is correct; the inherited environment variable is the actual defect.

## When to revisit

If this stops reproducing after a mypy or pydantic upgrade that changes how the plugin resolves
its compiled extension, delete this file.
