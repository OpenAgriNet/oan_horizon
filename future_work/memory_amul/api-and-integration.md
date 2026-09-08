# Memory — API reference and how it's wired into the bot

What's actually built and running, with paths. The design reasoning is in
`memory-overview.md`; this is the implementation surface.

Two pieces:
- **The memory service** — `/amulpfsdata/gautam/amul-memory/service/`, container
  `amul-memory-api`, `localhost:8100` (in-network: `http://amul-memory-api:8100`).
  The background writer lives beside it in the same repo, at
  `/amulpfsdata/gautam/amul-memory/dreamer/` — one repo, since the two halves share
  the entry shape and every storage rule.
  Stores and serves memory. Owns the per-farmer on/off decision.
- **The bot integration** — `amul-oan-api`, branch **`memory_v0`**:
  `app/services/memory.py` (the read + prompt-block builder), plus a small change
  in `app/services/chat.py` and `agents/deps.py`.

Storage: Qdrant (container `amul-qdrant`, `localhost:6350`), collection
`amul_memory`. The collection and its payload indexes are created by the service on
startup, so the store is reproducible from `memory_api.py` alone.

**Why there is a second service (Marqo) at all, when the store is Qdrant.** Qdrant
stores and searches vectors; it does not create them. Something has to turn "his
buffalo went off feed" into 1024 numbers — at write time, and again at query time,
with the *same* model both times, or the numbers aren't comparable and search
silently returns nonsense. That embedding call is the only thing outside Qdrant, and
it goes to the Marqo instance Amul already runs, using the same model as Amul's
knowledge base (`multilingual-e5-large`, 1024-dim). Two reasons: memory text is
frequently Gujarati, so an English-first model would be a poor fit (cross-language
retrieval was verified — a Gujarati memory is found by an English query and the
reverse); and it is already running and already the thing the rest of Amul embeds
with, so there is no second model to host or keep in sync. The alternative is to
bundle the model into the service and embed in-process — worth doing only if the
network hop becomes a problem, and it would have to be the same weights or the whole
collection needs re-embedding.

---

## The three levels, and how each one is served

| Level | What it is | How the agent gets it | Cost per turn |
|---|---|---|---|
| **1. Standing record** | Fixed 7-field schema, only the populated fields | **Injected automatically, every turn** | One document read by id — no search, no AI |
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
- **Signature is deliberately small**: `recall_more_detail(about, detail_key,
  detail_value)`. Date-range parameters were built and then removed — going back
  through the real log findings, no farmer ever asked what they'd *told the bot* in a
  given period (the "last 7 days" questions are about live milk data, not memory),
  and the one case that would justify them (comparing against the same season last
  year) belongs to a scenario that isn't built. Dates are still *visible* on every
  result, which is what actually does the work: the agent could answer "how long has
  this been going on" with no filter at all, just by reading them.
- `detail_key`/`detail_value` filter on the **dreamer-invented keys** — the mechanism
  agreed in `memory-overview.md`: the dreamer decides which keys exist, those keys
  become filterable, and the agent filters on top of them. Filters on system fields
  (`type`, `status`) were briefly added and reverted — nothing has demonstrated the
  agent needs them, and in testing it answered a listing question ("which schemes
  have I not been paid for") correctly from the injected Layer 2 context *without
  calling the tool at all*.

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
| `POST` | `/memory/{farmer_id}/search` | **Level 2.** Semantic search over *headline* vectors only. Body: `{query, limit, only_current?, type?, status?, metadata_key?, metadata_value?, since?, until?, include_undated?}` |
| `POST` | `/memory/{farmer_id}/search_expanded` | **Level 3.** Same, over *expanded* vectors. What the recall tool calls |

The service supports more filters than the agent's tool exposes (`type`, `status`,
`since`/`until`). That's deliberate: the service keeps them because they cost nothing
and the background job and ops views use them; the agent's surface stays minimal so
there are fewer untested paths in the model's hands.
| `GET` | `/memory/{farmer_id}/entries?type=&status=&metadata_key=&metadata_value=&only_current=&limit=` | Direct field filter, **no vector search** — e.g. "anything still open?". `status` repeats for OR (`&status=open&status=pending`). Reports `returned`/`truncated`, because "zero means zero" survives truncation but "this is all of them" does not |
| `GET` | `/memory/{farmer_id}/keys` | **Agent-safe.** Which metadata keys exist for *this* farmer, their descriptions, and this farmer's own values. Identifier-shaped keys (`animal_id`, account/transaction/phone) are stripped here — see the ID policy below |
| `GET` | `/memory/{farmer_id}/profile` | **Level 1.** The standing record. A point read by deterministic id, not a query. Returns only the populated fields |
| `GET` | `/memory/{farmer_id}/entries/{id}/history` | How an episode's account developed, oldest first — replaced versions (via `previous_version`) and folded consolidation fragments. What makes bounding safe: condensed detail stays reachable |

