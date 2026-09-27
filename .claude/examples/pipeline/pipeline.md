---
paths:
  - 'src/app/pipeline/**'
  - 'src/app/worker/**'
  - 'src/app/cli.py'
---

# Pipeline Patterns

`AGENTS.md` §H (the pipeline rules) is the enforced version — read it first. This file is the
deeper reference for each stage's contract and for the batch job's runtime budget. Schema and
migrations are in [alembic.md](alembic.md); tests in [pipeline-testing.md](pipeline-testing.md).

## The line

```
pipeline/sources/base.py       Protocol: Source.fetch() -> AsyncIterator[RawDocument]
pipeline/sources/<source>.py   one adapter per content source
pipeline/sources/filesystem.py local files — pipeline development and tests, no live source
pipeline/stages/normalize.py   RawDocument -> NormalizedDocument, computes content_hash
pipeline/stages/chunk.py       NormalizedDocument -> list[Chunk], heading-aware with overlap
pipeline/stages/embed.py       list[Chunk] -> list[EmbeddedChunk], batched, bounded retry
pipeline/stages/load.py        list[EmbeddedChunk] -> database, idempotent on content_hash
pipeline/stages/types.py       the shapes above
pipeline/runner/runner.py      run_pipeline(): the stages in order, plus the run record
cli.py, worker/tasks.py        entry points; both call run_pipeline() and nothing else
```

Data flows one way. A stage never reaches backwards, and stages talk only through their package
`__init__.py` (import-linter independence contract on `app.pipeline.*`).

## Purity is the contract, not a preference

`normalize`, `chunk` and the batching logic in `embed` are pure: data in, data out, no database,
no network. Only `sources/*` and `load.py` do I/O.

That is what makes "the chunking got worse" a unit test that runs in seconds instead of a full
re-ingest against a live source. A database session opened inside `chunk.py` destroys that
property; it is the most damaging change you can make to this pipeline's debuggability.

`embed.py` is the nuanced one: its batching and retry logic must be pure and testable, while the
provider call itself goes through the `EmbeddingProvider` protocol, injected as a default
parameter so tests pass a fake.

## Sources

A source yields `RawDocument`s and nothing else — no normalising, no chunking:

```python
class DocsSiteSource(Source):
    async def fetch(self) -> AsyncIterator[RawDocument]: ...


docs_site_source = DocsSiteSource()
```

Register it in `cli.py` as a new `--source` choice. Nothing downstream changes, because every later
stage works on the source-agnostic shapes. Its name is declared once and imported by the CLI, the
worker and the tests (the one-home rule).

A source that reads published, public content stays unauthenticated. Giving it credentials, or
pointing it at an authenticated route, turns a public consumer into a privileged one: that is a
security change, not a convenience.

Use `sources/filesystem.py` in development and in tests; never reach a live source from a test.

## Chunking

Heading-aware, with overlap. Size and overlap are settings (`core/settings/config.py`), never
literals scattered in the stage: they get tuned, and a tuning change means a full reindex, so they
must be findable and reviewable.

Changing either **changes the corpus**. Existing chunks were produced under the old settings, so a
change without a reindex leaves the index internally inconsistent.

## Loading — idempotency is the invariant

Keyed on the document's `content_hash`:

- Content unchanged: **no** new chunk rows, `indexed_at` untouched, and the run records 0 chunks
  written.
- Content changed: the document's chunks are replaced in a **single transaction** — delete its
  chunks, then insert the new set. Never a row-by-row update-in-place diff.

Delete-then-insert exists because of chunk-count drift: new content can produce a different number
of chunks, so a positional update leaves orphans from the previous run. A duplicated corpus still
returns answers, just worse ones, so this regression is silent in production; its test is the one
to keep green.

## Runs are always recorded

Every run writes a `pipeline_runs` row, success or failure: source, start and end time, documents
seen, chunks written, status, and the error on failure. `run_pipeline()` wraps the stages in a
try/except whose only job is to guarantee that row. It lives in `pipeline/runner/`, not in
`cli.py`, because `cli.py` is composition only and excluded from coverage: logic there would go
untested.

A swallowed failure that leaves the table looking clean is the bug this exists to prevent: the
schedule looks healthy while the corpus silently goes stale.

## Worker and CLI

The worker task (`worker/tasks.py`) is a thin wrapper that calls `run_pipeline()`, exactly as the
CLI does. Never fork the logic: the worker is how this runs in production, and a divergence means
local runs stop being evidence about production behaviour.

## Performance — a batch job, not a request path

Nobody waits on a response. The constraints that bind are different from a request path's:

| Constraint | Why it binds |
| --- | --- |
| Embedding API quota and rate limits | the ceiling on how fast a full reindex can run |
| Write pressure on a shared database | a reader service may be querying it while you write |
| Memory when a source yields large documents | the whole corpus must never be resident at once |

- **Stream, never accumulate.** `Source.fetch()` is an `AsyncIterator` on purpose. The moment a
  stage does `documents = [d async for d in source.fetch()]`, memory grows with the corpus and a
  growing corpus eventually kills the worker.
- **Batch the embedding calls.** One provider call per batch, with the batch size as a setting.
  One call per chunk multiplies wall clock and quota by the chunk count.
- **Bounded retries with backoff**, in the adapter. An unbounded retry against a quota error does
  not recover; it burns the remaining quota.
- **One transaction per document**, with one multi-row insert for its chunks. A transaction that
  spans the corpus holds locks for the whole run and blocks the reader; one per chunk loses the
  atomicity the load rule needs. Never hold a transaction open across an embedding call.
- **Prefer incremental runs.** The content-hash check makes an unchanged document cost a hash
  comparison, not an embed and a write. Schedule full reindexes deliberately.
- **One `@lru_cache`d async engine per process** (`db/session.py`), never one per document: the
  pool is shared with the reader's role, and exhausting it takes the reader down too.
- **Measure before optimising.** Log events carry the document id, the source and the run id, and
  the runs table records chunks written. On an incremental run the embedding calls dominate, and no
  amount of Python tuning touches that.
