# Providers — the wrapping-API layer

`AGENTS.md` §D (Rules 12–15) is the enforced, numbered version — read it first. This file is the
deeper reference for the provider pattern and the traps in it.

## The shape

Every external dependency is a `Protocol` plus at least one adapter:

```
providers/llm/base.py         Protocol: LLMProvider
providers/llm/<vendor>.py     vendor SDK adapter + module-level instance
providers/embedding/base.py   Protocol: EmbeddingProvider (if this repo embeds anything)
providers/embedding/<vendor>.py  adapter
```

A service depends on the `Protocol`, never on the vendor module (§D Rule 12). The payoff is
concrete: swapping one adapter for another, or a stub for a real implementation, is a one-line
default-parameter change with no service edit and no test rewrite.

`providers/` must never import `app.modules` (§B Rule 8, enforced by import-linter).

## Writing a new provider

1. Define the `Protocol` in `<kind>/base.py` with the narrowest method set a service actually needs
   — not the vendor SDK's surface.
2. Implement the adapter in `<kind>/<vendor>.py`. Translate vendor exceptions into
   `UpstreamProviderError` here, so no vendor exception type escapes into a service.
3. Export a module-level instance for use as a default parameter.
4. Unit-test the adapter's translation logic with a fake transport; never a live call.

## LLM — two rules that exist because of real failure modes

**Streaming is the default (§D Rule 14).** Use the vendor's streaming API, not a bare
non-streaming call. Long generations exceed the HTTP timeout otherwise.

**Check the completion status before trusting the text (§D Rule 15).** Some vendors' safety
filters can decline a request *while still streaming partial text*. Accumulating that text and
returning it delivers a refusal to the user as a broken answer. Anything other than a genuine
success status must become an error before the text is treated as content. Keep the regression
test that pins this down; it is one of the highest-value tests in the repo.

## Embedding (if applicable)

The model name and its output dimension are a cross-repo contract if a sibling repo owns the
vector column's schema. That column's width is fixed at migration time there, so changing the
embedding model here without a coordinated migration and full reindex produces dimension-mismatch
errors at query time, not at boot. Treat the setting as schema, not config.

## Retriever and the read-only role (if Rule 13 applies)

`src/app/db/models.py` is a byte-for-byte mirror of the schema owner's copy (§D Rule 13). A
read-only service has no migrations and no write role:

- A retriever/reader issues `SELECT` only. No `INSERT`/`UPDATE`/`DELETE`, no DDL.
- A new column needed here lands in the schema-owning repo first (migration + model), then this
  repo's `models.py` is updated to match in a follow-up PR.
- Wire a guard hook (like `.claude/hooks/safety-check.sh`'s existing checks) to warn on edits to
  that file and block `alembic` outright — see `pipeline.example.md` for the mirror-image version
  in the repo that *does* own the schema.

Verify the mirror before committing a change to it:

```bash
diff src/app/db/models.py ../<schema-owner-repo>/src/app/db/models.py
```

## Timeouts and failure

Every provider call needs an explicit timeout — a hung upstream must surface as
`ServiceUnavailableError`, not as a request that never returns. Retries belong in the adapter, with
a bounded count and a named constant. Never retry a safety-filter refusal: it is a decision, not a
transient fault.
