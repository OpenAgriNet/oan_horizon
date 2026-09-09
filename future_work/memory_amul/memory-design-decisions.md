# Technical decisions

Current companion to [the overview](memory-overview.md), 9 September 2026.

## A small service over Qdrant

Keep one Qdrant collection with two named dense vector slots: `headline` and
`expanded`. Parent episode points hold the Level 2 vector; child chunk points hold
Level 3 vectors. Chunk points are internal and never appear as independent memories. The service supplies storage, farmer scoping, exact filtering,
versioning, and settings enforcement. The background job supplies reasoning. This
fits the existing infrastructure and makes stored state inspectable without adopting
Honcho or Graphiti's larger memory model.

Marqo currently supplies embeddings; it is not a second memory store. E5 document
and query conventions differ. Keep them consistent, stamp `embed_model` on stored
memories, and re-embed deliberately when changing models. A matching dimension alone
does not establish vector compatibility. Changing embedding infrastructure remains
separate work.

## Retrieval decisions grounded in earlier experiments

The recorded experiments in `oan-brain/knowledge/amul-memory-system.md` found large
score overlap between real and irrelevant queries for the same farmer. Do not infer
“on record” from a score threshold. These were small historical experiments, not
validation of the revised writer or all future conversations.

A homemade semantic/keyword blend without corpus IDF performed worse and was removed.
Semantic search plus agent-selected rephrasing remains the baseline. Exact field
listing serves a different purpose and is not ranked search.

There are no category labels or category filters. Arbitrary documented metadata keys
remain available. Multiple typed scalar filters are ANDed and scoped to the farmer
in code. Internal record kinds are always excluded from memory search/listing.

## Write boundaries

The live agent is read-only. Background tools propose changes through `writer.apply`.
The standing-record pass also uses that boundary. The writer generates the bounded
summary and contents page before checking the complete proposed account. Redacted text is checked again before saving. The deterministic
identifier cleanup supplements model checks; it is not a complete privacy classifier.

An update preserves omitted detail/metadata, writes the replacement first, and only
then retires the prior version. A failed write cannot retire the only current memory.
Fold destinations must exist, belong to the same farmer, and be current memories.
Semantic merge correctness still needs evaluation; valid IDs do not prove two
situations are the same.

Supporting turns are selected per entry. Distinct known source sessions determine
recurrence counts. Exact normalized-headline retries and updates whose traces are
already recorded are guarded. This is not a proof of semantic idempotency: a reworded
new proposal can still be duplicated. One turn may legitimately support two distinct
memories, so shared trace IDs alone cannot reject a new entry.

## Limits to keep visible

- The consolidation pass reads all current pages but clusters bounded batches.
  Related entries in different batches may remain separate.
- There is no automatic condensation pass. Chunking preserves the proposed detail;
  extraction and merge reasoning can still omit source facts. Previous versions
  preserve earlier stored accounts; raw transcripts remain in Langfuse.
- Retry reports are not a persistent job queue. Concurrent dreamer runs for the
  same farmer need an operational single-writer rule or a later locking/checkpoint
  design; replacement and retirement are not a cross-point transaction.
- API writes and internal reads assume trusted callers. The local service has no
  end-user authentication layer. Restrict access before deployment beyond that boundary.
- Dynamic extraction, key selection, and state assignment can all omit information.
  A listing is exact over its stored values, not exhaustive over reality.

Program control of standing fields, temporary default-on user settings, and future
scope are described in the overview and decision review.
