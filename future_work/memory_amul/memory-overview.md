# Amul Memory — Overview (start here)

This is the one-stop version of everything we've worked out so far about giving
Sarlaben (Amul's dairy-farmer chatbot) memory of past conversations. It pulls together
the design thinking, real examples from actual farmer conversations, made-up examples
to stress-test the idea, and the memory-technology comparison (Honcho / Graphiti /
build-it-ourselves) — all in one place, in plain language.

**Status: technology decided, mechanics worked out.** Every example below has a
priority, the feature ideas from that review (proactive follow-ups, a background
"notice patterns" step, a general-purpose tracker) are written up as their own
sections (3b and 3c), and Section 5/6 now cover the actual decided approach — build it
ourselves on the vector database (Qdrant) already running, not Honcho or Graphiti —
plus how the two decisions that come with that (what's worth storing, and how to tell
an update from something new) actually get made. A couple of policy questions remain
(Section 7). Keep marking things up — this is still a draft.

The other files in this folder have more detail/sourcing if you want to dig into a
specific point: `memory-design-decisions.md` (the fuller technical write-up),
`log-findings.md` (exact dates/sessions for the real examples), `backtesting-plan.md`
(how we'd test any of this before shipping it).

---

## 1. Where things stand today

Sarlaben has **no memory of past conversations** right now. Every time a farmer calls
or opens the chat, the bot starts from zero — even for someone who's called every day
for months.

What it *does* have, which can look like memory but isn't:
- **A live lookup of the farmer's records** — herd, milk payments, animal details —
  fetched fresh from Amul's own systems each time. This tells the bot *facts about the
  farmer's account*, not anything about what was actually *discussed* before.
- **A short-lived chat history** — but it only lasts 2 hours, and a new phone call or a
  new app session almost always starts a brand new one anyway.

So today: no memory of what was said, no memory of unresolved problems, no memory of
anything the farmer told the bot that isn't already sitting in some other Amul system.

---

## 2. Guiding principles

A few rules that should shape any memory design, regardless of how it's built. The
first five were the original starting point; 6, 7, and 8 came directly out of the
review below and later discussion, and are now just as load-bearing.

1. **Speed only matters during the actual call or chat message.** Anything that
   happens before a call connects, or after it ends, can take as long and cost as much
   as it needs to — a farmer never feels that. The only thing to keep fast is whatever
   happens *while someone is waiting for an answer*.
2. **During a live call, don't make the farmer wait for memory.** If we need to look
   something up, do it either (a) instantly — a simple, cheap lookup, not a slow
   "thinking" step, or (b) in the background, at the same time as something else that's
   already happening (like how the bot already checks a message isn't against the
   rules *while* it's also generating a reply, not before). Never add a new wait purely
   for memory.
3. **Remembering the wrong thing is worse than not remembering.** A wrong guess about
   what a farmer meant, a stale fact treated as current, or a memory that misreads a
   farmer's concern (see Example 6) does real damage to trust — more than just staying
   quiet would have.
4. **Not everything should be remembered.** Some things a farmer says are sensitive —
   money troubles, something they'd rather the cooperative not know, a mistake they
   made. Remembering everything forever, and letting all of it flow into every system
   that touches this bot, could make farmers stop telling it the truth. What to keep,
   for how long, and who else can see it needs a real, deliberate answer — not a
   default of "keep everything." **This is the single highest-priority principle in
   this whole document** (see Example F3).
5. **Keep "hard facts" and "things we've noticed" separate.** A farmer's cooperative,
   how many animals they have, which of two linked accounts they usually mean — these
   are simple facts that don't need any clever reasoning, just a lookup. Things like
   "this farmer has asked about the same unresolved problem three times" are a
   different kind of memory — they need some actual thinking to notice, not just a
   lookup.
6. **When memory gives you a guess, confirm it — don't state it as fact.** Instead of
   "you're from Banas cooperative" (which is embarrassing if wrong), ask "are you
   calling about your Banas account, like usual?" — the farmer just says yes or no.
   Same effort saved, but wrong memory can't mislead anyone (Examples 3, 4).
7. **Memory only knows what happened in this chat — it is not the farmer's whole
   life.** Never assume something didn't happen just because it's not in memory (a
   farmer may have booked a vet visit some other way entirely). Track status as "not
   confirmed in this chat," never as a flat "this didn't happen" (Example 8).
8. **Never store raw identifying numbers.** No ear tag numbers, no exact account or
   transaction IDs, in the memory system itself. Describe things instead ("a
   recurring deduction around ₹1,200, mid-August" rather than quoting the exact
   ledger line-item ID) — enough to be useful without creating a second copy of
   identifying data that already lives, properly secured, in Amul's real systems. If
   an exact ID is ever genuinely needed, look it up live from those systems at that
   moment — don't duplicate it into memory just in case.

---

## 3. What we're actually building — feature areas

### 3a. Farmer-facing memory — three layers

- **Quick facts** — cooperative, animal count/species, which linked account they
  usually mean. Looked up instantly, no search needed. Used per principle 6: to phrase
  a confirmation, not to state a fact outright.
- **Case status** — for anything that spans multiple visits (an unresolved complaint,
  a sick animal, a pending booking): a compact, current record — what it's about, when
  first and last raised, how many times, what's been tried, and its status. Per
  principle 7, status should read like "not confirmed booked in this chat" rather than
  "not booked" — never claim certainty about the world outside this chat.
- **A general tracker** (from Example B2) — not tied to one topic. A farmer can save
  and update information about anything over time — feed costs, a treatment's
  progress, cash flow — and ask about it later. One reusable feature instead of a
  one-off for each topic.

### 3b. "Memory x Reasoning" — proactive, scheduled follow-ups

A capability, not just a data store: the bot (or the background reflection step, see
3c) can decide something is worth checking on later, and follow up without being
asked.

**Core building block**: a reminder/check-in ticket — farmer, a trigger (a date, or a
condition like "when this scheme opens"), and what to check or say. A simple scheduler
(same shape as background jobs already in the codebase, e.g. `scheme_scheduler.py`)
watches for due tickets and either sends a message or preps context for the farmer's
next call.

**Feature list (draft — add to this as more comes up):**
- Re-check a stuck status later (e.g. "is this payment still not showing up?") and
  follow up instead of just repeating "I don't know" every time (Example 1).
- A health follow-up nudge — "did the advice help," or flagging something that's gone
  unusually long without resolution (Example 5).
- A withdrawal-period reminder after a vet treatment (Example A2) — opt-in, e.g. "want
  me to remind you daily until tomorrow not to use this milk?"
- A vaccination-window reminder, timed to when it's actually useful, not after the
  fact (Example C2).
- A scheme/subsidy window watch (Example C3) — but re-confirm the farmer still wants
  it before acting, don't assume an old wish is still true.
- A loan-reassessment watch (Example B1) — framed as the farmer opting in, not the bot
  pushing debt.

**Guardrails (non-negotiable, not optional polish):**
- Always opt-in — ask before scheduling anything, never silently.
- Never for routine or low-stakes things (we explicitly rejected doing this for a
  simple dropped call — see Example D2 below).
- Easy to turn off, and stop offering something a farmer has declined repeatedly
  (Example F2) — be deliberate about *when* to prompt a farmer at all; every proactive
  message costs their time and attention.

### 3c. What the background reflection ("dreaming") step should also produce

This step already has to run after every conversation to update the memory above — per
Section 2, principle 1, that's unlimited-budget background work. These are additional,
essentially free outputs of the same pass, all **Amul-facing, not farmer-facing**:

- **Redacted, aggregated "recurring problem" summaries across farmers** (Example 2) —
  not useful to any individual farmer in the moment, but valuable for Amul to see
  patterns (the same unexplained deduction type hitting many farmers, say) without
  exposing any one farmer's identity.
- **Content-gap and grievance tagging** (Example 9) — a running list of things the bot
  couldn't answer well, or complaints that came up, stored in its own collection for
  Amul to review and use to improve the bot.
- **A draft glossary/translation-correction queue** (Example D3) — when a farmer
  corrects the bot's wording, draft that as a suggested glossary entry for a human to
  verify, not a silent live behavior change.

---

## 4. Real examples, sorted by priority

We pulled real conversations for 8 farmers who use the bot a lot (checked in daily or
almost daily over a month) and read through everything they said, looking for moments
where remembering something from before would have made a real difference. Exact
dates/quotes are in `log-findings.md`. Made-up examples (letter-numbered, A1 through
F3) are invented, not from logs — see Section 6 in the previous version of this doc /
`log-findings.md` for why they were written.

### High priority

**Example F3 — Some things this bot should probably never keep.**
Farmers will sometimes tell this bot things that are true and risky for them to have
on record — a side-sale outside the cooperative, a financial struggle. If any of that
could ever reach the cooperative or a bank, farmers will learn to stop being honest
with it.
**Decision:** High priority. We should be careful with what we store — never store
anything a farmer could be uncomfortable with later. This is the top constraint on
everything else in this document (principle 4).

### Medium priority

**Example 3 — Asked "which cooperative are you with?" even after the bot already knew.**
**Decision:** Medium. This is a case where downstream tool calls depend on getting the
cooperative right, so we shouldn't just silently trust memory — instead store it and
use it to ask a yes/no confirmation ("are you calling about your Banas account?")
instead of the open question. Protects against wrong memory while still saving the
farmer effort (principle 6, Section 3a).

**Example 4 — Asked "cow or buffalo?" when the bot already knew the answer.**
**Decision:** Medium. Same pattern as Example 3 — use memory to propose the likely
answer and get a confirmation ("should I book this for your cow?") rather than asking
the open question or silently assuming.

**Example 6 — Misunderstood a farmer's real worry and made it worse.**
**Decision:** Medium. A good use case, though this instance is partly tangled up with
a translation issue too. General principle: if the bot makes a mistake a farmer calls
out — especially if they're upset about it — it should remember that and not repeat
it. Needs a cheap search over memory to surface the right past instance when the
farmer calls again.

**Example 8 — A farmer believed help was already on the way, when it wasn't (our top
safety concern).**
**Decision:** Medium (capped from higher due to the caveat below, not because it
matters less). Important caveat: memory is not the farmer's whole universe — the fact
that a booking never completed *in this chat* doesn't mean the farmer didn't get help
some other way, so we must never assert "you never got a vet" as fact (principle 7).
What this case actually needs is a compact, current case-status record — e.g. "cattle
fell sick [date], tried these home remedies so far, no vet booking confirmed in this
chat despite being offered 11 times" — so the bot can speak contextually ("this seems
to have gotten worse since last time, may be worth calling a doctor") without
overclaiming what actually happened.

**Example 9 — Something suddenly looked wrong, with no explanation.**
**Decision:** Medium. Gives a more contextual answer, though it doesn't fix the
underlying issue by itself. The bigger idea this surfaces: the background reflection
step is already "looking at everything" anyway, so it should also tag issues, farmer
grievances, and content gaps into a separate store while it's at it (Section 3c) — no
extra infrastructure needed, we're already writing its output somewhere.

**Example 10 — Useful details given once, then gone.**
**Decision:** Medium. Generalizes into its own feature — a "tracker" a farmer can use
to save and check on any topic over time (Section 3a), not just feed costs. Two open
questions this raises, not yet settled: (1) should we tell the farmer outright when
we're drawing on something they said before, rather than silently using it — leaning
yes, but not decided (see Section 7); (2) what should be automatically injected into
every turn vs. only fetched when relevant vs. only pulled by the bot actively
searching — assume there really are three different budget tiers here, not one.

**Example B2 — A farmer tried something new and never found out if it worked.**
**Decision:** Medium. This is really the same "tracker" feature as Example 10 — let a
farmer save and check on cash flow, a treatment's progress, or anything else over
time. One reusable primitive, not a one-off.

**Example C1 — Personal breeding-season advice, not generic advice.**
**Decision:** Medium. Worth tying memory to the farming/breeding calendar specifically
— this can be built into whichever memory approach we pick (agent- or rule-driven).

**Example C2 — Bringing up vaccination at the right time, sensitively.**
**Decision:** Medium. Memory can track which vaccinations are done and which are
pending, feeding the proactive-reminder feature (Section 3b).

**Example C3 — Remembering a wish, for when it becomes possible.**
**Decision:** Medium. Gives useful context for a later, related question — if a
farmer's mentioned wanting something before, we can surface it directly when relevant
info comes up (a scheme, a subsidy), instead of starting from zero.

### Low priority (real cases, but blocked on the Section 3b/3c features existing first)

**Example 1 — Told "I don't know" the same question, over and over.**
**Decision:** Low, for now. Each time, we'd still need to actually re-check the
status via a tool call to see if anything changed — so on its own this only improves
*tone*, not the actual answer. The real fix is proactive: periodically re-check status
in the background and get back to the farmer (Section 3b) — that's the version worth
prioritizing, not tone-polish alone.

**Example 2 — The same unexplained money deduction, asked about for weeks, never
resolved.**
**Decision:** Low for the farmer-facing angle specifically — noticing this doesn't
directly help the farmer get an answer we don't have. But the underlying pattern
(multiple farmers hitting similar unresolved issues) is exactly the redacted,
aggregated analytics feature in Section 3c — worth doing, just as an Amul-facing
feature, not a farmer-facing one.

**Example 5 — A serious animal-health issue nobody followed up on for 10 months.**
**Decision:** Low until Section 3b exists — this needs the ability to schedule
messages from the model, which we haven't built yet. Otherwise a strong example; once
proactive follow-up exists (possibly as part of the background reflection/"dreaming"
step deciding to check in), this becomes a good candidate.

**Example 7 — Same complaint, raised again and again for three weeks, never
connected.**
**Decision:** Low, same reasoning as 1 and 2. We'd track the complaint, how many times
it's been raised, and its status — but without the ability to actually act on that
(scheduled checks, escalation), this currently only improves tone.

**Example A2 — Forgetting a treatment could spoil milk for a whole village.**
**Decision:** Low, tied to Section 3b existing. A fair, real use case — but should be
something the bot explicitly offers ("want reminders until tomorrow?") rather than
something it just does.

**Example B1 — Told "no" for a loan, and never told when that changes.**
**Decision:** Low, tied to Section 3b. There's a real limit here too — we don't know
everything about the farmer's situation — but for scheme/loan deadlines specifically,
offering to remind the farmer when a window opens or closes is a reasonable, opt-in
version of this.

**Example D3 — Learning how a specific person talks, to stop mishearing them.**
**Decision:** Low. Somewhat useful for understanding mistranslations/corrections —
best framed the same way as Section 3c: when a farmer corrects the bot's grammar or
translation, draft it as a glossary suggestion for human review, not a live
auto-correct.

**Example F2 — Checking back on advice, and knowing when to stop offering something.**
**Decision:** Low, folded into Section 3b's guardrails — be very deliberate about when
to prompt a farmer at all, with real limits on frequency, rather than treating this as
a standalone feature.

### Deferred — revisit later, not now

**Example E1 — Spotting a possible disease outbreak early.**
**Decision:** Real idea, worth doing later — not now. Cross-farmer, so it carries the
sharpest privacy requirements in this whole document if it's ever built.

### Out of scope for now

- **Example A1** (vets seeing a full cross-visit case history) — not in scope for us
  right now.
- **Example D1** (telling apart multiple people sharing one household phone) — too
  risky; getting this wrong (e.g. leaking one family member's info to another) is
  worse than not attempting it.
- **Example D2** (texting a farmer after every dropped call) — avoidable; people
  usually already know when a booking didn't go through, and this would mostly just be
  annoying.
- **Example E2** (grading a specific technician's outcomes) — not required, and risky
  (grades a real person using data outside their control).
- **Example F1** (assuming an animal died and going silent about it) — too risky to
  act on an unconfirmed inference; if this is ever built, it needs an explicit
  farmer confirmation first, never a silent guess.

### Things that look like memory problems but aren't

A few repeated questions turned out to be **not** memory issues at all:
- Some farmers ask the same routine question ("today's milk total") many times a day —
  that's supposed to be looked up fresh every time, not remembered.
- One farmer got a slightly different number each time they asked the identical
  question within the same hour — that's a data-accuracy bug, not a memory gap.
- A couple of account labels were literally garbled/broken in the system — memory can't
  fix a broken label, only a real data fix can.

Good to keep in mind so we don't try to "memory-fix" things that are actually a
different kind of problem.

---

## 5. Which memory technology — decided: build it ourselves, on Qdrant

Three real options were weighed: build it ourselves on the vector database (a
database built for fast "find similar things" lookups) already running for this work
— Qdrant — or adopt one of two ready-made products, **Honcho** or **Graphiti**. This
section is the comparison; Section 6 covers how the "build it ourselves" approach
actually works in practice.

**A definition worth pinning down first, since it comes up a lot below: "agentic
search."** A normal lookup is one fixed step — turn a question into a search, get
results, done. Agentic search means an AI decides, step by step, what to look up
next — it tries one search, looks at what came back, decides whether it needs to
check something else, and keeps going on its own judgment until it thinks it has
enough to answer. That's real, and it's genuinely smarter for open-ended questions —
but it's also slower (several AI steps instead of one), and we've decided we don't
need it for a live conversation (Section 2, principles 1 and 2).

### The plumbing (extraction) is roughly the same everywhere — but two separate
decisions hide inside it

All three approaches do the same basic thing to *remember* something: read a
conversation, have an AI pull out what matters, save it. But that single step is
actually two separate decisions, and it's worth being precise about which tools help
with which:

1. **What's worth storing at all.** Checked directly: none of these tools have real
   built-in judgment for this. Honcho's own extraction instruction, by default, is
   closer to "write down everything explicitly stated" — broad, not curated — the
   only way to narrow it down is a plain-language instruction we write ourselves and
   hand to it, which is the same work as writing our own extraction prompt from
   scratch. Graphiti and a from-scratch build both need this written by us too. This
   part of the decision really is a wash across all three.
2. **Whether something is an update to an existing memory, or genuinely new.** Here
   the tools actually differ. Honcho has real, automatic duplicate-checking built in
   — it compares a new fact against existing ones by meaning (not just exact text)
   and can skip or replace accordingly. That's a real, working version of something
   we'd otherwise have to build by hand (see Section 6). Graphiti goes further still —
   it doesn't just detect a duplicate, it tracks *when* a fact stopped being true and
   keeps the old version as history rather than deleting it.

### Infrastructure — corrected and compared directly

- **Build it ourselves** — uses the vector database (Qdrant) already running for this
  work, plus the LLM access the bot already has. **No new infrastructure at all.**
- **Graphiti** (the open-source engine behind Zep) — is a plain code library, not a
  separate program we'd have to run — we'd call it directly from our own background
  job. It does need **one new thing: a graph database.** The default is Neo4j, which
  is a real, separate database system to run and maintain — more than we want.
  **But it doesn't have to be Neo4j** — Graphiti also supports FalkorDB, which speaks
  the Redis protocol (Amul already runs Redis, so this is much less unfamiliar
  territory), and there's even an embedded version with no separate server process at
  all — though that specific version needs a newer Python than the bot currently runs,
  so it's not free today.
- **Honcho** — needs the most: **a full separate database engine (Postgres, which
  nothing in Amul's stack runs today) plus its own dedicated Redis plus a permanently
  running background program of its own**, on top of everything we already operate.
  To be clear, since this was a point of confusion: **Honcho does not use Qdrant** —
  Qdrant only shows up in the "build it ourselves" option, because that's the database
  we already have and chose to build on.

**So, ranked by new infrastructure, lightest to heaviest: build-it-ourselves <
Graphiti-with-FalkorDB < Graphiti-with-Neo4j < Honcho.** Honcho is the heaviest of the
three, not the lightest — worth being clear about since it's easy to assume the
"ready-made" option is also the leanest one.

### Retrieval speed — do we need "search and reason," or just a fast lookup?

Since we don't need agentic search (see the definition above):
- **Build it ourselves**: one fast lookup, no AI call at read time. Exactly what we
  want.
- **Graphiti**: also one fast lookup, no AI call at read time — confirmed directly
  from its own code, it combines a quick similarity search and keyword search, nothing
  more, and is built for sub-second responses. Same speed class as building it
  ourselves.
- **Honcho**: has both a fast, no-AI-call option (similar to the above) *and* a
  slower, agentic option that does take extra time — the fast option is fine for us,
  but the reason people reach for Honcho at all (the smart multi-step search) is the
  part we've said we don't need.

### How much structure you get "for free" — and where Honcho falls short of what we want

- **Build it ourselves**: fully free-text unless we write our own structure — the
  most control, but the most work up front.
- **Honcho**: **always** free-text notes, no structured fields at all — this doesn't
  change no matter how it's configured. Even the automatic duplicate-checking
  mentioned above stays in free-text form. So even if we used Honcho, we'd still need
  to build our own layer on top to get real fields like `status: open` — it doesn't
  give us the structured, fast-to-check shape we actually want, in any configuration.
- **Graphiti**: this is its real advantage — you can define simple structured types
  (e.g. "a complaint has a status and a count") as plain building blocks, and its
  already-written extraction step fills them in automatically, plus automatically
  retires an old fact when it changes instead of piling up old and new side by side.

### Why we're not using either ready-made option — the infrastructure problem

Both Honcho and Graphiti need a database capable of "find similar things" search
built in — and that's exactly what Qdrant already does for us. Checked directly in
Graphiti's own code: there's no way to point it at Qdrant and just use a graph
database for structure — the two are bundled together by design. So adopting either
one means running a *second* database that duplicates something we already have
running, on top of whatever else that database needs (Graphiti's lightest option,
FalkorDB, is still a new service; Honcho needs a new database engine plus its own
cache system plus a permanent new background program — the heaviest of the three by
a clear margin).

### Decided: build it ourselves

Given neither ready-made option gives us real structured storage without new
infrastructure, and the two things Honcho *does* give for free (duplicate-checking,
and to a lesser extent Graphiti's history-tracking) are both realistically cheap to
build ourselves on top of Qdrant (see Section 6) — the decision is to build this
ourselves. Zero new infrastructure, reusing what's already running and already
trusted elsewhere in the org (`mh-oan-api` runs its own memory system on Qdrant in
production today).

---

## 6. How this actually gets built

The overall shape: **a small background job**, separate from the main chatbot
program, that after each conversation (or every so often) reads what was said, decides
what's worth keeping, and saves it into Qdrant (already running). **During a live call
or chat**, one fast, simple lookup — no "thinking" step, no extra wait — adds a short
block of context to the top of the conversation, the same way the bot already does
for other short context blocks today. No new software to run at all.

Within that shape, two decisions have to be made deliberately — neither Honcho nor
Graphiti would have made these for us either, so this is real work either way, not
something lost by not adopting them.

### Decision 1 — what's worth storing

This comes from an explicit instruction sheet we write for the background job, not
something an AI figures out by itself. Concretely, it should say:
- Here's the fixed list of things worth remembering: a stable fact about the farmer
  (cooperative, animal count), an open issue/complaint, a requested action and its
  real status, a health note, something the farmer explicitly volunteered (like feed
  costs). Extract only things that fall into one of these categories — not everything
  said.
- Only extract something if it would actually matter in a *future* conversation —
  don't just restate what's already sitting in the farmer's live account record
  (that's re-fetched fresh every time anyway, no need to duplicate it).
- **Never extract**: anything from principle 4/Example F3 (side-sales, admissions of
  anything risky, pure venting with nothing actionable) — and, per principle 8, never
  the exact raw ID of anything (ear tags, transaction numbers) — describe it instead.

This list isn't invented from nothing — it's a direct translation of Section 4's
taxonomy and Section 2's principles into rules an AI can actually follow.

### Decision 2 — is this the same thing as before, or something new

The harder one. A new fact might be worded completely differently from an existing
memory about the same underlying issue (Example 7's "12 animals, only 5 show online"
vs. "0 milking animals" are the same complaint, said two different ways). Since we're
not storing raw IDs to match on (principle 8), this has to be done by meaning:

1. Before saving something new, the background job searches that farmer's *existing*
   current entries of the same category for anything that looks like the same
   underlying thing.
2. If there's a close match, don't blindly trust a similarity score — hand the
   candidate matches to the same AI step and ask it to explicitly decide: is this an
   update to one of these, or genuinely new?
3. **When it's a close call, default to "new," not "same."** A duplicate is mildly
   noisy (a problem logged twice) and easy to clean up later. A wrong merge is worse —
   it could make an *actually new* problem look like something already being tracked
   and quietly ignored. This follows straight from principle 3: getting it wrong is
   worse than not remembering.

This is a real, working version of the automatic duplicate-checking Honcho has built
in — worth being honest it's not *nothing* to build, but it's a modest, well-defined
piece of logic, not a reason on its own to take on Honcho's infrastructure.

### Keeping a history, the way Graphiti does — without a graph database

Graphiti's trick is: never overwrite a fact in place, mark the old version as no
longer current and add a new one instead, so nothing is ever silently lost. That's
easy to copy on Qdrant directly — give every memory entry two extra tags: **when this
version became true**, and **when it stopped being true** (empty if it's still
current). When something changes, update the old entry's "stopped being true" tag to
right now, and add a fresh entry for the new version. Reading "what's true right now"
= look for entries with an empty "stopped being true" tag. Reading "the full history
of this issue" = look at every entry for that topic, in order. This also happens to
be exactly what the testing plan in `backtesting-plan.md` needs — being able to see
what memory looked like *as of* a specific past date, not just what it says today.

### How search actually works when a farmer asks something, live

Every single lookup starts with "only look at this one farmer's own memories" —
never search across everyone's. Beyond that, there are three different shapes,
and using the right one matters more than making the search itself cleverer:

- **A known, stable fact** (cooperative, animal count) — no search at all, just read
  the field directly. Instant.
- **A known category, just not which specific entry** (the bot's about to book a vet
  visit, so it wants "any open booking for this farmer") — filter by category and
  "still current," no search needed — more reliable than a fuzzy search since it
  doesn't depend on wording lining up.
- **A genuinely open-ended question**, where we don't know in advance what it relates
  to — this is where a real similarity search earns its place: turn the question into
  something searchable, look only within that one farmer's own (small) set of
  memories, take the closest matches. Since it's already narrowed to one person's
  history, a plain search performs well without needing anything fancier layered on.

---

## 7. Open questions (not decided yet)

- **Do we tell farmers when we're using memory** — e.g. "as you mentioned before..." —
  or keep it invisible? Raised in Example 10, not settled.
- **What's the retrieval budget shape** — a fixed, small set of facts injected on
  every single turn no matter what, a cheap search triggered only sometimes, and
  (rarely) something more actively searched for — is that really three separate tiers,
  and if so, how big is each one allowed to be so memory doesn't quietly eat the token
  budget every turn?
- Does this cover just farmers, or also the separate vet-facing mode?
- Does a farmer who hasn't signed in get any memory at all, or none (like today)?
- Same memory for phone calls and the chat app, or does one come first?
- What exactly do we keep forever, what do we forget quickly, and who's allowed to see
  it? (Principle 4 and Example F3 — the highest-priority open question in this
  document.)

---

## 8. Your turn

Priorities are set, the technology decision is made (Section 5), and Section 6 covers
how it actually gets built. What's most useful next: (1) sanity-checking the "Medium
priority" bucket in Section 4 — that's the list that would actually get built first,
and (2) the open questions in Section 7, especially the transparency one.
