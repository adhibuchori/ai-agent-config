---
paths:
  - 'tests/**'
  - 'pyproject.toml'
---

# Testing the Pipeline

The purity and idempotency rules in `AGENTS.md` §H are what this file supports; the tiers, the
coverage floor and the loop-scope constraint are in `../common/testing.md`. This file covers how to
test each stage.

## Layout

Every test mirrors the path of the source it tests (`../common/folder-shape.md`):

```
tests/unit/pipeline/stages/test_normalize.py   pure — no fixtures
tests/unit/pipeline/stages/test_chunk.py       pure — no fixtures
tests/unit/pipeline/stages/test_embed.py       batching and retry, faked EmbeddingProvider
tests/unit/pipeline/stages/test_load.py        idempotency, the database faked
tests/unit/pipeline/sources/test_<source>.py   source adapters, transport faked
tests/unit/pipeline/runner/test_runner.py      the run record, on success and on failure
tests/unit/worker/test_tasks.py                the worker calls run_pipeline()
tests/integration/pipeline/stages/test_load.py the same idempotency cases on real Postgres
tests/fixtures/                                fakes shared by more than one file
```

## Pure stages — the cheap, high-value tests

`normalize` and `chunk` take data and return data, so their tests need nothing:

```python
def test_chunk_keeps_heading_context_on_each_chunk() -> None:
    doc = NormalizedDocument(title="T", content="# Intro\nalpha\n# Setup\nbeta")
    chunks = chunk(doc, size=32, overlap=8)
    assert [c.heading for c in chunks] == ["Intro", "Setup"]
```

If such a test needs a database, the stage is no longer pure: fix the stage, not the test.

Cover the boundaries explicitly: empty content, content with no headings, a chunk shorter than the
overlap, and content exactly one chunk long. An off-by-one there silently drops or duplicates text,
and nothing else catches it.

## `embed` — test the batching, fake the provider

```python
class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]


async def test_embeds_in_batches_not_one_call_per_chunk() -> None:
    provider = FakeEmbeddingProvider()
    await embed_chunks(make_chunks(25), provider=provider, batch_size=10)
    assert [len(c) for c in provider.calls] == [10, 10, 5]
```

`EMBEDDING_DIMENSIONS` is imported from `core/settings/constants.py`, never retyped. Also test that
a rate-limit error retries a bounded number of times and then gives up: an unbounded retry is not
recovery, and only a test pins the bound. Never a live provider call, never a real API key.

## `load` — the idempotency tests are the important ones

The regression fails silently in production: a duplicated corpus still returns answers, just worse
ones. Cover all three cases:

```python
async def test_unchanged_content_writes_no_chunks() -> None: ...
async def test_changed_content_replaces_chunks_in_one_transaction() -> None: ...
async def test_fewer_chunks_than_before_leaves_no_orphans() -> None: ...
```

The third is the one people forget: new content can produce *fewer* chunks, and a positional
update would leave the tail of the previous run behind. It is why the load rule says delete and
insert.

## The failure path

A run that raises partway through still writes its `pipeline_runs` row:

```python
async def test_records_a_failed_run_when_the_source_raises() -> None:
    with pytest.raises(SourceUnavailableError):
        await run_pipeline(source=RaisingSource())
    run = await latest_run()
    assert run.status == "failed" and run.error
```

Without it, a broken schedule looks healthy while the corpus goes stale.

## Sources

Fake the transport, not the network. `sources/filesystem.py` doubles as the fixture source for
pipeline-level tests. Never reach a live source from a test, and never give a test credentials for
one.

## Integration tests

Marked `@pytest.mark.integration`, gated by `RUN_INTEGRATION_TESTS=1`, against real Postgres from
`docker compose up -d`. The schema comes from `alembic upgrade head`, never from DDL written in a
fixture: hand-written DDL lets the test schema drift from the revision chain and hides exactly the
bug `alembic check` exists to catch.

## What not to test

- `cli.py` argument wiring — composition only, omitted from coverage like `main.py`;
  `run_pipeline()`, which it calls, is tested
- Alembic itself — `alembic check` in the gate covers drift
- Embedding values — assert on shape and dimension, never on floats
