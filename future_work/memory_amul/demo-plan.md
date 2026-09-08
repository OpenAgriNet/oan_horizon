# Amul memory — demo plan (and what's already running)

The goal here is narrower than `backtesting-plan.md`: get a working, believable demo
on real farmers' data, and get an early read on whether memory helps or quietly hurts.
`backtesting-plan.md` is the full, rigorous version to do once this looks promising.

Two things to show:
1. **Live**: be one of these farmers, chat with the bot, and watch it actually use
   what it remembers.
2. **Side by side**: take that same farmer's *real* later questions and answer them
   twice — with memory and without — and compare.

---

## Already built and running (no setup needed to start)

- **Qdrant** — container `amul-qdrant` on the `amul-network` docker network,
  reachable at `localhost:6350`. Collection `amul_memory` is created with the design
  from `memory-overview.md` Section 6: two named vectors per entry (`headline` and
  `expanded`) and filter indexes on `farmer_id` / `type` / `status`.
- **A memory API** — container `amul-memory-api` (source in
  `/amulpfsdata/gautam/amul-memory-api/`), at `localhost:8100`. A thin service over
  Qdrant implementing exactly the Section 6 design:
  - `POST /memory/{farmer_id}/entries` — write an entry (never overwrites).
  - `POST /memory/{farmer_id}/search` — the quick, every-turn search (headline
    vectors only).
  - `POST /memory/{farmer_id}/search_expanded` — the deeper search, meant to sit
    behind a deliberate tool call.
  - `GET /memory/{farmer_id}/entries?type=…&status=…` — direct field filter, no
    vector search ("anything still open?").
  - `PATCH /memory/{farmer_id}/entries/{id}` — update by closing out the old version
    (sets `valid_to`) and writing a new one, so history is never lost.
  - `farmer_id` is applied **in code** on every read path — a query structurally
    cannot reach another farmer's memories.
- **Embeddings** come from the Marqo instance and model Amul's own knowledge base
  already uses (`multilingual-e5-large`, 1024 dimensions) — deliberately, since
  memory text is often Gujarati and an English-first model would be a poor fit.
  Verified working: a Gujarati query ("મારી ગાય બીમાર છે, ડૉક્ટર ક્યારે આવશે?")
  correctly retrieves an English-language memory entry about the same sick animal.
- **The bot itself** — `amul_app` is already running locally against this same
  network, so the demo can point at it directly.

**Verified end to end**: write an entry → retrieve it by English *and* Gujarati query
→ filter it by `status: open` with no vector search → update it to `resolved` and
confirm the open-filter goes empty while both versions remain in history → confirm a
different farmer sees nothing.

**One known external issue**: the OpenAI key in `amul-oan-api`'s `.env` is out of
credits. It isn't needed for memory (embeddings come from Marqo), but anything else
routed to OpenAI will fail until it's topped up.

---

## Step 1 — Pick the demo farmers

Their full 30-day transcripts are already pulled and saved locally, so no new data
work. Pick 4-5 with the richest cases from `log-findings.md` rather than all 8:

| Farmer | Why them |
|---|---|
| `...3048` | The sick-animal/booking saga — Case 8, our top-priority scenario and the clearest "memory changes the answer" moment |
| `...5963` | Asked a question the bot already had the answer to, plus the 10-month stale fertility follow-up (Cases 4, 5) |
| `...5951` | The misread anxiety complaint, plus the recurring registration grievance (Cases 6, 7) |
| `...7788` or `...3007` | The recurring unexplained deduction (Cases 1, 2) |
| `...7896` | Linked-account disambiguation, plus the anomaly case (Cases 3, 9) |

## Step 1b — The held-out set (picked, and deliberately not read)

The five farmers above are the ones whose conversations we've already read in detail
— which makes them exactly the wrong sample to judge the system on. Prompts written
while staring at their transcripts will fit *them*, not farmers in general.

So a second set is picked up front, **by activity volume only — none of their
conversation content has been looked at, and it shouldn't be while the extraction
prompts are being written.** Spanning different activity levels on purpose, so it
isn't all power users:

| Farmer | Volume band | Turns in the 30-day window |
|---|---|---|
| `...4693` | high | 190 |
| `...6314` | high | 166 |
| `...6793` | mid | 106 |
| `...3965` | mid | 83 |
| `...0108` | lower | 52 |
| `...8783` | lower | 36 |

(Full numbers are saved locally alongside the pulled transcripts; only the last four
digits appear here.)

**The discipline that makes this worth anything**: write the extraction instruction
sheet and the matching logic against the *first* five (and general principles), then
run it cold on these six and see what breaks. Anyone tuning prompts should avoid
opening these transcripts until after the first honest run — otherwise this set
stops being a test and becomes more training data.

## Step 2 — Pick a cutoff date, per farmer

Split each farmer's history into **before** (used to build up memory) and **after**
(held back as real test questions). Per farmer, not one global date — their activity
patterns differ.

For `...3048` specifically, put the cutoff right after the first afternoon's flurry
of sessions (~Aug 21). That leaves the real "until then, what medicine can I give the
cow?" follow-up (Aug 29) in the *test* set — exactly the moment we want to see
handled differently.

## Step 3 — Run the "dreaming" step over the before-cutoff data

This is the piece still to build (the API above is the storage layer, not the
extraction logic). Two scripts, matching `memory-overview.md` Section 6:

