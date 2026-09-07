# Amul Memory — Technical Design

This is the technical companion to `memory-overview.md` (start there for the
plain-language version, the priority-sorted examples, and the feature list). This file
has the code-level detail: exactly what exists today, why Amul is different from
mahaVistaar's memory system, and the final decision on what to build it with.

See `log-findings.md` for the real cases this is based on. Its Case 8 — a farmer left
believing a vet visit was already booked when it never was, across a 12-day worsening
animal-health case — is why "does the bot's wording match what actually happened" is
treated as the single most important thing to get right below.

## Current state (checked directly against the `amul-oan-api` code, 2026-09-04)

Amul (`voice-oan-api` + `amul-oan-api`) has **no memory of past conversations today.**
Everything that looks like memory is actually live data pulled fresh from other Amul
systems each time — not anything the bot has learned from talking to a farmer:

- **Conversation history**: kept in Redis, but only for **2 hours**, and only within
  one `session_id` — a new phone call or a new app session usually starts a fresh one
  anyway. (`app/config.py:166-173`, `HISTORY_CACHE_TTL_SECONDS`.)
- **Farmer/animal record**: a cache of the farmer's live account data (herd, vet
  visits, AI-technician info), refreshed every 12 hours if found, sooner if not.
  (`agents/services/farmer_cache.py`, `agents/farmer_context.py`.) This is re-fetched
  source data, not anything derived from conversation — no sense of "what we told this
  farmer last time."
- **Soil Health Card context**: a small, bounded block of facts pulled in for one
  session and then dropped — never carried across sessions. Worth noting as a
  precedent already in the codebase for "a short, labeled block of context added to
  the prompt" — the shape any memory should follow, not something new to invent.
- **Identity**: the farmer's phone number, already normalized and used as the lookup
  key for the record above — the same mechanism to key memory on, nothing new needed.
- **Two separate modes**: a `farmer` mode (the default) and a `doctor` mode — a
  separate, vet-facing clinical assistant with its own prompt and identity. Memory for
  a vet (case history for one animal across visits) is a different shape from memory
  for a farmer (herd-level facts, ongoing concerns) — any plan here needs to say
  clearly which mode it's for.

So this is starting from nothing — unlike `mh-oan-api` (Amul's sister product for
Maharashtra), which already has a working memory system to learn from, there's no
existing scaffolding here to extend.

## What makes Amul different from mahaVistaar (why we can't just copy its design)

1. **Voice-first, and speed matters.** The voice pipeline already tells callers
   "please wait" specifically because looking things up takes noticeable time. Any
   memory step that requires the bot to "think" before answering adds a delay a caller
   directly feels, mid-sentence.
2. **Two separate programs, one identity.** The phone and chat/app systems are
   separate pieces of software but need to share the same farmer's memory — the
   existing farmer-record cache already does this (both look up the same phone
   number), and memory should work the same way.
3. **Two modes** (farmer vs. doctor) — decide scope explicitly, don't assume "memory"
   automatically means both.
4. **Signed-in vs. not is already a built-in distinction** — the same on/off switch
   that already controls which tools/information a caller gets can gate memory too,
   nothing new to build for that part.
5. **There's already a working example of "small, bounded context block"** in this
   codebase (the Soil Health Card block mentioned above) — memory should be added the
   same way, not as a raw dump of everything ever said.
6. **The topics are narrower and more factual** — herd size, specific animals, vet
   visit history — genuinely easier to capture as a handful of clear fields than
   general open-ended advice topics would be.

## Guiding principle: speed only matters live, not before or after

**Latency only matters while a farmer is actually waiting for an answer.** Outside
that exact window, cost isn't something to design around.

- **Before a call starts, and after it ends: no limit.** As much processing, as many
  AI calls, as much time as it takes — a farmer never feels any of this. Background
  work (updating memory after a call, checking whether something needs following up)
  should be done properly here, not rushed.
- **During the live turn: the rule is "don't add a new wait," not "no AI calls at
  all."** A memory-related AI call made *during* a turn is fine **if it happens
  alongside** the main reply being generated — the same way the bot already checks a
  message against moderation rules *while* it's also drafting a reply, not before. A
  new step the farmer has to wait through before the reply even starts is what to
  avoid.
