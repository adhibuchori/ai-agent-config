# Inherited `PYTHONPATH` breaks mypy's pydantic plugin

**Applies to:** any repo running `mypy` with `plugins = ["pydantic.mypy"]` (or pytest) inside a
harness or CI runner that may export its own `PYTHONPATH`
**Status:** Known trap — no code fix, only a habit: run Python tools with `env -u PYTHONPATH`

## Symptom

```
pyproject.toml:1: error: Error importing plugin "pydantic.mypy":
No module named 'pydantic_core._pydantic_core'
```

It looks like a broken venv. `uv sync` reports success, `ruff` runs fine (it is a standalone binary
with no plugin loading), and `pydantic_core` is clearly installed if you look in `.venv/`.

## Root cause

Some agent harnesses and CI wrappers export a `PYTHONPATH` pointing at their own interpreter's
`site-packages`. That directory precedes `.venv/` on `sys.path`, so `pydantic_core/__init__.py` is
imported from *there*, while its compiled `_pydantic_core*.so` was built for a different Python
version and is invisible to the interpreter running `mypy`. The pure-Python half imports; the
compiled half does not exist from this interpreter's point of view.

`ruff` is unaffected because it never loads Python plugins. mypy's plugin is where it shows first,
but pytest can import the wrong copy of a package the same way, with a subtler failure.

## Fix

Check `PYTHONPATH` before assuming the venv is broken, and run the Python tools without it:

```bash
echo "$PYTHONPATH"                               # should be empty when working in this repo
env -u PYTHONPATH uv run mypy .                  # succeeds if this was the cause
env -u PYTHONPATH uv run pytest tests -q --cov   # same for the suite
```

Run them the same way in `.pre-commit-config.yaml` and the gate list. If a wrapper needs
`PYTHONPATH` for its own purposes, unset it around these invocations rather than working around it
in `pyproject.toml`: the plugin mechanism is correct, and the inherited variable is the defect.

## When to revisit

If this stops reproducing after a mypy or pydantic upgrade that changes how the plugin resolves its
compiled extension, delete this file.
