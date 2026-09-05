# Amul Memory Design

**See `log-findings.md` first** — real cases mined from 8 heavy-repeat farmers' actual
prod conversations, grounding everything below in observed behavior rather than
hypotheticals. In particular, its Case 8 (a farmer left believing a vet visit was
already booked when it never was, across a 12-day worsening animal-health case) argues
that booking/action-state continuity is not an optional nice-to-have here — it's the
single highest-priority scenario found.

## Current state (verified directly against `amul-oan-api@main`, checked 2026-09-04 —
## supersedes `Amul_understanding.md` where they disagree)

Amul (`voice-oan-api` + `amul-oan-api`) has **no conversational memory today** — same
gap as `bharat-oan-api`, not `mh-oan-api`. Everything that looks like "memory" is
actually live external profile data, refetched and cached, not facts the bot has
derived from what a farmer has said in past conversations:

- **Conversation history**: Redis, keyed by `session_id`, TTL is
  `HISTORY_CACHE_TTL_SECONDS` (default **2 hours**, refreshed on every turn) —
  `app/config.py:166-173`. This is shorter-lived than `Amul_understanding.md`'s 24h
  figure; treat 24h as stale. `session_id` is client-supplied, per-call/per-thread —
  nothing here maps it to farmer identity across sessions.
- **Farmer/animal profile** (`agents/services/farmer_cache.py`, `agents/farmer_context.py`):
  a stale-while-revalidate cache over Beckn/PashuGPT/CVCC/Banas APIs — farmer record,
  animal data, vet visit history, AI-technician info — keyed by a SHA-256 hash of
  phone number. Soft refresh 12h (found) / 2h (not-found), hard retention nominally 7d
  per the module's own docstring but `farmer_animal_api_cache_ttl` in `app/config.py`
  is set to **17 days** — this discrepancy is unresolved in the code itself, worth a
  quick check before relying on either number. Either way: this is re-fetched source
  data, not conversation-derived memory — no timestamps-per-fact, no "what we told this
  farmer last time," no state tracking of *changes* the farmer has reported.
- **Soil Health Card context**: `soil_health_card_context` on `FarmerContext` — "bounded
  agronomic facts from this signed-in session's latest Soil Health Card." Explicitly
  session-scoped, not persisted across turns/sessions. Notable as a **precedent already
  in this codebase** for "small, curated, bounded context object injected into the
  prompt" — the shape any new memory injection should probably follow, not a new
  pattern to invent.
- **Identity**: normalized mobile number (`agents/tools/farmer_animal_backends.py::normalize_phone`),
  same mechanism mh-oan-api's `resolve_memory_user_id()` uses (phone-based, just not
  SHA-256-hashed at the `FarmerContext` level — the farmer-cache layer hashes it,
  `mobile` on `FarmerContext` itself is plain). `signed_in: bool` is already a
  first-class field, gating which tools/context a turn gets.
- **Two personas, not one**: `FarmerContext.persona: Literal['farmer', 'doctor']`.
  `doctor` is the **Amul Veterinary Assistant** — a separate audience (vets, not
  farmers) doing clinical decision support on cattle/buffalo/calves, with its own
  system prompt (`assets/prompts/doctor_system_translation_pipeline.md`) and identity
  response (`app/services/identity_profile.py`). **This matters for memory design**: a
  vet's useful "memory" (case history for a specific animal across visits, prior
  diagnoses/treatments) is a different shape from a farmer's (herd-level facts,
  recurring concerns, advice already given) — any design here needs to say which
  persona(s) it's for, not assume "Amul memory" means the farmer persona only.

So this is a **greenfield build**, not an extension — unlike `mh-oan-api`, there's no
existing mem0/Qdrant scaffolding here to build on.

## What's different about Amul vs. mahaVistaar (why this isn't a copy-paste)

1. **Voice-first, latency-sensitive.** The voice pipeline nudges the caller
  ("please wait") specifically because tool calls introduce audible delay. Any memory
  recall step that's a live LLM call (vs. a cached lookup) adds latency on a channel
  where that's directly felt mid-sentence.
