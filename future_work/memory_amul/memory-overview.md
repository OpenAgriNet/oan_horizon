# Amul memory: the current design

Current deployment architecture (9 September 2026): Amul reads Qdrant directly through `app/services/memory_store.py` and uses its existing Marqo endpoint for query embeddings. The independent background dreamer consumes Langfuse and writes Qdrant through its private storage API. The bot does not require `MEMORY_API_URL` or a running memory service. Settings, ownership, current-version filtering and chunk assembly are enforced by the bot reader. HTTP routes described here remain the background service contract. See [bot deployment settings](../../../amul-oan-api/docs/memory-dev-demo.md).

Reviewed with Gautam, 9 September 2026. Local implementation, not a rollout report.

## What this is for

A farmer should not have to start from the beginning on every visit. Remember useful
things learned in conversation: what they have tried, what remains uncertain, what
they want remembered, and how they prefer to converse. New topics should work without
adding a new category or a special-purpose tool.

The original principles still govern the design:

1. Do expensive reasoning after conversations. Keep waiting during replies bounded.
   Parallel requests still take time; measure the actual added latency.
2. Remembering something wrongly can be worse than staying quiet. Confirm ambiguous
   animal/account references and distinguish reported claims from established facts.
3. Do not remember everything. Sensitive admissions and identifying numbers should
   not be copied into conversational memory. Current checks need evaluation; they
   are not a proof of perfect detection.
4. Live Amul records remain authoritative for balances, payments, herd details,
   account lists, and similar changing facts. Memory must not become a stale copy.
5. Memory covers recorded conversations, not the farmer's whole life. An offered
   visit is not a confirmed booking; no confirmation in chat does not mean no visit.
6. Keep source links, dates, and earlier versions so mistakes can be investigated.


## Deciding what to retain

The agent and pipeline share a neutral usefulness test in `dreamer/prompts.py`.
There is no expected memory count and no instruction that most batches should be
empty. Each farmer statement must be considered even when the surrounding batch
contains routine milk tables. Goals and interests can be retained as discussions,
without claiming the farmer committed to or completed an action. An answered
question is not proof that its underlying concern was resolved.

Live record values and the fact that a lookup happened are not episodes by
themselves. A reported missing entry, unexplained deduction, or unresolved request
for correction can be useful conversational context. General education without
personal context or follow-up value can still be skipped. Skip reasons are logged.

The sensitive-content check explicitly permits ordinary livestock illness, care
and treatment history. Its human-health restriction does not apply to animal
health. Ordinary record grievances are not by themselves financial distress or
wrongdoing. Existing restrictions on private human information and prohibited
admissions remain. A separate honesty check must still reject unsupported diagnoses,
confirmed actions or bookings. Failed checks still leave proposals unwritten for
retry; these prompt changes do not bypass the write checks.

These are model judgments, not hard guarantees. Check missed concerns and needless
retention as separate measures; a higher episode count alone is not success.

## Three levels of reading

| Level | Contents | When read |
|---|---|---|
| Standing record | Small set of program-approved conversational facts/preferences | Every enabled farmer-chat turn |
| Level 2 | Summary plus inline contents ranges, dates and reference | Automatic search over summary and contents |
| Level 3 | Searchable chunks of the full episode account | The existing reply agent chooses search/list/read tools |

A successful ordinary reply often needs no additional memory tool. When more evidence
would help, the same agent chooses how to look. There is no separate search agent.

## General entries, flexible keys

There are **no mandatory farmer-memory categories** and no category filter. The old
five labels (`profile`, `complaint`, `booking`, `health_note`, `tracker`) came from
examples and overlapped. They could split the same grievance across categories and
silently hide it from a filtered lookup. Old records remain readable; no destructive
migration is required.

Each memory has a summary, detail, recorded state, dates, and source/version links.
Optional metadata holds useful filterable details. One farmer might have `scheme`
and `application_stage`; another might have `feed_supplement` and `animal_reference`.
These are examples, not required keys. The writer can invent keys and document what
they mean, while preferring existing vocabulary. Shared vocabulary is allowed;
other farmers' example values must not reach this farmer's agent.

The internal storage field `type` separates actual memories from settings, standing
records, and key documentation. It is bookkeeping, not a farmer-facing label. It is
not an instruction for the model to classify every conversation.

Recorded state remains `open`, `pending`, `resolved`, or `n/a`. These describe the
record's last supported state. Model assignments can be incomplete or wrong; a fixed
vocabulary does not make them ground truth.

## Search, list, read

- **Search** for a situation in ordinary words. It searches expanded text by meaning
  and returns matching passages with episode/chunk references. Rephrase or broaden when useful.
  Keys are optional. Similarity scores do not prove relevance or absence.
- **List** when the farmer asks for recorded items, optionally matching state and
  one or several metadata values. All specified keys must match. Follow the next-page
  cursor when more results exist. Missing tags can exclude a relevant record.
- **Read** a selected reference directly. This opens that entry, rather than doing a
  second search that might return a different one. Long detail can be read in pieces
  using the suggested next chunk numbers. Earlier versions are available on request.

A filtered list answers “which stored records have these values?” It does not prove
that every relevant conversation was extracted or tagged. Broader semantic search
remains available independently of the keys.