`farmer_id` is applied **in code** on every one of these — never passed in a filter a
caller controls, so a query structurally cannot reach another farmer's memories.

### Writing (the background job's surface)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/memory/{farmer_id}/entries` | Write a new entry. Never overwrites |
| `PATCH` | `/memory/{farmer_id}/entries/{id}` | Update = stamp the old version `superseded_at` **and** write a new one, so history is preserved. Accepts `source_ts` so an update advances *last mentioned* while `first_source_ts` keeps the start |
| `PUT` | `/memory/{farmer_id}/profile` | Replace the standing record. Body: `{fields: {...}, source_ts?}`. Unknown field names are ignored and reported back, so the schema cannot drift; the previous version is kept as history |
| `POST` | `/keys/doc` | Record what a newly invented key means. Body: `{key, description, example_values}` |
| `POST` | `/memory/{farmer_id}/entries/{id}/fold` | Retire a fragment into a consolidated entry. Body: `{merged_into, reason}`. Stamps `superseded_at` + `merged_into` **without** writing a replacement — PATCH is wrong for consolidation because it would leave a live entry per fragment. Nothing is deleted: a wrong merge has to stay diagnosable |

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
`tracker` | `derived`, plus two internal-only types the read paths always exclude:
`settings` and `profile_record` — note `profile_record` (the Level-1 standing record)
is deliberately **not** the same as `profile`, which is an ordinary remembered fact),
`status` (`open` | `resolved` | `pending` | `n/a`),
`times_raised`, `headline`, `expanded`, `recorded_at`, `superseded_at`, `expires_at`,
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
| `source_ts` / `first_source_ts` | **Event** time — when the farmer actually said it, and when the thread first came up | Almost always | **Shown to the agent, never filtered on.** `first_source_ts` survives updates, so "how long has this been going on" is answerable from the current version alone |
| `expires_at` | A known, actionable end date where the conversation gave one | Rarely | Shown to the agent, and `GET /due`, where the date IS the question |

### No date is ever used to hide a memory

**Amended 2026-09-08, after getting this wrong three separate times.** Recorded at
length because it looks like a missing feature rather than a decision:

- `since`/`until` range filters were built speculatively and **never called by
  anything**. Dead code on this axis.
- `valid_from`/`valid_to` were record time wearing the name of real-world validity,
  and had to be renamed `recorded_at`/`superseded_at`.
- `expires_at` was folded into `only_current`, which silently hid an **open** booking
  whose scheme deadline had passed — the case most worth surfacing, not least.

Three failures on one axis is evidence the abstraction was wrong, not that the
implementations were unlucky. Why it keeps failing:

- A date cannot tell you whether something is **resolved**. `status` can.
- `expires_at` is inferred from a conversation by a model, so it is a guess wearing
  the costume of a precise fact — and we were letting that guess delete things.
- **Filtering is silent and destructive.** An entry a filter removes produces no
  signal at all, so the assistant cannot reason about what it never saw. Showing the
  date instead lets it reason out loud — "that withdrawal period ended last week" —
  and say so to the farmer.

So dates are stored, indexed, and **shown**, framed for the model to judge: an end
date that has passed means that deadline or withdrawal period is over, **not** that
the matter was settled. A request still marked open is still open.

The one thing still filtered is `superseded_at`, and that is deliberately **not** a
date comparison — it is a version-state check (set or unset). Nothing is compared
against the clock.

### One date format, everywhere

`01-September-2026`, from a single function per repo
(`dreamer/dates.py`, `app/services/memory_dates.py`, asserted by test to agree).
Bare ISO is ambiguous read aloud and invites day/month confusion when spoken back in
Gujarati; twenty independent `[:10]` slices could each drift. Undated entries render
one explicit marker, never a blank that reads as a missing field.

### Only the latest version is ever searched at runtime

### Only the latest version is ever searched at runtime

`only_current` defaults on and both agent tools hardcode it, so a superseded version
is never returned. This survived the removal of date filtering precisely because it
is a **state** check rather than a date comparison — verified by test on all three
read paths (headline search, expanded search, exact listing), and folded
consolidation fragments are excluded the same way.

History is not lost, and is now **walkable**: an update records `previous_version`,
so `GET /memory/{id}/entries/{entry_id}/history` returns how an account developed,
oldest first, following both replaced versions and folded fragments. A current entry
whose account has been rewritten says so (`earlier_versions_available`), because a
reader who cannot tell whether they have the whole picture will assume they do.

