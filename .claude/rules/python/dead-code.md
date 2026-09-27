---
paths:
  - '**/*.py'
  - 'pyproject.toml'
---

# Dead code (Python)

Blocking in pre-commit and the Quality Gate.

- vulture reports unused functions, classes, attributes and unreachable code; deptry reports
  unused, missing and transitive dependencies. Both are configured in `pyproject.toml`.
- A finding is fixed, not silenced. Unused anywhere: delete it. Reached by a convention or a config
  the tool cannot follow (a framework calls it by name, or a decorator registers it): add it to
  vulture's whitelist, `ignore_names` or `ignore_decorators`, with a comment saying which. A
  dependency nothing imports but the runtime needs (a server, a database driver) goes in deptry's
  `per_rule_ignores` with a comment saying who loads it. Generated or vendored: exclude it by its
  narrowest path.
- Never whitelist a name or ignore a dependency because it "might be used later".
