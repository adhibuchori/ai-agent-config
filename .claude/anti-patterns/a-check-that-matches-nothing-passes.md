# A check whose scanner matches nothing reports success

**Applies to:** any check script, leak scan or grep gate — `scripts/check/*`, a CI step, a one-off
audit you run by hand
**Status:** Permanent (a property of every pattern-based check)

## Symptom

A new check passes on the real tree and fails on a violation you inject, so it looks proven. Then a
real violation walks straight through it. Its output says "all checks passed", and the number it
prints comes from its configuration (the size of an allowlist), not from anything it observed.

## Root cause

A check has two failure modes, and only one is loud:

- It finds a violation and exits 1. Visible.
- It finds **nothing to look at** and exits 0. Indistinguishable from a clean repo.

The usual causes of the second: a pattern whose tail requires a shape the real code never has (a
regex that expects a call to end `\n));` when every real one ends `\n}));`), a glob that stopped
matching after a folder move, or an empty file list from a command whose error was swallowed.

A red-then-green test pair does not catch it. The injected violation matched because you wrote it
to fit the pattern, and the green on the real tree was vacuous: "scanned and found nothing wrong"
and "scanned nothing" print the same line.

## Fix, in order of value

1. **Make silence impossible.** Assert the scanner saw what you know is there: every allowlisted
   entry must be observed in this run, or the check fails. If the pattern stops matching, the
   allowlist row goes unseen and the check goes red.
2. **Fail on an empty corpus.** Zero files read means the check could not run, never "clean". A
   sparse checkout, a moved folder or a filter that stopped matching all look like success
   otherwise.
3. **Do not guess the syntax with one pattern.** Find the site with a narrow pattern, then read it
   properly from there: balance the brackets, or parse it (`ast` for Python).
4. **Print what was scanned, not what was configured.** `scanning <n> file(s)` is evidence;
   `1 allowed exception(s)` is not.

```python
files = sorted(Path("src").rglob("*.py"))
if not files:
    sys.exit("no Python files under src/ — the rule cannot be verified")
print(f"scanning {len(files)} file(s)")
```

`scripts/check/ai-config.sh` follows the same habit: it prints how many files its rule-citation
check read, and it fails, rather than passes, when python3 is missing.

## The signal

A check that has never failed on a real violation, only on one you wrote to test it. Before you
trust a new guard, ask: if the thing it looks for moved out of the pattern's reach, would it still
say "passed"? If yes, add fix 1 or 2 until the answer is no.
