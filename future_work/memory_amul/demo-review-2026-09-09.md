# One-farmer memory demo review — 9 September 2026

The core storage and retrieval design is ready for a controlled engineering demo.
The Gemma agent flow is not yet reliable enough to claim complete recall or complete
listing from ordinary requests. Authentication remains a separate decision, as agreed.

## Setup and final data

Gautam selected an existing farmer with repeated conversations. Farmer suffix **5951**
had the most distinct stored sessions among eligible demo farmers.

- Read 338 turns in 52 sessions from Langfuse, using read-only access.
- Generate memories from 326 earlier turns, processed in 45 prompt chunks.
- Cutoff: `2026-09-07T16:16:53.389Z`; reserve the final 12 turns in two sessions.
- Model: configured local vLLM `gemma-4-31b-it`, port 8894.
- Reviewed memory API: localhost port 8101, existing Marqo document/query embeddings.
- Final store: **9 current episodes, 11 current chunks, 25 episode versions**, plus
  one standing record containing the supported Gujarati language preference.
- Every stored episode layout respects the 350-character summary, 120-character
  contents rows, at-most-five rows and 1,200-character chunk bounds. All source IDs
  resolve to the source export; none belong to held-out turns or exceed the cutoff.

The authorized reset affected only `amul_memory`. Full points/vectors were backed up
before each reset; separate settings records are preserved by the reset code. None
existed in this dataset. Other Qdrant collections and production bot enablement were
untouched. The first backup is
`/amulpfsdata/gautam/amul-memory-demo/before-reset-20260908T223112Z.json`.

Private source exports, backups, generation logs, per-probe tool transcripts and the
complete bot patch are in `/amulpfsdata/gautam/amul-memory-demo/`. They are deliberately
outside these documentation repositories. The original service container on 8100
was not rebuilt; demonstrations should use the reviewed local API on 8101.

## What was fixed using real-run evidence

1. Contents synthesis sometimes returned too many rows, blocking updates. Code now
   determines at most five adjacent chunk groups; the model writes bounded descriptions.
2. Update checks saw the old conversation count. They now see the proposed union of
   selected source sessions and dates before deciding whether recurrence is supported.
3. The consolidation prompt clipped each input account at 800 characters. That caused
   the specific report of missing AI receipts to disappear in an earlier merge. The
   cut is removed, and a regression test verifies late detail reaches synthesis.
4. The merge prompt demanded repetition even when fragments came from one conversation.
   It now receives a distinct-session count and does not equate fragments with occasions.
5. Per-turn parallel tool calls could race the evidence budget. Memory calls share
   a per-turn lock. Returning a whole chunk takes precedence over filling the remaining
   character allowance: additional output is stopped rather than shortened.
6. Re-embedding now uses actual child passage text and parent summary-plus-contents,
   so later embedding migrations will not replace chunk vectors with blank-text vectors.

Later source instruction supersedes the earlier configurable read-budget proposal:
**agent-facing tools return whole chunks**. Search has query/optional episode reference;
read has reference/optional chunk numbers/optional history; list has state/filters/cursor.
No model-selected character budgets, offsets or result counts remain.

## Mini-test evidence

The probe uses Amul's installed Pydantic AI SDK, actual memory tools, actual
`FarmerContext`, automatic memory context and shared memory instructions. It uses a
small review system prompt and registers only memory tools. It is **not** the complete
Amul HTTP chat route, translation pipeline, production model selection or live Amul
operational tools. Responses are requested in English for review.

Eight questions were run with memory off and on, using the same model and review
prompt. Two are genuine held-out questions; six are constructed checks. This is a
smoke test, not an eight-case unbiased quality benchmark. Earlier probe transcripts
are retained, including failures that motivated changes.

| Probe | Final observation |
|---|---|
| Recall calf-scheme problem | Recalled the scheme/registration difficulty and previously discussed escalation without another tool call. |
| Specific missing AI receipt | Failed: searched detail, but answered the earlier certificate-eligibility question. The specific source report that no receipt was supplied is absent from final current memories. |
| Ordinary “list unresolved matters” | Failed: returned three automatic matches without calling list. |
| Explicit request to use list | Passed plumbing: called list twice, followed the cursor, and obtained all nine stored entries before grouping them in the reply. |
| Read escalation chunk directly | Called read on the chosen chunk and returned the discussed office. Whole chunk reached the agent. |
| Held-out delayed order | Did not invent an order status; recognized live order records were needed. Some response wording still implied future checking despite the fixture lacking those tools. |
| Held-out current herd/tags | Did not invent tags or assert a current total, but mentioned the earlier reported 12-versus-5 discrepancy. Review whether that historical aside is useful or distracting. |
| Unrelated arithmetic | Answered 43 without using or mentioning memory. |

Observed final probe median wall time: **0.33 seconds off, 1.25 seconds on**.
Memory-on range was **0.58–3.14 seconds**. These are warm local runs on one farmer,
not production latency or p95 estimates.

## What the demo does and does not establish

The design is general: no required categories, program-controlled standing fields,
optional farmer-specific keys, search/list/read, version history, whole chunks and
bounded automatic context. The stored accounts distinguish offered veterinary visits
from confirmed bookings. Relevant source-linked detail can be found and read.

The remaining problem is quality and tool selection, not missing APIs. Generic list
requests still need evaluation with the full Amul agent and the actual reply model.
Repeated generation runs also produced different groupings and omissions. Safety
checks refused some routine-looking updates; no validation failures were bypassed.
Consolidation left related fragments separate, including a merge rejected because
all its traces were already present on the destination. Leaving the originals current
avoids losing them, but does not finish semantic deduplication.

This farmer produced no visible flexible metadata vocabulary beyond the private
animal identifier. Typed multi-key filtering is verified with synthetic records;
this real farmer does not demonstrate useful metadata extraction across topics.

A controlled demo can show the stored memories and explicit search/read/list paths.
Do not present ordinary-language completeness, extraction fidelity or merge quality
as solved. The next evaluation should use the full Amul agent, as proposed in the
[backtesting plan](backtesting-plan.md).

## Code review and checks

The bot diff against local `main` contains seven memory-related files: `agents/deps.py`,
`agents/agrinet.py`, tool registration, `agents/tools/memory_tools.py`, chat attachment,
`app/services/memory.py` and the memory date formatter. No unrelated feature changes
were found. The extra `agrinet.py` change puts memory rules in agent instructions.
Without memory context, its original prompt selection is preserved. Existing SHC
context remains attached through the same path.

The complete patch is
`/amulpfsdata/gautam/amul-memory-demo/amul-oan-api-vs-main.patch`.
The observed bot branch now contains commit `21e1908` (“memory design”); this agent
issued no git commit or push commands. Memory-service changes remain in the working tree.

**115 mechanical tests pass across the offline and disposable-service runs:**
29 unit, 19 writer/source regressions, 25 bot-tool/context tests, 7 layout/migration
tests, 6 real-Qdrant chunk contracts and 29 HTTP service contracts. Actual SDK schemas
also verify that only the simplified tool arguments are exposed. Syntax and diff
whitespace checks passed. These counts are not model-quality scores.