- **In practice, this means:** don't design memory as something the live bot "looks up
  and waits for" mid-conversation. Instead, either (a) start any deeper memory lookup
  the moment the caller's identity is known — in parallel with whatever already
  happens first (like the initial greeting) — so it's ready by the time it's needed,
  or (b) do the real thinking *after* the call ends, so the *next* call starts already
  informed. Only the cheapest, simplest lookup (a plain fact check, no "thinking"
  step) belongs directly in the live turn, because nothing else is available to run it
  alongside at that exact moment.

## Decision: build it ourselves, on the vector database already running for this work

Three options were seriously considered — building it ourselves on a vector database
(a database built for fast "find similar things" lookups; we already have one, called
Qdrant, running for this work), a ready-made product called **Honcho**, and another
called **Graphiti** (which stores memory as a small knowledge graph rather than plain
records). Full comparison notes are in `memory-overview.md` Section 5. The short
version of why we're not using either ready-made option:

- **Honcho needs the most new infrastructure of the three** — a whole new type of
  database (Postgres, not used anywhere in Amul's stack today) plus its own separate
  cache system plus a permanently-running background program of its own. Its real
  advantage (a genuinely smart way of answering "has this come up before, how many
  times") is real, but not worth that much new infrastructure for a bot that doesn't
  need that specific capability as its top priority.
- **Graphiti needs a graph database** (Neo4j, or a lighter alternative called
  FalkorDB) as a new piece of infrastructure. Its real advantage (defining simple
  structured fields and getting them filled in automatically, plus automatically
  marking old facts as no-longer-true when something changes) is genuinely useful —
  but **it stores its own copy of the same kind of "find similar things" data Qdrant
  already handles for us**, checked directly in its code — there's no way to make it
  use Qdrant for that part while just using the graph database for structure. So
  adopting it means running a second database that duplicates something we already
  have running.
- **Qdrant is already proven inside this org** — `mh-oan-api` runs it in production
  for its own memory system today, and another product (`docs-pipeline`) uses it too.
  It's not new to the org, just new to Amul specifically. Building on it adds **zero**
  new infrastructure to Amul's stack.

**What we give up by not using Honcho or Graphiti, and how to get it back cheaply:**
- *Automatic structured fields* (Graphiti's advantage) → instead, define a small,
  fixed set of fields ourselves (e.g. "a complaint has a status and a count") and
  store them as tagged data alongside each memory entry in Qdrant. Qdrant already
  supports this kind of tagged/filterable data — we just have to decide the fields and
  write the extraction step, which we'd have to do with any of these options anyway.
- *Automatically updating stale facts* (Graphiti's other advantage) → our own
  background job checks, each time it processes a conversation, whether an entry for
  that topic/farmer already exists and updates it in place (e.g. status: open →
  resolved) instead of blindly adding a new one. A small amount of logic, not a new
  system.
- *A genuinely smart way to notice "this has come up before, repeatedly"* (Honcho's
  advantage) → this is the one thing worth being honest we're not getting automatically.
  It's a real capability gap for the "unresolved complaint" style cases (see
  `log-findings.md` Cases 2, 6, 7) — but per the priority list in `memory-overview.md`,
  those are currently marked **low priority**, blocked on the proactive-follow-up
  feature existing first anyway. Worth revisiting if that priority changes.

**What neither option solves, regardless of what we pick:** Case 8 in `log-findings.md`
— making sure the bot's own words match what actually happened (never implying a
booking is confirmed when it isn't) — needs its own simple tracking (a plain "was this
actually done, yes or no" record), completely separate from whichever memory system
we build. This has to be built deliberately either way.

## How memory gets read during a call

- **Simple facts** (cooperative, animal count, which linked account): a plain,
  instant lookup, kicked off the moment the caller's identity is known — cheap enough
  to sit directly in the live turn regardless of anything else.
- **Anything deeper**: not something the live bot waits on mid-turn. Either started
  in parallel with whatever already happens first in a call (so it's ready in time),
  or reasoned about after the call ends so the *next* call already has it. A live,
  mid-call lookup is the fallback for a rare case that genuinely couldn't be
  anticipated — not the default design.

## Open questions

- Which of the two cache lifetimes for the farmer record is actually correct — 7 days
  or 17 days? (Two different places in the code disagree.) Doesn't block memory design
  directly, but worth resolving since a memory-retention policy will get compared
  against it.
- Scope: farmer mode, doctor mode, or both? Different shape of memory needed for each
  — needs deciding before the field/schema work starts.
- Does memory apply to callers who haven't signed in at all, or only to signed-in
  farmers? Leaning toward signed-in-only, not decided.
- Same memory for phone calls and the chat app from day one, or does one come first?