- **Extraction**: one AI call per session, following Decision 1's instruction sheet
  (the fixed list of what's worth storing, the never-store list, no raw IDs).
- **Matching**: Decision 2's logic — before writing, search this farmer's existing
  open entries of the same type, let the AI judge same-vs-new, default to "new" when
  it's a close call.

Then run it over each demo farmer's before-cutoff sessions in chronological order —
simulating exactly what would have accumulated if this had been live all along.

## Step 4 — The live demo

Point `amul_app` at the memory API: do the Layer 1/2 lookup at the start of a turn
and inject it, and expose the field-filter tools so the agent can check things like
"anything still open for this farmer." Mint a token for one of the demo farmers (the
`/auth/token-for-phone` flow already tested) and just chat past the cutoff date.

**Decided**: demo against the real accounts and real history — a masked stand-in
wouldn't actually show whether this works. Revisit before showing this outside the
team, and handle the data accordingly until then.

## Step 5 — The side-by-side comparison

For each demo farmer, take their **actual** post-cutoff questions from the logs and
run each one twice through the real agent: memory off, memory on. Read them side by
side. (Formal scoring per `backtesting-plan.md`'s axes can come later — for the demo,
a careful manual read is enough to see whether this is working.)

## Step 6 — The reliability check (the part that matters most)

Memory looking good on hand-picked cases proves very little. Three checks that
actually test whether it's safe to turn on:

- **A zero-memory control.** Run the same test for a farmer with no accumulated
  memory (set their cutoff before their first session). Memory-on and memory-off
  should be **identical** — nothing to retrieve means nothing should change. This is
  a basic correctness check: retrieval against empty memory must do nothing
  gracefully, never error, never invent content.
- **Routine questions must stay untouched.** Include several of each farmer's
  ordinary queries (the "today's milk total" kind — see `log-findings.md`'s boundary
  section). Memory-on should not meaningfully change these at all; they're supposed
  to keep hitting live data. Any difference here is a signal to investigate, not to
  wave off.
- **Test beyond the curated five.** These farmers were chosen *because* they had
  demo-worthy cases — the sample most likely to flatter the system. Spot-check 3-5
  more ordinary farmers from the wider pool to catch cases where memory does
  something unhelpful for someone whose situation matches nothing we designed for.

---

## How this gets built — decisions taken

- **Two pieces, deliberately split.**
  - The **background memory job** (extraction, matching, the "dreaming" step) lives
    in its **own repo**, separate from the bot. It has no business being inside the
    request-serving codebase — it runs on its own schedule, with its own model
    choices and its own failure modes.
  - The **integration into the bot** is built directly in **`amul-oan-api`**, on a
    branch called **`memory_v0`** — kept off the main line until it's proven.
- **Any model, for the background job.** The job should accept **either a local vLLM
  endpoint or OpenRouter**, switchable by configuration — not hardcoded to one
  provider. Two practical reasons: the OpenAI key currently in the repo's `.env` is
  out of credits, and (per `memory-overview.md` Section 5) structured extraction is
  more reliable on stronger models, so being able to point the background step at a
  better model than the one serving live chat is worth having from day one. Credentials
  for OpenRouter already exist in the usual place (`oan-brain/oan_creds/`).
- **Memory is switchable per farmer, at runtime — built and working.** Two levels,
  and deliberately **no flags in Redis** (see the engineering note in
  `oan-brain/style/swe-style.md`: if it's data, it belongs in a DB where it can be
  listed and inspected, not in an opaque cache key):
  1. **A single global switch in the bot's `.env`** (`MEMORY_ENABLED`) — nothing
     happens anywhere unless it's on.
  2. **A per-farmer flag stored in Qdrant**, in the same collection as that
     farmer's own memory. One source of truth, sitting with the data it governs.
     Default is **on** for everyone (within the global switch), so the per-farmer
     entry exists mainly to switch *specific* farmers **off** — which is exactly
     what the A/B comparison and the shared-account safety case need.
  - `PUT /memory/{farmer_id}/settings` `{"memory_enabled": false, "note": "..."}`
  - `GET /memory/{farmer_id}/settings` to check one farmer
  - `GET /settings` to list everyone with an explicit flag, and who's switched off
  - **Enforcement is in the memory service, not the bot**: when a farmer is off,
    every read path returns empty regardless of what was asked. A caller that
    forgets to check still gets nothing. A *failed* flag lookup also returns
    nothing, so the failure mode is never "memory leaked for someone disabled."
  - **Verified end to end**: same farmer, same question ("my cow still has that skin
    problem"), flag flipped in Qdrant between runs with no restart anywhere.
    Memory on → *"It sounds like the skin problem is persisting. Since it hasn't
    improved, your cow likely needs a professional medical examination."* Memory
    off → *"It seems your animal might need medical attention. Would you like to
    book a health call?"* — the continuity is visibly there in one and absent in the
    other, and a `memory_used=` field is now logged on every turn.
- **Never store raw identifying numbers.** Reaffirming `memory-overview.md` principle
  8, since it has to be enforced in the extraction prompt specifically, not just
  stated as a design intention: no ear tags, no account or transaction numbers — a
  description of the thing instead. The storage layer already documents this; the
  prompt has to actually hold the line.
- **Real farmer data for the demo, for now.** Decided: use the real accounts and real
  history rather than building a masked stand-in, since a synthetic version wouldn't
  show whether this actually works. Revisit before this is shown outside the team, and
  treat the data accordingly in the meantime.

## Open questions before starting

- How far back the "before" window should go — all 30 days of available history, or a
  shorter window, given a real deployment would accumulate far more than 30 days.
- Which specific model to default the background job to, of the ones actually
  available (a local vLLM model vs. something via OpenRouter) — the plumbing should
  support both regardless, so this is a tuning question, not a blocking one.
