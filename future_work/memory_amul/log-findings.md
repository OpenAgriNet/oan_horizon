# Real memory-value cases, mined from Amul prod logs

Where this came from, so it can be reproduced or extended, and what it means for the
design in `memory-design-decisions.md`.

## Method

- **Data source**: Amul's prod Langfuse (`langfuse.prod.amulai.in`, creds at
  `oan-brain/oan_creds/.langfuse_keys`). Chat-channel turns are logged in full plaintext
  (`query`/`output`) under trace name `chat.translation`, env `chat-production` — this is
  what was read. Voice (`agent_journey`, env `voice-production`) is privacy-truncated
  (SHA-256 hash + short preview only) and was not deep-read for this pass.
- **Finding repeat users, efficiently**: Langfuse's Metrics API supports `GROUP BY
  userId` with a plain `count` aggregation on the `traces` view — this works fine (the
  known-broken fields per `knowledge/langfuse-api-gotchas.md` are specifically
  `uniqueSessionIds`/`uniqueUserIds`, a different bug). One query ranked all **77,495
  distinct users active in the last 30 days** by turn count — no need to scan raw
  traces to find repeat callers.
- **Sample**: the top 8 users by volume, cross-checked for real multi-day usage (not
  test/QA accounts — query content confirmed these are genuine recurring farmers
  checking milk/payment records daily, not scripted test traffic). Each user's full
  `chat.translation` history over 30 days was pulled via a `userId`-filtered query
  (cheap — one user's full history in a handful of pages, not a bulk scan) and read in
  full, chronologically, across every session.
- **Masking**: farmers referenced below by last-4-digits of their phone (e.g. `...3007`)
  — enough to cross-reference within this doc, not enough to identify.
- **What this is not**: a statistically representative sample (8 heavy users, not a
  random draw), and a counterfactual read (these farmers never had memory, so the bot's
  actual behavior is the only data point — see `backtesting-plan.md` for how to test a
  real memory-augmented alternative against these same threads).

## Taxonomy — the different *shapes* of memory value found

Five genuinely distinct mechanisms showed up, not one repeated pattern. A design that
only does simple fact-recall would miss the more valuable (and harder) ones:

1. **Stable-fact recall** — a static fact re-explained/re-asked for, sometimes even
   *within* the same session. Cheapest to fix (`FarmerProfile`-style preload).
2. **Unresolved-thread escalation** — the same unanswered complaint/question recurring
   over days or weeks, with the bot treating each occurrence as new. Needs a
   repeat-count/escalation signal, not just recall — this is closer to Honcho's
   reasoning/conclusions model than plain retrieval.
3. **Proactive, time-aware follow-up** — facts the system *already has* (a stated
   commitment, a stale medical status) that nothing ever re-surfaces unprompted. Needs
   timestamps + a follow-up ledger, not just retrieval.
4. **Emotional/anxiety continuity** — a farmer's specific standing worry (not a generic
   topic) that the bot has no memory of, leading to real comprehension failures.
5. **Booking/action-state continuity** — whether a requested action actually happened,
   especially when the bot's own language implies it's already in motion when it isn't.
   The most safety-relevant category found (see Case 8).

A sixth category matters as a **boundary, not a memory case**: some repeated queries are
legitimately live-data lookups (today's milk total) where memory would be the wrong
fix — the real issue there was data-freshness/consistency, not missing memory. Don't
let "reduce repeated questions" become the design goal; several of these repeats
*should* re-fetch live data.

## Cases

### 1. A stable fact re-asked for two weeks straight (`...3007`)
8+ separate sessions (Aug 7 – Aug 21) asking variants of "when will this month's
payment arrive?" — identical non-answer every time ("I don't have exact payment dates,
contact your society"), phrased slightly differently, never acknowledging it's told
this same farmer the same thing many times before. *Simplest possible case*: a bot that
knows "I've told this person 6 times I don't know this" could at least answer with
continuity instead of fresh surprise each time.

### 2. A recurring deduction, never resolved, never escalated (`...3007`, `...7788`, `...1036`)
Three independent farmers, three different unexplained deduction line items:
- `...3007`: a recurring ₹1,200 "કપાત ખાતું" (deduction account) line, asked about 7+
  times over a week (Aug 13–20), a different non-committal answer each time.
- `...7788`: a ₹4,400 "Member Goods Advance Account" deduction, asked about across 6
  sessions over a week; on one occasion the bot's answer got strictly *worse*
  ("Sorry, I cannot see your total due amount") than earlier sessions.
- `...1036`: a ₹5,460→₹10,480 "ગ્રાહક બાકી એ/સી" deduction with a **garbled account
  label** (literal `?????` placeholders in the trace) — asked about once, then silently
  recurs in every subsequent 7-day report for 4+ more days, climbing to net-negative for
  the month, with zero acknowledgment it's the same unresolved item.

None of these bots ever said "you've asked this before and I still can't answer it" —
which would itself be more honest and useful than re-litigating from zero. This is the
clearest case for an **unresolved-thread signal**: 5+ occurrences of the same
unanswered question is a real, actionable signal for human escalation, not something
recall alone fixes.

### 3. A stable identity fact re-asked, sometimes twice in the same session (`...3007`, `...7788`, `...7896`)
- Both `...3007` and `...7788` independently hit the same gap: asking for the milk
  price gets "which dairy union/cooperative are you asking about?" — even in sessions
  where the bot *itself* had already named the farmer's union minutes earlier answering
  a different question. Confirmed 5+ times each across the month.
- `...7896` has two linked PashuGPT profiles; disambiguation was asked **three times in
  a row within one 10-minute session** for three different questions, farmer eventually
  typed the full name out longhand to force it through — then the very next session,
  the bot silently picked the *other* profile without asking, an inconsistent default.

This is the cleanest `FarmerProfile` case in the whole set: a fact (which union; which
of two linked accounts is "usually meant") that should be set once and never re-asked —
currently re-asked even inside a single session.

### 4. A disambiguation question the bot's own data already answers (`...5963`)
Farmer asks to book an AI (artificial insemination) visit; bot asks "cow or buffalo?"
Session ends before booking completes. ~1.3 hours later, in a new session, same
request — bot asks the **identical disambiguation question again**, despite having
successfully fetched this farmer's animal registry the day before showing they have
exactly **one** registered animal, a cow. The question was mechanically unnecessary.

### 5. A 10-month-old medical follow-up that never got surfaced (`...5963`)
The bot's own fetched record: last AI attempt 31 Oct 2025, last pregnancy check 26 Mar
2026, status "not pregnant" — farmer still asking breeding questions in August, ~10
months after the last attempt. The bot itself had once said *"if she isn't pregnant
after the next heat cycle, book a health check to rule out infection"* — nothing
tracks whether that ever happened. **Strongest case for memory as proactive care**: the
facts needed are already in hand; what's missing is a layer that reasons over elapsed
time and surfaces "it's been unusually long, and we told you to follow up" unprompted.

### 6. A specific past incident misread, compounding a farmer's real anxiety (`...5951`)
Farmer states, agitated: *"REMEMBER, I am not going to sell any animal"* and *"two
months ago one of my buffaloes was DELETED [from the online system]"* — a real, named
grievance. The bot **misreads "deleted" as calving news** and responds with
congratulations — actively worsening the interaction. A bot holding this farmer's
specific standing worry (not a generic "reassure the user" instinct) would have
recognized the reference and responded to the actual concern instead of misfiring on
it.

### 7. A recurring registration/visibility grievance, repeated for 3+ weeks with escalating stakes (`...5951`)
"12 animals total, only 5 show online" / "no farmer in my society gets scheme
benefits" / "I give 40 liters daily but it shows 0 milking animals" — raised across at
least 4 separate days (Aug 9, 13, 14, 18) plus a related variant Aug 28, each time
restarting diagnosis from zero. One session (Aug 14) escalates to a 56-turn session
covering the same ground plus a society-wide complaint. No session acknowledges this is
a known, weeks-old, still-unresolved complaint for this specific farmer.

### 8. An abandoned booking the farmer believes is already in progress — the sharpest finding (`...3048`)
A sick-animal case (skin disease → coughing → "could it be TB? contagious to humans?")
unfolds across **7 different sessions in one afternoon** (Aug 20). Sarlaben offers to
book a health-check appointment **eleven times**, always resetting to a fresh generic
disease writeup, never confirming an actual booking — at one point stating explicitly
*"you haven't scheduled a visit yet, so the doctor hasn't been informed... is this for
a cow or a buffalo?"*, which the farmer never answers.

**Nine days later** (Aug 29), the farmer asks *"until then, what medicine can I give
the cow?"* — language implying they believe a vet visit is already pending. Sarlaben's
own reply uses the phrase *"you are waiting for the doctor"* in the same breath as
urging them to book a health call — **the bot's own language reinforces the farmer's
false belief that help is already coming**, when nothing was ever booked.

**Twelve days after the original complaint** (Sep 1), the same animal now can't stand
or sit — a materially more severe symptom — and the farmer is still asking home-remedy
questions, with no connection made to the original complaint.

This is the highest-priority case in the whole set: a farmer may have delayed seeking
other help for a worsening animal because they believed a vet visit was already in
motion. A memory system here isn't a nice-to-have personalization — it's the difference
between "we never confirmed the booking, here's what's actually true" and letting a
real welfare situation drift for nearly two weeks. **Any memory design for Amul should
treat "does the bot's stated action-state match reality" as a hard requirement, not an
optional layer** — this maps directly to the "booking/action outcome" open question
already flagged in `memory-design-decisions.md`.

### 9. Anomaly against a personal baseline (`...3007`, `...7896`)
- `...3007`: after 13 straight days of daily milk records, two sessions on Aug 19
  suddenly return "no records found" for the same routine query — no context offered
  for a farmer who might reasonably read this as "did I lose my delivery record?"
- `...7896`: 3 separate sessions 6 days apart (Aug 11, 15, 17) all return "no milk
  collection records found," with the farmer explicitly asking "is my account even set
  up right, can my name be changed?" — each time getting the same unhelpful answer with
  no acknowledgment this is the same unresolved problem recurring.

Memory's value here isn't recall, it's **detecting a break from a known personal
pattern** and contextualizing it, rather than a flat, context-free non-answer.

### 10. Rich data volunteered once, then lost (`...5951`)
Farmer states exact feed costs (cottonseed cake ₹2000, corn ₹1900, Amul bypass feed
₹1720 over 10 days) against a stated ₹18,000 income, concluding "milk gives nothing."
This is exactly the kind of personalized economic snapshot that, if retained, could
power a real "is your feeding strategy working" comparison later — it currently
evaporates with the session.

## Boundary findings — NOT memory gaps (don't over-fix these with memory)

- **`...7472`**: almost entirely narrow, repeated transactional queries ("last 7 days,"
  "today and yesterday," "this month's total") that legitimately need fresh data each
  time, not memory. The one real issue found: asking the *identical* question minutes
  apart returned **different totals each time** (₹2,596.35 → ₹2,596.75 → ₹2,758.28 →
  ₹2,619.58 within about an hour) — a live-data-consistency bug that could easily read
  as "the bot is unreliable," but the fix is data consistency, not memory.
- **`...1036`**'s garbled account label (`ગ્રાહક બાકી એ/સી_?????`) and `...7788`'s
  garbled society name are upstream data/rendering bugs, not explanation gaps — memory
  can't fix a broken label.
- Repeated "when will payment arrive → I don't know" exchanges (`...3007`, `...3048`):
  memory can't manufacture data that doesn't exist. The repeated identical failure is
  itself worth surfacing to whoever owns that data gap — but as a data-completeness
  issue, separate from the personalization cases above.

## What this changes in the design

- **Case 8 (abandoned booking, false "in progress" belief) should be treated as the
  top-priority scenario for the backtest in `backtesting-plan.md`** — it's the one case
  in this set with real welfare stakes, not just convenience. Worth replaying this exact
  thread (`...3048`, Aug 20 – Sep 1) with a memory-augmented agent and checking whether
  it would have either completed the booking or at least never implied it had.
- The **unresolved-thread cases (2, 6, 7)** argue for something closer to Honcho's
  reasoning/conclusions model (an LLM judging "has this come up before, how many times,
  still unresolved?") over plain similarity-threshold recall — a vector search alone
  won't produce "you've asked this 5 times" as a first-class signal.
- The **stable-fact cases (1, 3, 4)** are exactly the `FarmerProfile`-equivalent from
  `memory-design-decisions.md` — cheap, low-latency, preload-only, no reasoning needed.
- The **proactive-care cases (5, 10)** need timestamps + a follow-up ledger on top of
  recall — matching the "state tracking" idea already floated in
  `oan_horizon/future_work/memory/memory-design-decisions.md` for mahaVistaar.
- The **boundary findings** are a reminder to scope the backtest's "regression" gate
  correctly: a memory system must not start treating live, legitimately-changing data
  (today's milk total) as something to recall instead of re-fetch.

## Hypothetical scenarios (not mined from logs — generated to broaden design thinking)

Everything above is observed behavior from real farmers. The cases below are **invented,
not observed** — generated (via a larger model, briefed on Amul's actual tools/channels/
personas and explicitly told not to repeat the categories above) to push the design past
what 8 real transcripts happened to surface, into territory the log sample is too narrow
or too short (30 days) to show on its own: the doctor persona, the loan feature, seasonal/
calendar reasoning, multi-caller households, cross-channel and cross-farmer patterns, and
— deliberately included rather than filtered out — the ethical limits of what this system
should remember at all. Treat every scenario's caveat as load-bearing, not a disclaimer:
several of these are here specifically because more memory is not obviously better.

### A — The doctor persona: case files, not sessions

#### 1. The repeat-breeder workup that no single vet ever finishes

Buffalo tag ending 4471 in Nandotra has now been inseminated four times in seven months. In March, Dr. Prajapati palpated her and noted a mild endometritis; in May a stand-in vet on the same round gave a routine PGF2α and told the farmer "try again next heat"; in July a third vet is looking at a cold animal and starts, again, from zero. Each of them had exactly one session's worth of context, so nobody ever crossed the threshold where "unlucky" becomes "this is a repeat breeder, stop inseminating and investigate — mineral deficiency, cystic ovary, silent heat, or a semen-handling problem at the sub-centre." A vet on a 30-animal round has maybe ninety seconds per animal; the memory has to hand him the pattern, not the archive.

**Memory must track:** per-animal (not per-farmer) clinical timeline keyed to ear tag — AI dates, sire/semen batch, PD results, drugs given with dose and route, differentials already ruled out, and which vet said what; plus a derived flag ("4th service, no conception") that fires without being asked. Must survive the animal changing vets, villages, and owners.

**Caveat:** longitudinal notes cause diagnostic anchoring. If vet #1's speculative "probable endometritis" gets replayed as settled fact to vets #2 and #3, memory has actively narrowed the search instead of widening it. Provenance and confidence must ride with every remembered clinical claim, and unconfirmed impressions should decay or be explicitly labelled as unverified.

#### 2. Withdrawal-period memory — the case where forgetting spoils the whole village's can

Kanubhai's crossbred cow gets intramammary ceftiofur for clinical mastitis on a Tuesday evening. He is told to discard the milk, understands it as "don't pour tomorrow," and on Thursday morning pours all four animals' milk into the society can as usual. At the chilling centre the pooled sample fails the antibiotic-residue test, and 900 litres from eleven households is downgraded or rejected — Kanubhai's mistake, everyone's loss. Sarlaben knew about the treatment (the vet logged it in the doctor persona) and knew Kanubhai's pouring pattern, and said nothing on either channel.

**Memory must track:** drug → withdrawal window (milk and meat) computed from the actual treatment date, bound to a *specific* animal, and cross-linked from the vet's session into the farmer's session; the farmer's normal pouring rhythm so the reminder lands the evening before each affected shift, not once.

**Caveat:** this is the clearest case where memory creates liability. If the reminder is late, wrong, or silently dropped because the vet's note never synced, the farmer will reasonably say "Sarlaben told me it was fine." A safety-critical reminder that is *sometimes* delivered is arguably worse than one that never existed, because it trains reliance.

### B — Money that only makes sense over months

#### 3. "What changed since they said no"

Bhikhabhai applied for a KDCC micro-loan in January to buy a second buffalo and was declined — his 90-day average pouring was below the threshold and he had an outstanding cattle-feed credit. He didn't understand the reason, so in February, April and June he asked Sarlaben to "check loan" again, got the same opaque no, and each rejection went onto his record. By August his position has actually flipped — the feed credit is cleared and his daily pouring is up 40% — and nobody tells him, because a fresh session has no idea a door was ever closed.

**Memory must track:** the fact and *reason code* of each past denial, which specific variables were binding, and a standing watch that re-evaluates only those variables; plus a suppression rule so the same application isn't re-litigated pointlessly in between.

**Caveat:** proactively telling a farmer he is now loan-eligible is a nudge toward debt, delivered by a trusted voice to a user who may not be able to read the terms. The line between "you no longer face the barrier you asked about" and lead-generation for a partner bank is thin, and crossing it once will be remembered by the village far longer than by the system.

#### 4. The feed experiment nobody kept score of

In November, Alkaben mentioned in passing that she had started adding bypass fat and had increased cottonseed cake by two kilos a day because a neighbour's yield had gone up. Five months later she asks Sarlaben whether it is "worth it." A memory system can answer honestly: her per-animal yield rose about 9%, but her fat percentage slipped, the union rate is fat-linked, and her feed spend rose more than her milk bill did — the experiment lost her money, and it lost more in the summer months than the winter ones.

**Memory must track:** farmer-stated inputs (feed changes, ration, green-fodder availability, dates) as first-class remembered facts even though no external system records them, aligned against the collection ledger's yield/fat/SNF/rate series; and enough seasonal baseline to separate "the feed did this" from "May did this."

**Caveat:** correlation dressed as causation, for a user with no way to challenge it. She also calved, changed fodder, and lived through a heatwave in that window. A confident "your feed change cost you ₹4,000" that is actually a seasonal artifact is worse than silence — this class of answer needs to show its working in plain Gujarati and name what it cannot separate.

### C — The agricultural year is the real clock

#### 5. The personal breeding calendar and the summer that eats conception rates

Jethabhai's Mehsani buffaloes go quiet every March, as buffaloes do — silent heat, heat stress, poor expression. Last year he wasted three inseminations between April and June, and both his good animals ended up calving in the wrong part of the year. A memory-equipped Sarlaben knows *his* herd's history, not just the textbook: it can tell him in February which two animals are due to come into heat before the window closes, suggest night-time heat detection and evening AI through summer, and flag in October — when conception odds are best — that animal 2209 has now been dry for five months and every week costs him a lactation day.

**Memory must track:** per-animal calving/AI/dry-off dates rolled into a calving-interval model; last year's *observed* month-by-month conception outcomes for this specific herd; and a seasonal prior for species and region, so advice is "your buffaloes, this June" rather than "buffaloes in summer."

**Caveat:** false urgency. Pushing a farmer to inseminate inside a closing window can override the animal's actual condition — a thin, negative-energy-balance animal shouldn't be bred on a calendar's say-so. The memory knows dates; it does not know body condition score unless someone looked.

#### 6. The anniversary of a bad monsoon

Ramilaben lost a young animal to lumpy skin disease two Augusts ago and still talks about it. Every year, HS and BQ vaccination should happen *before* the rains — May, not July — and every year she asks about it after the first heavy spell, when it's late. Memory lets Sarlaben open the conversation in the second week of May, in her own frame of reference: last year's timing, which of her animals are covered and which aren't, and that the mandali's vaccination camp date is the 22nd.

**Memory must track:** per-animal vaccination history and due windows; the farmer's own historical lag between "should" and "did"; a durable note that this household had a serious LSD loss, so the tone is careful rather than breezy; and the local camp/schedule facts the union publishes.

**Caveat:** annual re-raising of a traumatic event is exactly where "thoughtful" tips into "why does this machine keep bringing up my dead cow." The memory should change the *tone and timing* of the vaccination prompt without narrating the loss back to her. Referencing grief is almost never necessary to act on it.

#### 7. The dormant wish and the ikhedut window

In January, Vinodbhai mentioned he wanted a chaff cutter but couldn't afford one at full price; the conversation moved on and the wish evaporated. In September the Gujarat ikhedut portal opens a subsidy window for exactly that, for eleven days, and he finds out on day twelve from a neighbour. A memory system that stored "expressed intent: chaff cutter, price-sensitive, Jan" can fire once when a matching window opens, with the documents he'll need listed in the order the portal asks for them.

**Memory must track:** unfulfilled intents and aspirations as a distinct, long-lived object with a stated blocker (cost, documents, land record); a scheme catalogue with real open/close dates; and matching that is conservative enough not to spam every farmer with every scheme.

**Caveat:** intent goes stale quietly. He may have bought one, borrowed his brother's, or sold his animals. An eight-month-old offhand remark treated as a live want makes the bot feel like it filed him rather than listened to him — reactivated intents should be asked about ("you'd mentioned…is that still something you want?"), never assumed.

### D — Who is actually holding the phone

#### 8. The daughter-in-law who does the milking and the son who owns the number

The registered number for the Chaudhary household belongs to Hasmukhbhai, but three people use it: Hasmukhbhai for payment queries, his son Jignesh (literate, uses the app) for scheme paperwork, and his wife Nirali, who does the actual feeding and milking and calls when an animal is off-feed. Today's caller says "she isn't eating since yesterday" and gives a description of the animal, not a tag number. A memory system that models three distinct speakers on one identity can route to the right context — and, crucially, can hand the animal-health thread continuity across whoever calls next, because the *animal's* thread is shared even when the *person's* isn't.

**Memory must track:** speaker-level profiles under one phone identity (topic patterns, channel, language register, which linked farmer-account they act for), a live "who am I talking to" belief with an explicit low-confidence state, and separation of person-scoped memory from household- and animal-scoped memory.

**Caveat:** getting this wrong is worse than not doing it. Surfacing "your loan application" to whoever picks up leaks financial information inside a household where that may be genuinely unsafe — and confidently addressing Nirali as Hasmukhbhai is a small humiliation delivered daily. Default to household-safe context; require a cheap confirmation before anything person-scoped.

#### 9. The dropped call that finishes on WhatsApp

Dineshbhai is on an IVR call booking an AI visit; he's given the tag number and the preferred day, and the call drops at the exact moment RAYA is reading back the confirmation. He does not call back — he assumes it went through, which is precisely the failure mode already documented in the logs (see Case 8 above). With memory, a WhatsApp message reaches him ninety seconds later: "Your booking for tag 4471 wasn't completed. Reply 1 to confirm Thursday morning." He taps 1 and it's done.

**Memory must track:** in-flight task state with an explicit completion status that survives session death; channel identity mapping (MSISDN ↔ app ↔ WhatsApp); a resume token with a sensible expiry; and a rule that *incomplete transactions*, unlike chit-chat, are always worth a proactive nudge.

**Caveat:** cross-channel resumption assumes the channels reach the same person — on a shared phone the WhatsApp may be the son's. And a system that texts you every time a call drops in patchy Banaskantha coverage becomes noise fast; scope this to committed actions with real consequences, not to abandoned questions.

#### 10. The bot that learns how *this* farmer says his ear tags

Every call, the ASR hears Bharwad as "Bharwar", renders "beis hajar" as 2,000 instead of 20,000, and mangles the same two digits of the same ear tag. Vinodbhai corrects it every time, and every time the correction dies with the session. A memory system that keeps per-speaker recognition corrections — his tag numbers, his village, his animals' names, his particular Kutchi-inflected numerals — can bias decoding on the next call and stop making him repeat himself, which for a low-literacy voice user is the single most fatiguing part of the experience.

**Memory must track:** per-speaker correction pairs (heard → confirmed), the farmer's actual entity set (his tags, his society, his animals) as a decoding lexicon, and confidence so a one-off correction doesn't become a permanent mishearing in the other direction.

**Caveat:** a wrong correction becomes self-reinforcing. If the system once "learns" that his tag ending 41 means 47, it will confidently rewrite the correct one, and the farmer has no mental model for why the machine has started hearing him wrong. Corrections need to be evidence-weighted and easy to blow away.

### E — Across farmers, not just within one

#### 11. Nine farmers, one society, the same three sentences

Over four days, five farmers in the Dama mandali independently describe animals with high fever, sudden milk drop and stiffness in the hind limbs; two more mention flies being unusually bad. No single conversation is alarming and each is answered competently in isolation. A memory layer that aggregates *symptom features* — not identities — at society level can notice a cluster well above baseline for the season and do the one thing that matters: alert the union's animal husbandry officer and the local vet, and shift its own advice to the affected farmers toward isolation and immediate examination rather than generic supportive care.

**Memory must track:** de-identified, structured symptom extraction with village/society and date; per-society seasonal baselines so "more mastitis in monsoon" isn't an outbreak; and an escalation path to a human institution, since a chatbot must not be the one declaring an outbreak. The same substrate supports slower signals — which antibiotics are quietly failing in a given taluka.

**Caveat:** this is the sharpest privacy boundary in the whole design. It must be impossible for farmer B to learn anything about farmer A's animals, and the aggregate must never be granular enough to identify a household — "an outbreak at the one farm in Dama with Jaffarabadis" is a re-identification. There's also real false-positive cost: a rumoured outbreak can crash local trade, and self-reported symptoms over IVR are noisy evidence.

#### 12. The silent quality signal nobody can raise

Aggregated over six months, conception rates for animals inseminated by one sub-centre technician in a cluster of three villages are visibly worse than neighbouring routes — the pattern is consistent with semen-straw handling or thaw discipline, and no individual farmer could ever see it. Memory makes this visible for the first time, as a maintenance question ("check the LN2 container and thaw protocol on this route"), not an accusation.

**Memory must track:** AI events linked to technician/route/semen batch and their eventual PD outcomes, with enough volume and time depth to be statistically meaningful, plus confounders (species, season, parity, farmer heat-detection quality).

**Caveat:** this is a system that quietly grades named workers on data they didn't consent to be graded by, using conception rates that depend heavily on factors outside their control — farmer heat detection above all. Routed carelessly it becomes a surveillance tool inside a cooperative and will poison field staff's willingness to log anything honestly. Investigate equipment before people.

### F — What memory owes the farmer: forgetting, grief, and honesty

#### 13. Tombstones

Ramilaben's best buffalo died in March. In April, Sarlaben — cheerfully proactive, working off a stale herd snapshot and a remembered breeding calendar — tells her that animal 2209 is due for a pregnancy check and asks how she's doing. Memory that only accumulates is cruel; memory needs death and sale as first-class events that propagate immediately, suppress every downstream reminder, and quietly soften the tone of the next few conversations without ever narrating the loss back to her.

**Memory must track:** animal lifecycle terminal states (died, sold, culled, transferred) with the date and, where relevant, cause; cascade rules that kill all scheduled follow-ups for that animal; and a decayed sensitivity marker on the household.

**Caveat:** the source of truth for "this animal is gone" is often a passing spoken sentence, not the registry — the ear tag may stay active for months. Acting on an inferred death is high-cost if wrong ("I heard you no longer have her"), and so is waiting for the registry. This one probably needs a gentle explicit confirmation the first time, and absolute reliability afterwards.

#### 14. Closing the loop — and learning when to stop offering

In June, Sarlaben advised a farmer to reduce green lucerne and add dry fodder for an animal with recurrent bloat. Today he calls about something unrelated. A memory system with an outcome loop asks one short question — "did the bloat settle after the fodder change?" — and stores the answer, which turns a stream of one-shot advice into something that actually learns. The same mechanism has a second, less obvious use: Sarlaben has offered this farmer scheme information four times and he has declined every time, so it should stop offering, permanently, without being told to.

**Memory must track:** advice given → predicted outcome → observed outcome, with dates; and a separate ledger of *declines and non-engagement* — topics offered, ignored, or explicitly refused — treated as durable negative preference rather than an opportunity to retry.

**Caveat:** follow-up questions have a cost the system doesn't pay. A farmer calling at 6am mid-milking about a payment problem does not want a satisfaction survey about last month's fodder advice, and asking "did it work?" about an animal that subsequently died is a serious failure. Outcome-seeking must be cheap, skippable, and suppressed by anything in the record suggesting the story ended badly.

#### 15. The things Sarlaben should refuse to remember

Over months, farmers will tell this bot things that are true and dangerous: that they sold milk to a private buyer instead of the society, that they used oxytocin to let down milk, that they can't feed their animals this month, that they're thinking of selling everything. A memory system that faithfully records all of it creates a durable, subpoena-able, union-visible record of cooperative disloyalty, illegal practice, and personal distress attached to a named member — and once farmers grasp that, they will stop telling it anything true, which destroys the thing that made memory valuable in the first place. The design question isn't only what to remember; it's what to deliberately hold only for the length of one session, and what the farmer can see and erase.

**Memory must track:** an explicit sensitivity classification at write time with different retention tiers; a hard boundary preventing farmer-disclosed content from flowing into union/bank/enforcement surfaces; a spoken, low-literacy-friendly way to hear what is remembered ("what do you know about me?") and to delete it; and an audit trail of who read what.

**Caveat:** every one of these protections costs utility. Forgetting a mention of financial distress means missing the moment to surface a welfare scheme; siloing memory from the union means the union can't fix the systemic problem the memory has proven exists. This tradeoff cannot be engineered away, only chosen deliberately — and it should be chosen with farmer representatives in the room, not by whoever writes the retention config.