2. **Two backends, one identity.** `voice-oan-api` and `amul-oan-api` are separate
  services sharing a farmer (by mobile) — the farmer-cache layer already does this
  (chat and voice share the same Redis key per phone). Memory needs the same property:
  identity-keyed and reachable from both, not owned by one service's local state.
3. **Two personas.** Farmer and doctor (see above) — decide scope explicitly.
4. **Signed-in vs. not is already first-class** (`signed_in: bool`, gates
  `farmer_info`/tool access) — the same guest/no-memory gate mh-oan-api uses can reuse
  this existing field, not a new concept.
5. **A curated-context precedent already exists** (`soil_health_card_context`) — bounded,
  session-scoped, injected as a labeled block ahead of the query. Any memory injection
  should look like this, not a raw history dump.
6. **Domain is narrower and more factual** — herd composition, specific animals (ear
  tags), AI-call/vet-visit history — arguably easier to schema than general
  BharatVistaar advisory topics, closer to mh's structured "crop facts" than free-form
  chat.

## Guiding principle: the compute budget is asymmetric, not uniformly tight

Stated explicitly because it changes how the rest of this doc should be read: **latency
only matters during the live turn itself.** Outside that window, cost is not a
constraint worth designing around.

- **Pre-session and post-session: unlimited.** As many LLM calls, as much reasoning
  depth, as much token spend as the case needs — background consolidation
  (Honcho-Dreamer-style deductive/inductive passes, or a hand-rolled equivalent),
  escalation flagging, follow-up-ledger updates, whatever it takes to make the *next*
  session smarter. None of this is felt by a farmer mid-call, so none of it should be
  scoped down for latency reasons. Spend freely here.
