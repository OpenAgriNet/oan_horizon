# Amul memory: review and decision record

Reviewed with Gautam on 9 September 2026. This records the current discussion and
local implementation. Gautam later authorized a memory-collection reset and one-farmer
vLLM demo, with backups. Wider rollout remains separate.

## Original intent

Remember useful conversational evidence so a farmer does not start again each time.
Keep every-turn context small, do expensive work in the background, let the existing
agent investigate when needed, and leave live Amul facts in their authoritative systems.
Log examples explain the idea; they must not become a closed definition of what a
farmer is allowed to discuss or have remembered.

## Decisions checked in this conversation

| Area | Current decision |
|---|---|
| Farmer categories | Rejected explicitly. No five-category classification, labels, or kind filter. Legacy stored memories remain readable. |
| Flexible metadata | Retained explicitly. Different farmers can have different useful keys; the writer reuses documented vocabulary or adds a new key. |
| Standing record | Program-team controlled because it is injected every turn. Shared configuration controls names, meanings, and sizes. |
| Seven fields | Current starting configuration only; values are optional. Gautam approved explicit team control, not an eternal set of seven required facts. |
| Search/list/read | Approved explicitly. Semantic discovery, deliberate exact listing, direct selected-entry reading, within the existing reply agent. |
| Filter completeness | Only covers recorded matching keys/states. Normal search can broaden/rephrase without filters. |
| Keys-only context | Gautam confirmed: return no context when both standing record and headline results are empty, even if keys were fetched. |
| Recorded status | Keep open/pending/resolved/n/a as record state; do not treat model assignments as infallible real-world facts. |
| Dates | Show source/end dates; do not hide unresolved entries just because a deadline passed. Current-version checks remain. |
| Failed checks | Retry once. If still unavailable/malformed, leave the proposed change unwritten and report it for retry. |
| Background learning vs reply use | Separate. Disabling reply use does not stop background learning. The writer has no settings tool. |
| User setting default | Latest instruction supersedes selected-user opt-in: default on for all users for now; retain explicit stored off flags. No bulk enable writes. |
| Global setting | Bot global MEMORY_ENABLED still gates use and defaults off. No environment flags were changed by this review. |
| Public metadata | Fix approved: reply read responses expose filtered metadata only; trusted background reads retain identifiers needed for matching. |
| Previous-version links | Fix approved: create callers cannot invent history links. Only the checked update code creates them. |
| Long detail | Approved and implemented: bounded lossless chunks, Level 2 summary plus at most five inline contents rows, passage search and complete chunk reads with program-controlled page sizes. |
| Live data | Do not duplicate balances, account lists, herd counts, or other facts fetched live from Amul. |
| Identifiers | Keep the existing metadata-only animal-tag exception. Sensitive-content checks remain fallible and need evaluation. |
| Scope | Farmer chat is the first validation target. Voice parity and doctor case histories remain separate work. |
| Future features | Reminder delivery, aggregate analysis, chat correction, retention/deletion, scheduling/access control, and rollout are not included as completed work. |

## Repairs in the local implementation

- General entries and typed, multiple metadata filters replace required categories.
- Search/list/read distinguish empty, disabled, unavailable, and partial results.
  References accompany whole chunks; long detail has explicit next chunk numbers.
- Direct reads enforce farmer ownership and identify older versions.
- Public metadata no longer contains a raw hidden-key alias. Internal writer reads
  retain matching data and never change reply settings.
- Public creation cannot supply a previous-version link; only updates generate it.
- Program-owned standing fields are shared between service and writer, size checked,
  and passed through the common checks before writing.
- Invalid/unavailable checks retry and block saving if they remain unavailable.
  Redacted text is checked again. Failed writes do not block an otherwise valid retry.
- Omitted update detail/metadata is preserved. Replacements are saved before retiring
  prior versions. Updates cannot target internal or already superseded records.
- Fold destinations must exist, be current, and belong to the same farmer.
- Consolidation's unassigned latest-date variable is fixed. Its current-entry scan
  follows pagination; the standing pass chooses recent records deterministically.
- Per-entry supporting turns determine source traces, sessions, and dates. One turn
  can support different situations; same-trace/category rejection was removed.
- Interleaved sessions keep chronological order. Historical windows are anchored to
  the supplied cutoff rather than today.
- Background vocabulary discovery shares definitions without other farmers' values.
- The merge prompt no longer clips each fragment at 800 characters; late details
  now reach merge synthesis. A regression test covers facts beyond that boundary.
- Re-embedding understands parent contents vectors and actual child passage vectors.

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

## Limits and validation

Offline synthetic tests verify mechanical behavior, not real extraction/merge quality.
Chunk contracts have also run against a disposable real Qdrant. The authorized
one-farmer demo uses Gemma through the configured vLLM, with a local reviewed API
on port 8101. Its final two source sessions are held out. See the demo report for
results and limitations; the production bot has not been deployed or enabled.

Remaining known limits include semantic duplicates on nondeterministic reruns,
consolidation across different batches, concurrent writers, a durable retry queue,
and history/result bounds. See [technical decisions](memory-design-decisions.md) and
[backtesting](backtesting-plan.md). Historical observations in
[log findings](log-findings.md) remain evidence, not newly verified results.