### Search is semantic (dense) only — hybrid was built and backed out

A tunable dense+keyword hybrid was built, measured, and **deliberately removed**.
Worth recording why, so it isn't rebuilt the same way:

- The keyword side needs real inverse-document-frequency weighting to be useful. With
  only a stopword list, moderately common words stay over-weighted, so a paraphrase
  sharing filler words scored as a strong literal match.
- Getting the score scales wrong made it actively worse than plain semantic search:
  normalising each side *within its own result set* meant a score depended on
  whatever else happened to match — a lone strong keyword hit normalised to 0.00, a
  lone weak one to 1.00. Fixing that (absolute scales: raw cosine for dense, fraction
  of query keyword weight matched for sparse) worked, but the IDF gap remained.

**All of the keyword machinery has since been deleted** (2026-09-08) — the
tokeniser, the English+Gujarati stopword list, the crc32 sparse embedder, and the two
sparse vectors that were being written on every entry. It was dead weight sitting in
the write path of every single memory, and the live collection was migrated to
dense-only vectors to match. Keeping it "ready to switch back on" was not worth the
code: if hybrid returns it needs corpus IDF and a measurement, which is a different
implementation anyway, not this one re-enabled.

**Search is therefore semantic only, and the store holds two vectors per point** —
`headline` and `expanded`, both 1024-dim cosine.

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

1. `GET /memory/{id}/profile` → the standing record (Level 1)
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

## Deliberately removed (so it isn't rebuilt by accident)

- **Hybrid dense+keyword search** — built, measured, removed. Needs real IDF first.
  See the search section above.
- **Date-range parameters on the agent's tool** — no observed use case; dates stay
  visible on results instead, which covered the actual need.
- **`type`/`status` parameters on the agent's tool** — filtering rides on the
  dreamer-invented keys instead, per the agreed design. The service still supports
  them for background/ops use.

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

---

## Identifiers: what is stored, and what the agent can see

Amended 2026-09-08. Account numbers, transaction ids, phone and registration numbers
are **not stored at all** — memory holds descriptions ("a deduction of around ₹1,200"),
not ledger references.

**An animal's ear tag is the exception, and it is stored on purpose.** It is the one
identifier that does work for memory instead of just duplicating a record: it makes
"is this the same animal as last time?" a certainty rather than a guess, which is what
per-animal clinical continuity needs. Semantic matching cannot reliably separate "her
black buffalo" from "the other black buffalo"; a tag can, and the match step uses it —
same tag means same animal, different tags mean a genuinely new entry regardless of how
alike the wording is.

It never reaches a conversation, and that is enforced in three places rather than by
asking a model nicely:

| Where | What stops it |
|---|---|
| The dreamer's extraction prompt | Instructed to put the tag in `metadata.animal_id` only, never in `headline`/`expanded` |
| The dreamer, after extraction | Checks the prose for the tag and moves it out if the model put it there anyway (`_strip_ids_from_prose`) |
| The memory service, `GET /memory/{id}/keys` | Strips `animal_id` (and account/transaction/phone keys) from the agent-facing key list, so the always-injected block can never carry it |

The prose is the only thing the agent reads back to a farmer, so **a tag that is never
in the prose can never be spoken.** The rule in short: store the tag, match on the tag,
never say the tag.

---

## Embedding: store memories as documents, queries as questions

`multilingual-e5-large` is trained **asymmetrically** — a stored passage and a
question about it are meant to be encoded differently. Amul's own knowledge-base
search already does half of this (`MARQO_USE_E5_QUERY_PREFIX`,
`agents/tools/search.py:137`); the memory service originally did neither, embedding
stored memories and incoming queries identically.

Marqo exposes the distinction through `content_type`, so that is used rather than
hand-prepending `passage: ` / `query: `. The measurement that settled it:
`content_type=query` is **identical** to plain text (cosine 1.000000), so the side
that was actually wrong was the *write* path — memories were being stored encoded as
though they were questions.

Four combinations were measured on a labelled set of realistic memory headlines and
real farmer questions:

| Config | Right memory returned | Relevant avg | Routine avg | Separation |
|---|---|---|---|---|
| store raw, query raw (original) | 9/10 | 0.833 | 0.779 | 0.054 |
| **store document, query query (chosen)** | **10/10** | 0.828 | 0.786 | 0.042 |
| store `passage:`, query `query:` (manual) | 9/10 | 0.829 | 0.781 | 0.048 |
| store document, query `query:` | 10/10 | 0.825 | 0.786 | 0.040 |

So it improves **ranking** — which memory comes back — and does nothing for absolute
scores. That matters for the next section.

