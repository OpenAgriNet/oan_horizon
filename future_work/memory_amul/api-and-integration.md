# Memory — API reference and how it's wired into the bot

What's actually built and running, with paths. The design reasoning is in
`memory-overview.md`; this is the implementation surface.

Two pieces:
- **The memory service** — `/amulpfsdata/gautam/amul-memory-api/`, container
  `amul-memory-api`, `localhost:8100` (in-network: `http://amul-memory-api:8100`).
  Stores and serves memory. Owns the per-farmer on/off decision.
- **The bot integration** — `amul-oan-api`, branch **`memory_v0`**:
  `app/services/memory.py` (the read + prompt-block builder), plus a small change
  in `app/services/chat.py` and `agents/deps.py`.

Storage: Qdrant (container `amul-qdrant`, `localhost:6350`), collection
`amul_memory`. Embeddings: the same Marqo model Amul's knowledge base already uses
(`multilingual-e5-large`, 1024-dim) — chosen because memory text is often Gujarati.

---

## The three levels, and how each one is served

| Level | What it is | How the agent gets it | Cost per turn |
|---|---|---|---|
| **1. Standing summary** | ~200-word always-true summary of the farmer | **Injected automatically, every turn** | One plain filter, no search, no AI |
| **2. Headline index** | 2-sentence headline per memory, with status | **Injected automatically, every turn** — top-k matched against the farmer's current question | One embedding + one vector search |
| **3. Expanded detail** | The fuller text behind each headline | **Not injected.** Fetched only when the agent deliberately asks | Nothing, unless asked |

All three levels are now wired in and working. Level 3 is a tool the agent chooses
to call — `recall_more_detail` in `agents/tools/memory_recall.py`:

- It takes **a plain description** of what it wants ("the skin problem on her cow"),
  not an entry id — passing UUIDs through a model invites hallucinated ids and leaks
  internal identifiers for no benefit.
- **The farmer is never a parameter**: `farmer_id` comes from signed-in deps, the
  same way every other farmer-specific tool here works, so the model cannot ask
  about someone else even if it tries.
- A **prepare hook hides the tool entirely** when memory is off or no farmer is
  resolved, so the model never sees a tool that would return nothing.
- Bounded output, never raises, and framed as confirm-not-assert with an explicit
  note that it only covers what happened in this chat.
- Multi-step search falls out for free: the agent can simply call it again with a
  different description if the first answer wasn't enough. No orchestration needed.

**Verified end to end**: asked "what have I already tried for my cow's skin
problem?", the agent called the tool unprompted (`about='the skin problem on her
cow'`) and answered using detail that exists *only* in the expanded field
("neem-oil wash twice… a powder you bought locally… neck and shoulders"). Separately
confirmed the always-injected block does **not** contain that detail — 708 chars,
headlines only — so the layering genuinely holds and expanded text isn't leaking
into every turn.

Alongside 1 and 2, the agent is also handed **what extra details exist on record for
this farmer** (the metadata keys and their values), so it knows what it can ask for
rather than having to guess. Farmer-scoped, cheap, injected every turn.

---

## Memory service API

### Reading (all farmer-scoped, all respect the on/off flag)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/memory/{farmer_id}/search` | **Level 2.** Quick search over *headline* vectors only. Body: `{query, limit, type?, status?, only_current?}` |
| `POST` | `/memory/{farmer_id}/search_expanded` | **Level 3.** Deeper search over *expanded* vectors. Same body. Meant for a deliberate tool call, may be multi-step |
| `GET` | `/memory/{farmer_id}/entries?type=&status=&only_current=&limit=` | Direct field filter, **no vector search** — e.g. "anything still open?" |
| `GET` | `/memory/{farmer_id}/keys` | **Agent-safe.** Which metadata keys exist for *this* farmer, their descriptions, and this farmer's own values |

`farmer_id` is applied **in code** on every one of these — never passed in a filter a
caller controls, so a query structurally cannot reach another farmer's memories.

### Writing (the background job's surface)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/memory/{farmer_id}/entries` | Write a new entry. Never overwrites |
| `PATCH` | `/memory/{farmer_id}/entries/{id}` | Update = close out the old version (`valid_to` set) **and** write a new one, so history is preserved |
| `POST` | `/keys/doc` | Record what a newly invented key means. Body: `{key, description, example_values}` |