- **During the live turn: the constraint is "no added sequential wait," not "no LLM
  calls."** A memory-related LLM call made *during* a turn is fine **if it runs in
  parallel with the main agent generation** — exactly the pattern this codebase already
  uses for content moderation (`FarmerContext`'s `_moderation_task`/`ensure_in_scope()`
  in `agents/deps.py`: moderation runs concurrently with the agent, and side-effecting
  tools await it only at the point they'd actually act). What's not fine is a *sequential*
  hop the farmer has to wait through before the response can start.
- **Practical consequence**: don't design the "deep reasoning" memory capability as
  something the live agent calls and blocks on mid-turn (softening the framing in
  "Recall strategy" below — a nudge-covered tool call is still a sequential wait from
  the farmer's perspective, just a disguised one). Instead:
  - Kick off any deep/expensive memory read **as soon as identity resolves** (the
    moment a call connects or a session opens, before the farmer has even finished
    speaking their first turn) and run it in parallel with STT/greeting/whatever
    already happens first — by the time it's needed, it's ready.
  - Do the actual hard consolidation reasoning **after the session ends**, updating
    the record for *next* time — same shape as `farmer_refresh_worker.py`'s existing
    background-refresh pattern, just refreshing derived memory instead of raw farmer
    data.
  - Only genuinely synchronous, in-turn context (the low-latency
    `FarmerProfile`-equivalent read, or Honcho's `representation()` — see below) needs
    to be cheap enough to sit directly on the hot path, because nothing else is
    available to parallelize it against at that exact moment.

This reframes the earlier Honcho-vs-custom cost comparison too: the "unlimited off-turn
compute" principle applies equally to both options, so Honcho's Dreamer-style background
reasoning isn't something to ration for cost/latency reasons — the actual tradeoff
remains build-vs-adopt (do we want to write and tune that consolidation logic ourselves,
or use Honcho's), not "can we afford to run it."

## Design options

### Option A — Custom, mem0-style (port mh-oan-api's pattern)

Reuse the two-layer split mh-oan-api runs in production today, refined per
`future_work/memory/memory-design-decisions.md`'s proposed changes (post-session
writes, fixed schema, timestamps/state-tracking for the profile; reconciled
topic-chunk episodic memory).

- Pro: proven in this org already (mh-dev), same team knows the failure modes
  (additive-only drift, preload-reliability gap), and the "small curated bounded
  context" shape already matches this repo's `soil_health_card_context` precedent.
- Con: build + own it — reconciliation logic, chunk merging, retention policy all
  bespoke; mh's own version doesn't have these refinements built yet either, so Amul
  would be prototyping the *next* iteration of an unproven design, not copying a
  finished one.

### Option B — Honcho (`github.com/plastic-labs/honcho`) as the memory layer

Self-hosted (AGPL-3.0, FastAPI + Postgres/pgvector, `docker compose up`) memory
infrastructure, peer-centric:

- **Peer** = farmer (or vet, for the doctor persona — Honcho's peer model is
  general-purpose, not farmer-specific), keyed by the same normalized mobile already
  resolved today. **Session** = a call or chat thread. **Messages** = turns.
- Storage (sync, via API) is separate from Insights (async, background "deriver"
  worker) — messages get stored immediately, reasoning/representation-building happens
  off the critical path. Maps cleanly onto this repo's existing pattern of doing
  bounded, pre-built context injection (`farmer_info`, `soil_health_card_context`) —
  adding `session.add_messages(...)` alongside the existing post-turn Redis history
  write is additive, not a pipeline rework.
- Two retrieval shapes, which matter given the latency constraint:
  - `peer.representation(...)` — **static, low-latency snapshot, no LLM call at read
    time**. This is the one for voice preload (equivalent to mh's
    `preload_farmer_profile()`), since it doesn't add a live-inference hop mid-call.
  - `peer.chat(...)` — reasoning-informed natural-language query, but itself an LLM
    call — closer to a recall *tool* the agent can choose to invoke (nudge covers the
    latency, same as any other tool call in this codebase), not something to call
    unconditionally every turn.
- Gets timestamped, reasoning-derived "conclusions" and session summaries for free —
  the exact thing mh's reconciliation proposal is trying to hand-build.
- Con: new infra dependency (Postgres+pgvector, a deriver worker, its own LLM calls for
  reasoning — real cost/ops to evaluate), AGPL-3.0 license (check before shipping in a
  product context), and it's schema-agnostic/general-purpose — doesn't give Amul a
  `FarmerProfile`-style fixed-field schema out of the box; would still need
  Amul-specific prompting/schema on top (via its conclusions/chat API) to get
  herd-specific structured facts rather than free-form conclusions.

#### What Honcho actually differentiates on, vs. what we already have

Worth being precise about this, since raw vector storage and raw LLM access are **not**
the differentiator — both already exist here (Qdrant is already stood up locally for
this work; `mh-oan-api` already runs mem0-over-Qdrant in production; `amul-oan-api`
already has full LLM access wired in via `app/llm_core`). If Honcho only meant "a vector
DB plus an LLM call," it would add nothing worth the new infra.

What it does add:

- **The reasoning/consolidation pipeline itself** — an async worker that keeps
  extracting "conclusions" from conversation and updating a per-peer representation
  over time. This is *exactly* what `future_work/memory/memory-design-decisions.md`
  proposes hand-building for mahaVistaar (Option 2: topic-chunk merging, in-place
  updates, temporal reasoning) — Honcho ships a version of this already built and
  tuned, not something to design from scratch.
- **A natural-language query interface over accumulated history** (`peer.chat(...)`) —
  this is what would actually answer "has this farmer raised this deduction before, how
  many times, still unresolved?" (`log-findings.md` Cases 2, 6, 7). Plain
  similarity-threshold recall doesn't produce that on its own; something has to reason
  over the retrieved history. Honcho ships that reasoning step; a custom build means
  writing and maintaining our own version of it.
- **Session summarization "for free"** — `knowledge/mh-oan-api-memory.md` flags "no
  forced end-of-session consolidation" as a real, current gap in mh's own memory
  system; Honcho's deriver does this automatically.

What it does **not** solve, regardless of which option is picked: `log-findings.md`
Case 8 (a farmer left believing a vet visit was already booked, across a 12-day
worsening animal-health case) needs an explicit action/commitment ledger — tracking
whether a stated booking actually happened and never letting the bot's own language
imply otherwise. Neither Honcho nor a custom mem0-style store does this out of the box;
it's bespoke engineering either way, on top of whichever memory layer gets chosen.

### Recommendation (not decided — for discussion)

Case-driven, not a blanket pick — the log-findings cases split cleanly by which option
actually helps:

- **Cases 3, 4, 9** (stable facts, disambiguation, anomaly-vs-baseline) need only a
  **structured "FarmerProfile"-equivalent** (herd composition, last AI/vet call, which
  linked account is usually meant) — a small, explicit schema (same shape as
  `soil_health_card_context`), stored as a plain cached KV doc. **Must be a low-latency
  read, never a live reasoning call, on the voice channel** — this part doesn't need
  Honcho at all; Option A (or even simpler, no vector store) covers it.
- **Cases 2, 6, 7** (unresolved-thread escalation — the same complaint recurring for
  weeks with no acknowledgment) are where Honcho's reasoning pipeline earns its keep —
  this is genuinely hard to hand-build well, and is close to Honcho's actual job.
  Worth prototyping Honcho specifically for this layer, gated on resolving the
  AGPL/self-hosting question first.
- **Case 8** (booking/action-state continuity — the single highest-priority finding)
  is orthogonal to this whole decision and needs its own explicit design (a commitment
  ledger: was this action actually completed, don't say "waiting on the doctor" unless
  it's true) — don't let picking a memory backend substitute for solving this.
- **Case 5, 10** (proactive follow-up, volunteered financial data) need timestamps +
  a follow-up mechanism on top of whichever store is chosen — an incremental add either
  way, not a differentiator between options.

Net: if the priority is the unresolved-thread/reasoning cases, Honcho is worth the added
infra. If the priority is the stable-fact and booking-state cases, a narrow custom
build gets there with far less new infrastructure to operate. Starting position for
discussion, not a decision — flagging explicitly per this org's style of asking before
committing on an architecture call.

## Recall strategy (voice-specific tradeoff, from mh's still-open question)

mh-oan-api's own open question — model-driven tool call vs. unconditional retrieval
every turn — resolved here per the **compute-budget principle above**: a nudge-covered
mid-turn tool call is still a sequential wait from the farmer's perspective, so it's not
the preferred shape even though the codebase already has the pattern available.

- **Structured profile layer**: a cached, zero-LLM-call preload, kicked off the moment
  identity resolves (mirroring mh's `preload_farmer_profile` and this repo's own
  `farmer_info`/SHC-context pattern) — cheap enough to sit directly on the hot path
  regardless of which option gets built.
- **Episodic/"deep" recall**: not a mid-turn tool call the agent waits on. Prefer
  triggering it in parallel with whatever already happens first in a session (STT,
  greeting) so it's ready by the time it's needed, or doing the reasoning
  post-session so the *next* call starts already informed. A live, nudge-covered tool
  call is the fallback for the rare case that genuinely can't be anticipated, not the
  default design.

## Open questions

- Farmer-profile-cache retention: 7d (module docstring) vs. 17d
  (`farmer_animal_api_cache_ttl`) — which is actually authoritative? Doesn't block
  memory design directly but worth resolving since any memory-retention policy will
  get compared against it.
- Scope: farmer persona, doctor persona, or both? Different memory shape for each
  (herd-level vs. per-animal case history) — needs a decision before schema work
  starts.
- AGPL-3.0 licensing implications of self-hosting Honcho in this product — a real
  check, not just a technical one, before treating Option B as viable.
- Cost/ops of running Honcho's Postgres+pgvector+deriver worker alongside the existing
  Redis-only footprint — justified for Amul's traffic volume specifically vs.
  BharatVistaar/mahaVistaar?
- Does memory apply to guests at all, or signed-in only (mirroring mh's guest-gate,
  and this repo's existing `signed_in` field)? Leaning signed-in-only, not decided.
- Voice-vs-chat parity: same memory for both channels from day one, or does one lead?
