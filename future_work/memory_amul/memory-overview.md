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
8. **Don't duplicate identifying numbers into memory — with one deliberate
   exception.** Account numbers, transaction IDs, phone and registration numbers are
   not stored at all. Describe things instead ("a recurring deduction around ₹1,200,
   mid-August" rather than the exact ledger line-item ID) — enough to be useful
   without creating a second copy of identifying data that already lives, properly
   secured, in Amul's real systems. If an exact ID is genuinely needed, look it up
   live at that moment.

   **The exception is an animal's ear tag, and it is stored on purpose** (decided
   2026-09-08). It is the one identifier that does real work for memory rather than
   just duplicating a record: it turns "is this the same animal as last time?" from a
   guess into a certainty, which is exactly what per-animal clinical continuity needs
   (Examples 8 and 10). Semantic matching cannot reliably tell "her black buffalo"
   from "the other black buffalo"; a tag can.

   It is stored under two hard constraints, both enforced in code rather than left to
   a prompt instruction:
   - **It lives only in structured metadata (`metadata.animal_id`), never in the
     `headline` or `expanded` prose.** The prose is what the assistant reads back to
     the farmer, so an ID that is never in the prose can never be spoken. The dreamer
     checks the prose and moves an ID out if the model put one there anyway.
   - **The agent is never shown it.** The farmer-scoped key list that gets injected
     every turn strips `animal_id` (and any other identifier-shaped key) before the
     agent sees it. The tag is bookkeeping for the dreamer's matching step; the
     conversation always uses the farmer's own words — "her cow", "the one that calved
     in June".

   So: **store the tag, match on the tag, never say the tag.**

---

## 3. What we're actually building — feature areas

### 3a. Farmer-facing memory — three layers, all time-stamped

- **Layer 1 — the standing record.** A handful of short facts about the farmer that
  hold across conversations. There is exactly one per farmer at a fixed address, so
  it is a direct document read — no search, no ranking, nothing to get wrong. Used
  per principle 6: to phrase a confirmation, not to state a fact outright. Kept up to
  date by the background reflection step (Section 3c).

  **The fields are fixed and identical for every farmer** (decided 2026-09-08). A
  free-form "write up ~200 words about this farmer" summary was rejected: it drifts in
  shape between farmers, it grows, and there is no way to tell whether a given farmer's
  version is missing something or simply had nothing to say. The schema is:

  | Field | What it holds |
  |---|---|
  | `name_used` | What the farmer is actually called in conversation |
  | `usual_account` | Which linked account they mean by "my milk" — a *preference*, not the account list |
  | `language_register` | Which language, and short answers vs. full explanations |
  | `animal_references` | The words they use for their own animals, so the bot can use them back |
  | `usual_topics` | What they normally contact about, across several separate chats |
  | `standing_sensitivities` | Something that should change tone every time — a loss, a long grievance. Rare |
  | `explicit_requests` | Anything they directly asked the bot to remember, or to stop doing |

  **Only the populated fields are stored and injected.** A farmer we barely know
  contributes one line, not seven empty ones — an empty field costs nothing, a guessed
  one is injected into every future conversation. In practice most farmers will have
  two or three.

  **What is deliberately NOT in here**, even though a "profile" obviously suggests it:
  village, district, union, how many animals they have and of what species, which
  accounts are linked, any milk or payment figure. All of that arrives from Amul's own
  systems on every single turn via `farmer_info`. Copying it into memory would only
  create a second, staler version of a fact we already have correctly — and it is the
  single easiest way for this system to start confidently telling farmers things that
  stopped being true weeks ago. **Layer 1 holds what we learned by talking to them,
  and nothing that can be looked up.**
- **Layer 2 — the memory index.** Everything that spans multiple visits (an
  unresolved complaint, a sick animal, a pending booking) — but stored as a short,
  2-sentence **headline** per entry, not the full detail. This is what gets searched
  automatically on every turn, based on the farmer's current question (a quick "find
  the closest few matches" lookup, not a full re-read of everything). Each entry
  carries a status per principle 7 ("not confirmed booked in this chat," never a flat
  "not booked"), and is added to or updated over time, not just written once (see
  Section 6 for exactly how).