### On/off per farmer

| Method | Path | Purpose |
|---|---|---|
| `PUT` | `/memory/{farmer_id}/settings` | `{"memory_enabled": false, "note": "..."}` |
| `GET` | `/memory/{farmer_id}/settings` | Check one farmer |
| `GET` | `/settings` | Everyone with an explicit flag, and who's switched off |

Stored in Qdrant next to that farmer's own memory — one source of truth, no separate
flag store. **Default is on** (within the bot's global `MEMORY_ENABLED` switch), so
the flag exists mainly to switch specific farmers *off*. Enforced in the service: a
farmer who's off gets empty results from every read path, whatever was asked. A
*failed* flag lookup also returns nothing, so the failure mode is never "memory
leaked for someone disabled."

### Ops / review (NOT for the agent)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/keys` | Every metadata key in use across **all** farmers — counts, sample values, which are undocumented |
| `DELETE` | `/keys/{key}` | Drop a key from every entry that carries it, plus its doc |
| `GET` | `/due?within_hours=24` | Entries lapsing soon — the trigger for proactive follow-ups |
| `GET` | `/health` | Collection status, entry count, embedding model |

`GET /keys` crosses farmer boundaries (its sample values come from other people's
entries), so it must never be handed to the agent — that's what
`/memory/{farmer_id}/keys` is for.

---

## Entry shape

**System fields** (what the service filters on — stable, don't let the model write
these): `farmer_id`, `type` (`profile` | `complaint` | `booking` | `health_note` |
`tracker` | `derived`), `status` (`open` | `resolved` | `pending` | `n/a`),
`times_raised`, `headline`, `expanded`, `valid_from`, `valid_to`, `expires_at`,
`source_session_id` / `source_ts` (a pointer back to the conversation, not a copy),
`built_from` (entry ids a derived conclusion came from).

**`metadata`** — one nested object for everything else. The model invents keys here
freely; they can never collide with a system field. Still filterable later via
`metadata.some_key`.

### Three timelines, kept deliberately separate

Conflating these is the easiest way to get memory wrong, so the field names now say
which is which (an earlier version called record time `valid_from`/`valid_to`, which
invited exactly that confusion):

| Fields | Timeline | Known? | Used for |
|---|---|---|---|
| `recorded_at` / `superseded_at` | **Record** time — when *we* wrote or replaced a record | Always | Bookkeeping and versioning only. **Never shown to the agent, never used for date filtering** — after a backfill every entry shares the same `recorded_at`, so it says nothing about when anything happened |
| `source_ts` / `first_source_ts` | **Event** time — when the farmer actually said it, and when the thread first came up | Almost always | The only thing date filters use. `first_source_ts` is preserved across updates so "how long has this been going on" is answerable from the current version alone |
| `expires_at` | **Real-world** validity end — but only the narrow, knowable case | Rarely | Expiry and `GET /due`. Not a "when was this true" filter |

**Real-world "true since / true until" is deliberately NOT a filterable field.** It's
unknown for most facts, so filtering on it would silently drop nearly everything. It
stays in the text, where the uncertainty can be stated honestly ("started about ten
days ago") rather than flattened into a date that looks precise.

**Undated entries are always included in a date-filtered search**, flagged "date not
recorded" — an invisible relevant memory is a worse failure than an imprecise date.

### Only the latest version is ever searched at runtime

`only_current` defaults on and the recall tool hardcodes it, so a superseded version
(e.g. `times_raised: 4` after it became 5) is never returned to the agent. Old
versions are reachable only by explicitly asking for history. Verified.

### Hybrid search: dense + sparse, tunable

Every entry carries four vectors: dense `headline`/`expanded` (meaning, via Marqo's
multilingual model) and sparse `headline_kw`/`expanded_kw` (literal word overlap).
Searches run both and blend them with `MEMORY_HYBRID_ALPHA` (default `0.6` dense /
`0.4` keyword — the same knob shape Amul's Marqo config already exposes).

Both sides are scored on **absolute** scales, not normalised within the result set:
dense uses raw cosine; sparse uses the *fraction of the query's own keyword weight
that matched*. Two bugs came from getting this wrong first time — within-set
normalisation turned a lone strong keyword hit into 0.00 and a weak one into a
perfect 1.00, because the score depended on whatever else happened to match.

Measured behaviour (α=0.6):

| Query | Top hit | dense | keyword |
|---|---|---|---|
| "neem oil" (exact term in the text) | the skin-problem entry | 0.82 | **1.00** |
| "1200 rupees" (exact number) | the deduction entry | 0.83 | **1.00** |
| "the animal is unwell and losing hair" (paraphrase) | correct entry ranked, keyword near zero | 0.80 | 0.00 |
| Gujarati paraphrase | the skin-problem entry | 0.81 | 0.00 |

So exact terms and numbers are caught by the keyword side, paraphrases and Gujarati
by the dense side — which is the point of having both.

**Known gap**: the sparse side uses a stopword list, not real inverse-document-
frequency weighting. Without corpus statistics, moderately common words are still
over-weighted relative to rare ones. Worth closing before production; adequate for
testing.

---

## How the bot integration works

In `app/services/chat.py`, memory is fetched **concurrently with the existing Soil
Health Card lookup**, so it adds no sequential wait to a turn:

```python
shc_ctx, mem_ctx = await asyncio.gather(
    get_session_shc_context(session_id, loan_mobile),
    fetch_memory_context(loan_mobile, processing_query),
)
```

`fetch_memory_context` (in `app/services/memory.py`) then runs the three level-1/2
reads in parallel, and builds one bounded prompt block:

1. `GET /memory/{id}/entries?type=profile` → the standing summary
2. `POST /memory/{id}/search` → the top headline matches for this question
3. `GET /memory/{id}/keys` → what else is on record

It **never raises**: any failure or timeout (2s default) returns an empty string, so
a memory problem cannot delay or break a turn. Output is capped
(`MEMORY_MAX_CHARS`, default 1200) so memory can't quietly eat the prompt budget.

The block is attached to `FarmerContext.memory_context` and rendered in
`get_user_message()` alongside the existing SHC block — framed as something to
**confirm, not assert**, and explicitly told never to claim what did or didn't happen
outside the chat (principles 3, 6, 7).

**Config** (bot side): `MEMORY_ENABLED` (global switch, default off),
`MEMORY_API_URL`, `MEMORY_TIMEOUT_SECONDS`, `MEMORY_TOP_K`, `MEMORY_MAX_CHARS`.

**Observability**: every turn logs `memory_used=true|false`, which is what makes the
with/without comparison auditable.

---

## What's verified working

- Write → retrieve by English **and Gujarati** query (cross-language retrieval
  confirmed: a Gujarati question retrieved an English entry about the same animal).
- `status: open` filter with no vector search; update → old version closed out, both
  versions retained, open-filter correctly goes empty.
- Expiry: an entry lapsing tomorrow counts as current, one that lapsed two days ago
  doesn't, and `GET /due` surfaces the former.
- Farmer isolation: another farmer sees nothing.
- Per-farmer flag flipped in Qdrant between two runs of the *same* question, no
  restart anywhere — `memory_used` flipped accordingly, and the replies differed
  visibly (memory on: *"the skin problem is persisting… it hasn't improved"*; off:
  generic advice).
- Model-invented keys are immediately filterable, visible in `GET /keys` (with
  undocumented ones flagged), and removable via `DELETE /keys/{key}`.

## What's not built yet

- **The background extraction/"dreaming" job** — the whole write side. Everything
  currently stored was hand-written to test the plumbing; nothing has been extracted
  from the 2,736 real turns sitting on disk. This is the piece where the real
  uncertainty lives.
- **The semantic filter tools** (`check_open_issues` and friends) — the API supports
  the filters; the agent isn't wired to call them.

## Worth knowing

Moderation runs **before** memory injection, so a turn blocked by moderation never
reaches the agent and never sees memory (observed while testing: "why was money
deducted from my account?" was classified non-agricultural and short-circuited).
Relevant when picking demo queries.