The convention is part of `EMBED_MODEL_ID` (`.../doc-query`), because a store written
under the old symmetric convention is not comparable with queries under the new one.
`reembed.py` rebuilt the existing vectors; old vectors cannot be converted, only
recomputed.

## A score threshold does not work — measured, twice

**Finding (2026-09-08): score-based gating cannot separate "this is on record" from
"nothing like this is on record" here.** Recorded because it is counter-intuitive and
will otherwise be attempted again.

Calibrated on the real store via `search_expanded` (the Level-3 path), with 11
agent-style recall queries whose answer *is* on record and 9 about topics the same
farmer never raised:

| | n | range | mean |
|---|---|---|---|
| should find something | 11 | 0.768 – 0.875 | 0.825 |
| should find nothing | 9 | 0.741 – **0.852** | 0.785 |

The distributions overlap heavily. "The mastitis treatment" — nothing remotely like
it on record — scored **0.852**, higher than 7 of the 11 genuine recalls.

| Floor | Keeps real recalls | Blocks false ones |
|---|---|---|
| ≥ 0.78 | 10/11 | 4/9 |
| ≥ 0.82 | 5/11 | 8/9 |
| ≥ 0.86 | 3/11 | 9/9 |

A *relative* margin (top hit must beat the runner-up) was tested as an alternative
and is no better: margin ≥ 0.005 keeps 10/11 but blocks only 1/9; margin ≥ 0.02
blocks 6/9 but keeps only 6/11.

**Why**: every memory and every query sits in the same narrow domain (one farmer,
dairy, vet, payments), so cosine similarity measures *topical* closeness, not whether
this specific thing is on record. Everything scores 0.74–0.88. The signal simply
isn't in the number.

**Consequence**: relevance for Level 3 has to be decided by something that can read
the text, not by a number — or, better, avoided entirely by using a structured filter
where the question is actually structured (see Section 6 of `memory-overview.md` on
field filtering). A filtered lookup has no false-positive problem at all: no entry
with `status=open` means zero rows, definitively, not a weak vector match.


---

## The live agent's two memory tools, and why both exist

| Tool | For | Guarantee |
|---|---|---|
| `recall_more_detail` | A fuzzy question about one situation — "the skin problem on her cow" | Best matches, ranked. Says nothing about completeness |
| `list_remembered_items` | A structured question about state — "is anything still open" | **Zero rows means definitively zero**, and it says so in words |

They are not alternatives. The second exists because of a measurement: a query about
a treatment nothing on record resembles scored **0.852** while genuine recalls ranged
0.768–0.875, so from a score alone "no strong match" and "nothing on record" are
indistinguishable. Asked for pending bookings, a search returns whatever is closest
and the agent cannot tell whether that is all of them, some, or none. A field filter
can, so an empty result is stated as complete — otherwise the agent hedges, or retries
with a search.

`list_remembered_items` defaults to `state="unresolved"`, which is open OR pending in
one query rather than two plus a union the model has to compute. An unknown state or
category is rejected without troubling the service.

Both share the same safety shape: **the farmer is never a parameter** (it comes from
signed-in deps), both are hidden when memory is off or no farmer is resolved, neither
raises, both are bounded, and both report truncation.

## Nothing the agent pulls is cut mid-text

The recall tool used to slice its output at a character count. That halves a sentence
and says nothing about what was removed — and it was happening on real data, where
three entries came to 1532 characters against a 1500-character cap. A half-stated
memory is worse than one fewer memory.

Bounds now sit in two places, neither of them a character slice:

- **Write time, by re-synthesis.** An account past `MEMORY_EXPANDED_SOFT_LIMIT`
  (1500 chars) is condensed by a model — off any live turn, where there is no latency
  budget and something can actually decide what earns its place. Nothing is lost:
  every earlier version is kept and walkable, so what a condensation compresses stays
  recoverable.
- **Read time, by dropping whole entries** and saying how many were dropped.

The injected Layer-1/2 block is still bounded (`MEMORY_MAX_CHARS`, 1800 — raised from
1200 when dates were added to each line), but it now drops whole lines, refuses to
leave a section header with nothing under it, and states that something was left out.

## Tests

`amul-memory/run_tests.sh` — 71 stdlib-unittest tests, no model calls. Unit tests run
anywhere; integration tests skip when the service is down. They pin the behaviours
that regress **silently**: the embedding document/query convention (break it and
search still works, it just stops meaning anything), identifier stripping,
trace-level idempotency, `times_raised` counting occasions rather than writes, exact
listing keeping lapsed-but-open entries, cross-farmer isolation, and memory-off
returning nothing.