- **Layer 3 — the expanded version.** The fuller detail behind each Layer 2 headline.
  Not searched automatically every turn — if a headline looks relevant, the bot makes
  a deliberate tool call to dig into it properly, which is allowed to be a more
  thorough, multi-step search (see Section 6) since it's no longer on the path every
  single turn has to wait through.
- **A general tracker** (from Example B2), living in Layer 2 — not tied to one topic.
  A farmer can save and update information about anything over time — feed costs, a
  treatment's progress, cash flow — and ask about it later. One reusable feature
  instead of a one-off for each topic.

### 3b. "Memory x Reasoning" — proactive, scheduled follow-ups

A capability, not just a data store: the bot (or the background reflection step, see
3c) can decide something is worth checking on later, and follow up without being
asked.

**A real platform constraint that shapes how this actually gets delivered on chat**:
Amul's chat isn't its own app — it's an iframe embedded inside something else, so it
has no way to push an actual notification to a farmer between visits. On chat, "follow
up without being asked" can't mean "message the farmer out of the blue" — it has to
mean **something waiting for them the next time they're already there.**

**Core building block**: a reminder/check-in ticket — farmer, a trigger (a date, or a
condition like "when this scheme opens"), and what to check or say. A simple scheduler
(same shape as background jobs already in the codebase, e.g. `scheme_scheduler.py`)
watches for due tickets. On chat, delivery means turning a due ticket into an entry in
the **existing suggested-questions block** already shown in the UI — something like
"see if your payment issue is sorted" or "check on your booking" sitting there as a
tappable suggestion the next time the farmer opens the chat, not a push notification.
The farmer taps it (or doesn't) entirely on their own terms — this actually makes the
"always opt-in, never intrusive" guardrail below easier to guarantee, not harder,
since there's no way to interrupt someone through this surface even if we wanted to.
(Voice is a different channel with its own delivery options — RAYA calls/SMS aren't
limited by the chat iframe — but that's a separate decision, not assumed here.)

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
- On chat, every item in the feature list below (the daily reminder, the vaccination
  nudge, the loan-status watch, etc.) delivers as a suggested question waiting for the
  farmer next time, per the platform note above — not a literal message sent to them
  in between visits. Read "remind" and "follow up" below as "have something ready to
  check on," not "proactively contact."

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
- **Noticing when one phone number might actually be more than one person** — if the
  facts building up for one identity start genuinely contradicting each other in a way
  that suggests two different people are using the same account (see Example D1),
  don't try to guess who's who. Flag it and **stop using memory for that identity**
  until it's resolved. A wrong guess here is worse than no memory at all (principle
  3) — this turns a risk we'd otherwise just have to avoid outright into something we
  can actually detect and handle safely.

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
- **Example D1** (telling apart multiple people sharing one household phone) —
  actively telling them apart is still too risky; getting this wrong (e.g. leaking one
  family member's info to another) is worse than not attempting it. What we're doing
  instead: have the background reflection step notice *when* an account looks like
  it's shared (contradicting facts building up) and turn memory off for it, rather
  than guess who's who (see Section 3c) — a safe fallback, not the same as solving D1.
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

### More detail on Honcho, for the record

Honcho's own "fast" option (its equivalent of our Layer 1/2) is a real, working
feature — worth understanding exactly what it does, since it's basically the same
shape as what we're building. It takes the farmer's current question, turns it into a
search, and pulls back a capped number of matching notes (100 by default) — no AI
"thinking" step, just a lookup, same speed class as our own design. So functionally,
Honcho's fast path and our Layer 2 are doing near-identical things.

**Could we use Honcho but point it at Qdrant instead of a new database, to get the
best of both?** Checked directly — no. Honcho only supports three specific vector
stores: its default (Postgres, "pgvector"), a paid cloud search service
("Turbopuffer," needs its own account and API key — not something we'd self-host),
and an embedded local option ("LanceDB"). **Qdrant isn't one of the supported
options at all** — using it would mean writing and maintaining our own custom
integration code for Honcho, not flipping a setting, which defeats the entire point
of adopting a ready-made product in the first place.

And even that doesn't fully solve the infrastructure question: no matter which of
those three vector stores gets used, **Honcho still requires Postgres underneath for
everything else** — workspaces, sessions, the message log, its background work
queue. The vector-store setting only changes where embeddings specifically go; it
doesn't remove Postgres from the picture. So there's no configuration of Honcho that
gets us down to "just Qdrant, nothing else new" — Postgres (or a paid third-party
service) is required either way, plus its own dedicated Redis, plus its own
permanent background program. That's the real reason it's not worth it for us: not
because its fast-path feature is bad — it's genuinely comparable to what we're
building — but because there's no path to getting that feature without also taking
on infrastructure we've specifically decided against.

### More detail on Graphiti, for the record

Graphiti's fast path works the same way ours will — a similarity search plus a
keyword search, no AI step, sub-second. The appeal, as covered above, is that it can
also hand back real structured fields and keeps a history of how a fact changed,
which our from-scratch build has to earn by hand.

**Could using the lighter graph-database option (FalkorDB instead of Neo4j) make
this a non-issue?** It genuinely helps — FalkorDB speaks the same protocol Amul's
Redis already does, so it's a smaller leap than a full separate database system like
Neo4j. But it's still a **new, separate service to run, monitor, and back up** — not
nothing, just less than Neo4j. And critically, the vector-search part is **built
directly into each graph backend** (checked directly in Graphiti's own code — every
supported database, Neo4j, FalkorDB, or otherwise, has its own vector-search code
bundled in) — there's no way to tell Graphiti "use Qdrant for the searching part,
just use FalkorDB for the graph structure." Adopting Graphiti in any form means
running a database that duplicates what Qdrant already does for us, full stop.

One more practical catch worth knowing: Graphiti's structured-field extraction is
explicitly documented to work best with providers that support genuine structured
output (the major hosted ones) — it warns that smaller or self-hosted models can
produce broken results. Since this only runs in the background (Section 2's
compute-budget principle), that's not a blocker — we could route just this specific
step to a stronger model regardless of what serves live chat — but it's a real
detail to plan for, not assume away.

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

### How the background job divides the work

Decided 2026-09-08. Three rules, and each one exists for a reason:

**1. A hard cap of 10 turns per prompt.** Not "as much as fits in the context window."
The extraction quality of a small model falls off well before its context limit does —
give it fifty turns and it summarises instead of extracting, and quietly drops the one
unresolved thing that mattered. Whole conversations are packed into a chunk while they
fit under the cap; a single conversation longer than 10 turns is split across
consecutive chunks. Keeping conversations intact where possible matters, because
extraction is much better when it can see a problem raised *and* answered in the same
window.

**2. A batch holds one chunk each from many farmers — never two chunks of the same
farmer.** A farmer's memory state changes as their own chunks are processed (chunk 3
needs to see what chunk 2 wrote, or it will re-create the same entry as new). So one
farmer's chunks are strictly ordered and cannot be worked on in parallel. Different
farmers are completely independent, so those go side by side freely. Chunks are handed
out round-robin, which means **a farmer with a long history simply finishes in a later
batch.** That's the intended trade: heavy users take longer, nobody's memory gets
processed out of order. Run daily and almost everyone completes in the first batch or
two — the long tail only appears on a first backfill.

**3. Strictly chronological.** By chunk N the store contains exactly what it would have
contained had this been running live since the farmer's first conversation. This isn't
tidiness — it's what makes the backtest in `backtesting-plan.md` meaningful instead of
circular. A replay that used memory built from the farmer's *later* conversations would
be grading the bot on answers it couldn't have known.

### The three layers are written in order, by separate prompts

Per chunk: **Layer 3 → Layer 2**, then once a farmer's chunks are done, **Layer 1**.

Each stage is its own small prompt rather than one call producing everything, following
the standing engineering preference (`oan-brain/style/swe-style.md`): a small model
split into narrow steps, with validation on top, beats one large call — and each step
can be graded on its own.

1. **Extract (Layer 3)** — what, if anything, in these turns is worth remembering, in
   full detail. Most chunks correctly produce zero entries.
2. **Match** — for each candidate, is this the same situation we already track, or
   genuinely new? Defaults to "new"; the costs are not symmetric (Decision 2 below).
   On a merge, the earlier detail is carried forward rather than replaced — the point
   of an update is the thread.
3. **Headline (Layer 2)** — a *separate* call writes the two sentences that get
   injected into every future turn. Separate for two reasons: after a merge the entry
   covers more than its old headline said, so the headline has to be rewritten; and
   this is the highest-stakes text in the system, shown on every turn whether it is
   relevant or not, so it earns a prompt whose only job is getting it right. If this
   pass fails or returns something absurd, the extracted headline stands — a broken
   rewrite must never replace a working headline.
4. **Standing record (Layer 1)** — runs once, after the farmer's queue drains, not per
   chunk. It is meant to be stable; re-deriving it after every chunk would turn it into
   a running log, which is exactly what Layer 2 already is.

   One thing worth recording, because it was wrong on the first attempt: this pass
   cannot run on the Layer-2 headlines alone. Three of the seven fields — what the
   farmer is called, how they want to be spoken to, and the words they use for their
   own animals — exist *only* in the farmer's own phrasing, which the headlines have
   already paraphrased away. So the pass also gets a bounded sample (10 lines) of what
   the farmer actually typed, their side only, with an explicit instruction to read it
   as evidence of *how* they speak and not to promote the content of those questions
   into standing facts.

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
  anything risky, pure venting with nothing actionable) — and, per principle 8, no
  account, transaction, phone or registration numbers; describe the thing instead. An
  animal's ear tag is the one exception, and it goes into `metadata.animal_id` only,
  never into the text.

This list isn't invented from nothing — it's a direct translation of Section 4's
taxonomy and Section 2's principles into rules an AI can actually follow.

### Decision 2 — is this the same thing as before, or something new

The harder one. A new fact might be worded completely differently from an existing
memory about the same underlying issue (Example 7's "12 animals, only 5 show online"
vs. "0 milking animals" are the same complaint, said two different ways). For most
entries there is no identifier to match on, so this has to be done by meaning. The
exception is animal health notes: when both sides carry an `animal_id`, that settles
it outright — same tag means the same animal, different tags mean different animals
and therefore a new entry, no matter how similar the wording. That is the whole
reason the tag is stored (principle 8). Where there is no tag:

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

- **A known, stable fact** (Layer 1's standing summary) — no search at all, just read
  it directly. Instant.
- **A known category, just not which specific entry** (the bot's about to book a vet
  visit, so it wants "any open booking for this farmer") — filter by category and
  "still current," no search needed — more reliable than a fuzzy search since it
  doesn't depend on wording lining up.
- **A genuinely open-ended question** (Layer 2's job) — where we don't know in advance
  what it relates to. Turn the question into something searchable, look only within
  that one farmer's own (small) set of headline entries, take the closest matches.
  Since it's already narrowed to one person's history, a plain search performs well
  without needing anything fancier layered on.

**Getting both a quick headline search and a deeper, expanded one out of the same
database.** Qdrant supports attaching *more than one* embedding to the same stored
entry. So each Layer 2 entry carries two: one generated from its short headline, one
generated from its fuller Layer 3 detail. The automatic, every-turn search (above)
only ever searches the headline embeddings — fast, and that's all it needs. When the
bot decides a headline is worth digging into, it makes a tool call that searches the
*expanded* embeddings specifically instead — which can genuinely be a multi-step,
try-a-search-then-try-another kind of search, since it's gated behind a deliberate
tool call and not sitting on the path every turn has to wait through (Section 2,
principles 1 and 2).

### Two kinds of "no longer true" — and why they're separate fields

`valid_to` (above) is set **retroactively**: something changed, so the old version
gets stamped with when it stopped being true. But some facts have a **known expiry
from the moment they're written** — those get a separate field, `expires_at`:

- A milk withdrawal period after a vet treatment ("don't pour her milk until
  Thursday evening") — the clearest case, and the most safety-relevant.
- A scheme or subsidy window that closes on a known date.
- A vaccination window that has a real deadline.
- Time-bounded advice ("add dry fodder for the next 10 days").
- A loan eligibility result, which goes stale by its nature.

**Why not reuse one field**: the two mean genuinely different things.
`valid_to` = *"this turned out to be wrong or changed"* → it's just history.
`expires_at` = *"this was always going to lapse on this date"* → often deserves a
**follow-up** rather than silence ("the withdrawal period has ended — is her milk
okay to pour now?"). Collapse them into one field and you can't tell which
happened. So "is this current?" is two conditions: `valid_to` empty **and**
(`expires_at` empty or still in the future).

**The useful side effect**: this doubles as the trigger for the proactive
follow-ups in Section 3b — "what's coming due in the next day" is one date-range
filter. Which means **a reminder doesn't need its own separate store: a reminder
*is* a memory entry with an expiry.** The withdrawal reminder, vaccination nudge,
and scheme-deadline watch all fall out of one mechanism.

**Caveat worth keeping**: an expiry date is a *prediction*, and predictions are
wrong — deadlines get extended, a recorded treatment date can be off. So a lapsed
entry shouldn't silently vanish; for anything safety-relevant it should become
"needs checking," not "false." And per principle 7, "the withdrawal period ended"
still doesn't mean the farmer actually observed it.

### One free-form area for everything else, so system fields stay protected

Only a small set of fields are ones the system actually filters on: `farmer_id`,
`type`, `status`, `valid_to`, `expires_at`, `times_raised`. **Everything else the
model wants to record goes into a single nested `metadata` object** — feed costs,
which shifts a withdrawal period affects, its own confidence, whatever a new entry
type turns out to need.

Worth being accurate about the reason, since it isn't what you'd expect: Qdrant's
stored fields are already schemaless, so adding a new top-level key needs no
migration at all (unlike a SQL table). The real reason for the boundary is
**protection**: if the model can write keys at the top level, it can collide with or
overwrite a field the system depends on — a model deciding to write
`status: "cow is sick"` would quietly break every "still open?" filter. Nesting
model-generated keys under `metadata` makes that impossible.

And it doesn't cost queryability: nested keys can still be filtered and indexed
later via dotted paths (`metadata.some_key`), so if a model-invented key turns out
to be broadly useful, it can be promoted without moving any data.

### Checking a field directly (e.g. "does this farmer have anything still open")

Since real fields exist (`status`, `type`, `times_raised` — Decision 1 above), some
questions don't need a search at all, just a direct filter: "give me every entry for
this farmer where `status = open`." Instant, exact, no interpretation needed — and
crucially, this same kind of check is what lets the analytics idea in Section 3c
work at all (checking this across *many* farmers at once — "how many currently have
an open complaint of this type" — is one filter, not hundreds of individual reads).
This is precisely the thing Honcho's always-free-text storage can't do (Section 5) —
without a real field, "is this still open" has no answer except reading and
re-interpreting a sentence every time, which doesn't hold up once you're checking
more than one farmer at a time.

**How the live agent knows to use this**: no different from any other tool it
already has. Define it as a tool — say, `check_open_issues` — with a plain
description of what it's for ("check whether this farmer has an unresolved issue
raised before"), and the model calls it when the conversation calls for it, the same
way it already decides when to call `get_farmer_profile` or `book_ai_call` today.
Nothing new about *how* tools get exposed to the agent — just one more tool on the
existing list. For the common case, this doesn't even need to be its own decision —
Layer 2's automatic per-turn search can just default to only ever surfacing
`status: open` entries, since that's usually what's relevant; an explicit tool call
is for the narrower, more specific checks beyond that default.

**The background reflection ("dreaming") step uses the exact same filtering** — for
its own two jobs: checking whether a farmer already has an *open* entry of a given
type before deciding new-vs-update (Decision 2 above), and building the
across-farmers analytics view (Section 3c). Same mechanism, used internally rather
than exposed to a live conversation.

**A safety rule worth building in at the code level, not just as an instruction**:
whatever the actual query looks like — a simple filter, or something more elaborate
the dreaming step suggests based on a farmer's specific history — the tool that
executes it should always wrap it with `farmer_id = <this caller's id>` **in the
code itself**, not as something the model has to remember to include. That way,
however a query gets constructed, it's structurally impossible for it to reach past
one farmer's own memories — a hard guarantee, not a rule that depends on the model
following instructions correctly every time.

### Different farmers can genuinely have different fields — and a tool per entry type

Qdrant doesn't force every entry into one rigid, fixed set of columns — the tagged
data on each entry is flexible per entry, not a strict spreadsheet every farmer's
data must fit identically. So a `complaint`-type entry can carry `status` and
`times_raised`, a `booking`-type entry can carry `booking_type` and `confirmed`, a
`loan`-type entry can carry `reason_code` and `decided_date` — each type has whatever
fields actually make sense for it, and a given farmer's memory only ever contains the
types actually relevant to *their* history. A farmer who's never touched the loan
feature simply has zero `loan`-type entries — nothing forces every farmer's memory
into the same shape, and nothing breaks from most fields being absent for most
people. This quietly gets us the same "different farmers, different relevant facts"
outcome Graphiti's structured types were offering (Section 5), without needing a
rigid schema imposed from outside.

Following directly from that: define **one small, fast filter tool per entry type**
— `check_open_issues` (`type: complaint, status: open`), `check_pending_vaccinations`
(`type: vaccination, completed: false`), `check_loan_status` (`type: loan`), and so
on. Each is instant and exact, same mechanism as the single example above, and each
is only ever useful — and only ever called — for farmers who actually have entries of
that type. If a farmer has none, the filter just comes back empty; nothing goes
wrong, there's simply nothing to show. The agent picks whichever tool matches what
the farmer's actually asking about, same as any other tool call it already makes.

### Memory has to be switchable per farmer, from day one

Not an afterthought — a requirement, for three separate reasons that all point the
same way:
- **It's the only honest way to tell whether memory helped.** Being able to replay
  the *same* farmer's *same* real questions with memory on and off, and compare, is
  the whole basis of the validation in `demo-plan.md`. Without a per-farmer switch,
  there's no comparison, just a vibe.
- **It's the safety valve for the shared-account case** (Section 3c): if the
  background step notices an account's facts contradicting each other in a way that
  suggests two different people, the response is to *turn that farmer's memory off*,
  not to guess who's who.
- **It's the rollout control.** Turning this on for a handful of farmers first, then
  widening, is only possible if the switch exists.

Implementation should keep this dead simple — a per-farmer flag the bot checks before
doing any memory lookup at all, defaulting to off. When it's off, the bot behaves
exactly as it does today: no lookup, no injected context, no difference whatsoever.

### Two more things worth borrowing from how Honcho organizes its memory

Neither of these needs Honcho itself — just the ideas, built cheaply on the same
Qdrant setup:

- **Point back to the original conversation instead of copying it.** Rather than
  storing a farmer's exact original words inside the memory entry (more raw, possibly
  sensitive text sitting in a place it doesn't need to be — see principle 8), keep a
  reference to where it came from (which conversation, roughly when). If the deep,
  Layer 3 search ever genuinely needs to see the exact original wording, it can fetch
  that from Amul's existing conversation logs, which already store it — no need for
  memory to keep its own second copy.
- **Keep a "built from" trail on anything the reflection step concludes.** When the
  background step notices something bigger — "this is the third time this complaint's
  come up" — have it record which specific earlier entries that conclusion came from.
  Cheap (just a list of IDs), but it means a conclusion is never an unexplainable black
  box — if it's ever wrong, we can trace exactly why it was reached.

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

---

## Consolidation — the dream-time pass that makes over-splitting safe

Added 2026-09-08, after the first run against real logs exposed the problem.

The per-conversation match was originally built as though it ran during a live turn:
three candidates, filtered to a single entry type, one call, default to "new". It runs
nightly, with no latency budget, and it is the step where quality matters most —
because fragmentation corrupts everything downstream of it.

**What it actually produced.** On one real farmer, one grievance — the society not
registering his calves for the rearing subsidy — was stored as **six separate live
entries**, each with `times_raised = 1`. That makes "he has raised this repeatedly"
undetectable, which is the single most valuable thing memory could have surfaced here
(Section 4, Examples 2 and 7). It also filled top-k with near-identical entries,
crowding out everything else the farmer had said.

### Why the cheap version failed

- **The type filter made the most common duplication impossible to detect.** Candidates
  were only compared against existing entries of the *same* type. But the usual real
  pattern is one situation recorded as a `complaint` one week and a `tracker` the next.
  Those can never be compared, so they can never be merged.
- **Ranking by score was close to arbitrary.** Measured: everything in one farmer's
  store scores 0.74–0.88 whether or not it is the same situation. Taking the top 3 of
  that ordering is nearly a coin toss.
- **"Default to new" had no counterweight.** The default itself is right — the match
  step sees one conversation, and a wrong merge there is silent and permanent — but
  with nothing to correct over-splitting later, "cautious" just means "fragmented".

### What replaces it

Three passes, all affordable because none of this touches a live turn:

1. **Wide candidate retrieval.** No type filter. Both the headline and expanded
   vectors, searched across several phrasings of the new entry, unioned.
2. **Model reranking.** A model that can read the candidates decides which are
   plausibly the same *situation* — not which are topically closest. Returning nothing
   is a valid answer.
3. **A whole-store consolidation pass**, run after a farmer's chunks and *before* the
   standing record, so Layer 1 is derived from whole situations rather than fragments.
   It clusters every current entry into situations, synthesises one merged episode per
   group, and folds the fragments into it.

**The division of labour is the design.** The per-chunk match still defaults to "new".
Over-splitting is now recoverable, which is what makes that caution safe rather than
merely convenient — the online step is allowed to be wrong in the direction that can
be fixed later.

### Merging preserves the thread, and stays auditable

- The **longest-standing fragment is kept**, so `first_source_ts` survives and the
  merged episode doesn't look like it started today.
- `times_raised` becomes the number of separate occasions the situation came up. This
  is the whole point: it is what makes "raised repeatedly" detectable at all.
- `source_ts` advances to the most recent fragment, so the span is visible.
- Fragments are **folded, not deleted** (`POST /entries/{id}/fold`), stamped with
  `merged_into` and the reason. Runtime search returns only the consolidated entry,
  but the trail back is intact — a wrong merge must stay diagnosable.
- Low-confidence groups are skipped rather than merged.

### Measured result

On that farmer: **14 current entries → 8.** The grievance now reads "repeatedly raised
concerns since August 2026", `raised 6x`, with the ₹15,000 misconception, the
assistant's correction of it, and the advice given all preserved in one chronological
account — none of which any single fragment contained.

Retrieval improved too, which was not the goal but follows: **recall@1 went from 8/9 to
9/9** on a labelled set of nine recall queries, with recall@3 at 9/9 throughout. Fewer,
truer episodes are easier to retrieve than many overlapping ones.
