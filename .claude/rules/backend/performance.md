# Performance

The runtime budget behind `AGENTS.md` §B and §D. Provider-call specifics live in
[providers.md](providers.md); HTTP-layer specifics in [fastapi.md](fastapi.md).

## What actually costs time here

A service wrapping an LLM/vendor call is I/O-bound, not CPU-bound. In a typical request the wall
clock is roughly:

| Step | Order of magnitude |
| --- | --- |
| Embed / preprocess the input | ~100 ms, one upstream call |
| Vector search (if applicable) | ~10 ms with an index, seconds without |
| LLM generation | ~1–10 s, dominates everything |

Optimising Python around a multi-second LLM call is wasted effort. The wins are: fewer upstream
calls, never blocking the event loop, and streaming so the user sees output before generation
finishes.

## Event loop

- One `@lru_cache`d async engine per process (`db/session.py`) — never per request.
- No sync client on an async path. Ruff's `ASYNC` rules catch the common cases; a sync `psycopg`
  or `requests` call slipping in is the one to watch for by eye.
- No `await` inside a loop where a batch call exists. Embedding several items is one batched call,
  not N sequential ones.
- Anything genuinely CPU-heavy (large text normalisation) belongs in an offline pipeline, not in a
  request path here — if you have a sibling repo that owns that pipeline, that's where it goes.

## Vector search (if this repo has a `pgvector` column)

- Always `LIMIT` a similarity query — `ORDER BY embedding <=> $1 LIMIT k`, with `k` a named
  constant, never unbounded.
- If the index is created by a sibling repo's migration and a query is slow, check that the index
  exists and that the operator in the query matches the one the index was built for; a mismatched
  operator class silently falls back to a sequential scan.
- Select only the columns the answer needs. A large text column pulled for rows you are about to
  discard is the most common waste in this path.

## Connection budget

If this service holds a read-only role sharing the database with a writer service, the pool is
finite. Hold a session for the shortest possible span: read, release, then call the LLM — never
keep a session open across a multi-second generation.

## Streaming

Streaming is the default for correctness (§D Rule 14), and it is also the main perceived-latency
win. Do not buffer a full generation to post-process it unless the feature genuinely requires the
complete text; that trades away the entire benefit.

## Timeouts

Every upstream call carries an explicit timeout, and the total request budget must be smaller than
the caller's. A caller that gives up before we do means the work continues anyway, consuming a
connection and vendor quota for a response nobody will read.

## Caching

Before adding a cache layer: an identical-input cache keyed on the normalised input plus any
retrieved-context hash is the only shape that is safe — if the answer depends on a corpus, a key
that ignores the corpus version serves stale answers after a reindex. Any cache write needs a TTL
and a documented invalidation trigger.

## Measure before optimising

`structlog` events carry timing context. Establish which step actually dominates a slow request
before changing code — the assumption is usually wrong.