The tools distinguish an empty result, disabled access, a failed lookup, and a partial
result. They keep references internal and stop after a bounded number of requests.
Dates are shown so the agent can reason about them. An expired deadline does not
silently remove an unresolved memory. Superseded versions are excluded from current
results because they were replaced, not because they are old.

## Long episodes and reading budgets

Level 2 contains a summary plus an inline contents page with at most five rows.
Each row describes a range such as “chunks 3–4: registration attempts and missing
receipts.” Contents rows are navigation hints, not category labels or metadata keys.
Code partitions adjacent chunks into at most five groups; the model describes each
group. Code checks coverage and character limits, so the model need not count ranges.

The writer saves the full proposed Level 3 account without an automatic condensation
pass. Code splits it at paragraph/sentence/word boundaries where possible, preserving
every character. Defaults, shared by the writer and service:

| Setting | Default |
|---|---:|
| `MEMORY_CHUNK_MAX_CHARS` | 1,200 characters per stored chunk |
| `MEMORY_SUMMARY_MAX_CHARS` | 350 characters for the Level 2 summary |
| `MEMORY_CONTENTS_ROW_MAX_CHARS` | 120 characters per contents row |
| Contents rows | At most 5 |

Each chunk is separately embedded and searchable. The agent can search all this
farmer's Level 3 passages, optionally restrict to an episode, or directly read chunk
numbers from the contents page. Natural-language queries and specific keyword strings
both use dense semantic retrieval today; there is no separate exact keyword index.
The contents cannot mention every fact, so search is independent of its rows.

Latest simplification approved by Gautam: tools return complete chunks, never
character-truncated pieces. The Amul agent does not choose character budgets, offsets,
or result counts. Search accepts a query and optional episode reference; read accepts
an episode reference and optional chunk numbers. Listing retains optional state,
metadata filters and a next-page cursor. History reading remains optional.

Program defaults are three search chunks, three read chunks per page, eight list
summaries, and six requests per turn. The 12,000-character evidence guard stops
additional output rather than cutting a chunk. Memory tools serialize concurrent
calls so they share that guard. A response suggests the next whole chunk numbers.
Chunk numbers belong to one immutable episode version. Automatic context has a
separate 4,500-character limit and keeps a summary and its contents together when
dropping overflow. Low-level offset API reading remains for compatibility; neither
the reply agent nor the background read tool exposes character offsets.

This preserves the proposed account, not every fact in the source transcript:
extraction and merge proposals can still omit evidence. Earlier stored versions and
source references remain available for audit. Legacy entries get a readable layout
without a hidden write; an explicit internal index route can index their passages.

## Explicit program control of the standing record

This is deliberately different from flexible metadata. It enters every turn, so
program teams decide the allowed fields, descriptions, per-field lengths, and total
size in `amul-memory/service/profile_fields.json`. The service and writer use the
same configuration. Set `MEMORY_PROFILE_SCHEMA` to use another approved configuration
and deploy that same version to both processes.

The current seven names are a starting configuration, not seven required facts:

| Field | Intended meaning |
|---|---|
| `name_used` | Conversational name only when live records do not already supply it |
| `usual_account` | A usual account preference to confirm, never a number or account list |
| `language_register` | Supported language/answer-style preference |
| `animal_references` | Clear, recurring descriptions of animals, never identifying tags |
| `usual_topics` | Recurring interests, not a list of current problems |
| `standing_sensitivities` | Explicit requests about tone/topics to avoid, not inferred distress |
| `explicit_requests` | Lasting conversational instructions, such as keeping answers short |

Only populated approved fields are stored. Unknown names are omitted and reported;
oversized or non-text approved values are rejected. Current total value budget is
700 characters. The model cannot add fields. The team can remove or replace these
names without creating mandatory categories for ordinary memories.

## Background learning and reply settings

The background job reads farmer chat traces, searches existing memories, proposes
writes/updates, checks them, consolidates likely duplicates, and derives the standing
record. Supporting turn numbers are selected per proposal; code derives trace IDs,
session sets, and first/latest dates from those turns. Unrelated turns in a batch do
not count as evidence for every memory.

Sensitive-content and unsupported-claim checks must succeed before a proposal is
saved. A failed or malformed check is retried once. If still unavailable, the change
stays unwritten and the job reports a retry reason. This does not yet provide a
durable retry queue or an unattended scheduling guarantee.

**Current setting, per Gautam's latest instruction:** the bot's global
`MEMORY_ENABLED` defaults off. When it is on, per-farmer reply use defaults **on**.
An existing explicit `memory_enabled: false` in Qdrant is respected. Missing user
settings need no bulk initialization. A failed settings lookup returns no memory.

That flag is a separate deterministic settings record, not model-generated metadata.
Only the administrative settings endpoint changes it. The background agent has no
settings tool. “Off” currently stops use in replies; background learning can continue
through separate internal read routes and ordinary write routes without changing
the flag. This is not a retention or deletion policy.

## What remains outside this change

The live bot global switch and farmer flags were not changed. Gautam subsequently
authorized a backed-up reset of the Amul memory collection and a one-farmer vLLM
demo through a local API on port 8101. Other collections and outreach are untouched. Farmer chat is the first
validation target; voice parity and doctor case histories are not established.

Before wider use: run chronological held-out replay, measure live latency and unwanted
recall, decide service access control and reliable job scheduling/retry, and settle
retention/correction/deletion. Proactive reminders and cross-farmer analysis remain
separate future work. See the decision review for specific implementation limits.
