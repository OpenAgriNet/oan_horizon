# Amul Memory — Overview (start here)

This is the one-stop version of everything we've worked out so far about giving
Sarlaben (Amul's dairy-farmer chatbot) memory of past conversations. It pulls together
the design thinking, real examples from actual farmer conversations, made-up examples
to stress-test the idea, and the Honcho-vs-build-it-ourselves comparison — all in one
place, in plain language.

**This is a working draft, meant to be marked up.** Under every example below there's a
line to fill in — whether it's something we actually want to support, or something
we're consciously choosing to skip for now. Nothing here is decided yet.

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

A few rules we think should shape any memory design, regardless of how it's built:

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
   farmer's concern (see Example 6 below) does real damage to trust — more than just
   staying quiet would have.
4. **Not everything should be remembered.** Some things a farmer says are sensitive —
   money troubles, something they'd rather the cooperative not know, a mistake they
   made. Remembering everything forever, and letting all of it flow into every system
   that touches this bot, could make farmers stop telling it the truth. What to keep,
   for how long, and who else can see it needs a real, deliberate answer — not a
   default of "keep everything."
5. **Keep "hard facts" and "things we've noticed" separate.** A farmer's cooperative,
   how many animals they have, which of two linked accounts they usually mean — these
   are simple facts that don't need any clever reasoning, just a lookup. Things like
   "this farmer has asked about the same unresolved problem three times" are a
   different kind of memory — they need some actual thinking to notice, not just a
   lookup.

---

## 3. Real examples — things that actually happened

We pulled real conversations for 8 farmers who use the bot a lot (checked in daily or
almost daily over a month) and read through everything they said, looking for moments
where remembering something from before would have made a real difference. These are
real, not made up (exact dates/quotes are in `log-findings.md`).

For each one: what happened, why memory would help, and a line for you to mark.

### Example 1 — Told "I don't know" the same question, over and over
A farmer asked "when will this month's payment arrive?" on 8 different days over two
weeks. Every single time: the exact same "I don't know, contact your society" answer,
with no sign the bot remembered saying this before.
**Why memory helps:** Even just recognizing "I've told this person this many times
already" would make the answer feel less robotic and more honest.
**Priority:** [ low ] **While we have said the same answer multiple, each time we need to look up the tool and figure out the status etc through the tool to understand if that has changed, only tone can be improved through this and though a better experience for the user,  not very high priority. where what we can do it later allow for reasoning capabilities for the user, where we automatically check status at some interval for the user and get back to them for this. lets create a new sections titled Memory x Reasoning  --> where we can build other capabilities like scheduled messages and toool calls etc such that it helps the farmer to get info.  For exmaple this can be done by simple scheduling a message from the user at any interval they desire. what other minimal feature canwe have to improve reasoning also and make the bot more useful alongside this. lets maintain a feature list.  

### Example 2 — The same unexplained money deduction, asked about for weeks, never resolved
Three different farmers each had a deduction on their account they didn't understand.
Each asked about it repeatedly (5-8 times, over 1-3 weeks) and got a different vague
non-answer every time. Nobody ever said "you've asked this before and I still can't
explain it" — which would at least be honest.
**Why memory helps:** Noticing "this exact problem keeps coming up, unresolved" is a
real signal that a human should step in — this is more than just recall, it needs the
system to notice a pattern, not just remember one fact.
**Priority:** [ low ] **Very simlar to the above where the farmer has some repeated issue. Ar we saying multiple farmers used the same userid and mentioned simlar problems. this is good for memory store, and for us to later analyse, but not useful for the farmer themselves. maybe we can create a feature where we summarise recurring farmer problems identified the memmories with identities redacted such that its useful for Amul. This is another reasoning feature. Lets look into this separtely as another feature. 

### Example 3 — Asked "which cooperative are you with?" even after the bot already knew
Two different farmers were asked to clarify which dairy cooperative/union they belong
to — sometimes even in the *same conversation* where the bot had just used that exact
information minutes earlier for a different question.
**Why memory helps:** This is the simplest, cheapest kind of memory — a fact that
should just be looked up once and never asked again.
**Priority:** [ medium ] **This feels like some Amul stack tool call that is currenlty made each time, but in case its the same user that is using, this  can be made easier for the farmer. The issue is we should use tool calls to figure out cooperative as the downstream answers can change because of this. I think the best way is to store the cooperative in memory and then instead of asking farmer which cooperative they are from, ask them if they are from "this" cooperative. this protects us from giving ourt wrong data based on memory but makes user experience easier, where they have to jsut say yes instead of the location name. 

### Example 4 — Asked "cow or buffalo?" when the bot already knew the answer
A farmer asked to book a vet visit for artificial insemination. The bot asked "cow or
buffalo?" The session ended before the booking finished. An hour later, in a new
conversation, same request — same question, "cow or buffalo?" — even though the bot
had already looked up this farmer's animals the day before and knows they only have
one, a cow.
**Why memory helps:** The bot is asking a question it already has the answer to.
**Priority:** [ Medium ] **Similarl to above, we can use memory to supplant all the information, just tell the user before booking, that shouuld I book for 1 cow ? and wait for the user to give the confirmation. 

### Example 5 — A serious animal-health issue nobody followed up on for 10 months
The bot's own records show a cow hasn't had a successful pregnancy in about 10 months
since her last insemination attempt. The bot itself had once said "if this doesn't
work, book a health check" — nobody ever did, and nothing ever reminded the farmer.
**Why memory helps:** This is memory being used to *proactively* bring something up,
not just answer when asked — a stronger, harder kind of memory than plain recall.
**Priority:** [ low ] We need to build the ability to schedule messages from the model etc for this, ehnce putting as low; otherwise this is a good example.  Lets add another feature into Memory x Reasoning where the chatbot can send scheduled messages to the user.  This can be a part of the reflecting/dreaming where the model can decide to enquire about the health etc. 

### Example 6 — Misunderstood a farmer's real worry and made it worse
A farmer said, upset, "remember, I'm not selling any animals" and referenced that one
of their buffaloes was "deleted" from the system two months ago — a real, specific
complaint. The bot misread "deleted" as calving news and congratulated them — making
the farmer's frustration worse, not better.
**Why memory helps:** If the bot remembered this specific past complaint, it wouldn't
have misread what the farmer meant.
**Priority:** [ medium ] **This is a good use case, though this has been conflated with translation issues here.  If we make some mistake while answering the user we should be able to remember that and make sure we dont repeat it the next time especially if the user recognizes the issues and berates the bot fot it. This would require a cheap semantic/word serch on the meory to be able to surface this instance and conversation when the farmer makes the call. The second way is similar to first, just listing out everythign, first way was explicity related to complaints by user, but the fact that thier

### Example 7 — Same complaint, raised again and again for three weeks, never connected
A farmer kept saying some of their animals weren't showing up correctly in the system,
and that nobody in their cooperative was getting scheme benefits. Raised on four
different days across three weeks. Every time, the bot restarted the conversation from
zero, with no sign it remembered this was already an open, unresolved issue.
**Why memory helps:** Same as Example 2 — an unresolved thread that should get
escalated, not repeated.
**Priority:** [ Low ] **Again similar 1,2 . In memory we keep track of such complaints and the number of time its been raised, and its current status (has it been resolved etc) Again not useful without the extensions discussed earlier, that we can just scheulde some checks. Currently can only improve tone. 

### Example 8 — A farmer believed help was already on the way, when it wasn't (our top concern)
A farmer reported a sick animal (skin problem, then coughing, worried it might be
contagious). Over one afternoon, across 7 different conversations, the bot offered
**eleven times** to book a vet visit — but never actually confirmed a booking. Days
later, the farmer asked "what medicine can I give until the doctor comes" — clearly
believing a vet visit was already arranged. The bot's own wording ("you're waiting for
the doctor") made this worse by sounding like it agreed. Twelve days after the original
complaint, the same animal couldn't stand anymore, and the farmer was still just
asking home-remedy questions.
**Why memory helps:** This isn't about being polite or personal — a farmer may have
delayed getting real help because they thought it was already coming. This is the one
example in this whole list with real safety stakes, not just convenience.
**Priority:** [ Medium ] **A few caveats here. Memory is not the universe of the farmer. Just because something doesnt happen in the chat dosesnt mean it couuldnt have happened somewhere else. The farmer may have booked doctor elsewhere. Dont assume based on session. But from the use case its important to have a very compact history and current status of the farmer problem, for example we can quickly summarise in the memory that cattle fell sick last week (with actual date) tried these medicines so far (at least). no vet booked yet, asked 11 times but not booked on cha, could have booked elsewhre. this will help the bot give more contextual answers, saying that it has gotten worse from last time, maybe we need more medicines, call doctor etc. 

### Example 9 — Something suddenly looked wrong, with no explanation
After two straight weeks of daily milk records showing up normally, one day the bot
suddenly said "no records found" — with zero context for a farmer who might reasonably
panic that their delivery records were lost.
**Why memory helps:** Knowing what's normal for a specific farmer lets the bot say
"this is unusual for you" instead of a flat, alarming non-answer.
**Priority:** [ Medium ]  **Yes, this gives a more contextual answer, though might not be useful in genuinely fixing something. What this makes me think more about is the dreaming/reflecting part can be used for other things since its reflecting anyway. We can use it to tag issues, farmer greivances and especially content gaps. this can help improve the overall bot.  This can be done now itself, doesnt require anything extra. We will anyway store the output of the dreaming to Qdrant, can store these too to another collectiona nd keep deduping such that we  have a good list of missing content that can be added. The dreaming model makes a choice what to add to the missing_content, farmer_complaints datastore that Amul can analyse later. 

### Example 10 — Useful details given once, then gone
A farmer once explained, in detail, exactly what feed they were using and how much it
cost, wondering if it was worth it. That's exactly the kind of information that could
power a real "is this working for you" answer later — but it disappears the moment the
conversation ends.
**Why memory helps:** Farmers volunteer useful details unprompted sometimes — losing
them is a missed opportunity, not a mistake, but still worth fixing.
**Priority:** [ Medium ] **Yes, this is nice. Though we must be upfront that we are remembering from memory that they have said this. what to remember is a very critical thing. Does Hancho have some agentic setup that works well at deciding this, which will be much simpler than our schema. but we should have some schema setup anayway so that we can control some aspects that we want and maybe let the agent decide whaat else with some token budget so that memroy doesnt eat too many tokens (the part of the memory that is retrieved every turn. I am assuming there is some memeory that is retrieved every turn no matter what and some that needs to be seaeched based user using some quick search and some that can be activaley searched throhug agent. )

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

## 4. Made-up examples — to think beyond what we happened to see


**Is this something that Hancho can compe with automatically, figure out that storing and use them in a certain way would improve experience hence storing them; dont think so. 

The real examples above only cover 8 farmers over one month, so they can't show
everything. These next ones are **invented**, not from real logs — written to explore
areas the real examples didn't really touch: the vet-facing side of the bot, the loan
feature, things tied to the farming calendar, families sharing one phone, and — on
purpose — the limits of what memory should even try to do. Every one below names a
real downside, not just an upside; more memory isn't automatically better.

### A. The vet side of the bot (a separate "doctor" mode exists for actual veterinarians)

**A1 — No vet ever sees the full picture on a repeat case.**
An animal gets inseminated four times over seven months. Three different vets each see
it once, each starting fresh, and nobody ever notices "this animal keeps failing to
get pregnant — time to investigate why" instead of just trying again.
*Watch out for:* if an early vet's guess gets remembered as settled fact, it can bias
every vet after them instead of helping them think freshly.
**Priority:** [ low ] **nah, not in scope for us.  

**A2 — Forgetting a treatment could spoil milk for a whole village.**
A vet treats a cow with medicine that means her milk must be thrown away for a few
days. The farmer pours it into the shared collection anyway, not realizing — and the
whole village's pooled milk fails a safety test because of it. The bot knew about the
treatment and could have reminded him, but didn't.
*Watch out for:* if this reminder is ever late or wrong, farmers will (reasonably)
blame the bot for the mistake — a safety reminder that only sometimes works may be
worse than none at all.
**Priority:** [ low ] **fair use case, again tied to being able to tell the farmer, again this should be something the bot asks the farmer, do you want tme to remind you everyday until tomorrow to not use the milk ? 

### B. Money that only makes sense looked at over months

**B1 — Told "no" for a loan, and never told when that changes.**
A farmer is turned down for a loan in January for a specific reason. Months later, the
reason no longer applies — but nobody tells him, because each new conversation has no
memory a door was ever closed.
*Watch out for:* proactively telling someone they now qualify for a loan is a nudge
toward debt — this needs to be done carefully, not just because we technically can.
**Priority:** [ low ]. **again tied to being able to message the farmer, and there is a universe the bot doesnt know about, but yes, for schemes, launches etc, it can ask the farmer if they want to be reminded when the day comes or schemes expire etc as a reaosning use case. 

**B2 — A farmer tried something new and never found out if it worked.**
A farmer mentions changing what she feeds her cows to try to increase milk. Months
later she asks if it was worth it — and with memory, the bot could actually check: did
her income go up more than her costs did?
*Watch out for:* lots of other things changed in that time too (season, calving) — a
confident wrong answer here is worse than admitting we can't tell for sure.
**Priority:** [ medium ] **I think this is own use case, we can create a   a tracker using memory, where the farmer can keep saving the information about some subject over time, how cashflow/ treatment etc has gone and keep udpateing and checking that info when required. this is a good use case. 

### C. The farming year has its own clock

**C1 — Personal breeding-season advice, not generic advice.**
Knowing a specific farmer's animals tend to struggle to conceive in the hot summer
months (because we've seen it happen to them before) lets the bot warn them ahead of
time, instead of giving the same textbook advice to everyone.
*Watch out for:* pushing a farmer to act on a calendar date without knowing the
animal's actual condition could do more harm than good.
**Priority:** [ medium ] **While keeping track in memory, we can tie to the feeding/farming calendar which can make this more useful. can build that logicn ito honcho/ agent that stores 

**C2 — Bringing up vaccination at the right time, sensitively.**
A farmer lost an animal to a disease outbreak once and still thinks about it. Every
year, the vaccine for that disease needs to happen before the rains — and every year
she asks about it just after the rains start, too late. Memory could prompt this
conversation at the right time.
*Watch out for:* bringing up the loss itself, every year, could feel hurtful rather
than helpful — the reminder should change in *timing*, not turn into reopening old
grief.
**Priority:** [ medium ] **memory can keep track of which vaccincations are done, and what are pending etc. can be tied to to other use cases. 

**C3 — Remembering a wish, for when it becomes possible.**
A farmer once mentioned wanting to buy equipment but couldn't afford it. Months later,
a relevant government subsidy opens for a short window — memory could connect the two.
*Watch out for:* by then he may have already bought it another way — an old wish
shouldn't be assumed still true, it should be double-checked ("is this still something
you want?").
**Priority:** [ medium ] **also good, gives us more context to a question, when they ask about a scheme etc or some info , and we can directly say that if they are planning to do this, then this is an option. 

### D. Whoever's actually holding the phone

**D1 — More than one person uses the same phone number.**
A household phone gets used by the father, his adult son, and his wife — each asking
about different things. Memory could tell them apart and give each the right context,
instead of treating "whoever calls" as always the same person.
*Watch out for:* getting this wrong is worse than not trying — showing one family
member's private information (like a loan application) to whoever else picks up the
phone would be a real problem.
**Priority:** [ low ] **very risky, better avoid. 

**D2 — A call drops mid-booking, and the farmer assumes it worked.**
A phone call drops right as a booking is being confirmed. The farmer doesn't call
back, assuming it went through (this exact failure already showed up in real logs —
see Example 8). With memory, a text message afterward could catch this: "your booking
wasn't actually completed — reply to confirm."
*Watch out for:* only worth doing for things that actually matter (a real booking),
not every dropped call — otherwise it just becomes annoying, constant notifications.
**Priority:** [ low ] **can be avoided, people ususally know when they dont book, annoying to get reminders to book. 

**D3 — Learning how a specific person talks, to stop mishearing them.**
If the voice system keeps mishearing the same farmer's numbers or names the same way
every time, and he corrects it every time, that correction is currently thrown away.
Remembering it could stop the same mistake from happening again.
*Watch out for:* if a correction is ever learned wrong, it becomes a *new*, harder to
notice mistake — this needs to be easy to undo.
**Priority:** [ low ] **kinda useful to understnad mistransaltions and corrections, maybe we can do simlar thing as dreaming, where if a farmer corrects some grammar/transaltion, we can add it as a draft to the glosary (one of the things along with content gaps etc that can be triggered ), whcih can be verified and used later. 

### E. Looking across many farmers at once, not just one

**E1 — Spotting a possible disease outbreak early.**
If several unrelated farmers in the same area independently describe similar animal
symptoms within a few days, that pattern — invisible to any single conversation — could
be an early warning worth telling a real vet or the cooperative about.
*Watch out for:* this is the most sensitive privacy line in this whole document — no
farmer's information should ever leak to another farmer, and a false alarm here could
scare a whole local market unnecessarily.
**Priority:** [ low ] **to be done later 

**E2 — Spotting a quality problem with a service, not a person.**
If one particular technician's visits consistently lead to worse outcomes than others
nearby, that pattern points to something worth checking (equipment, technique) — but no
single farmer could ever see it.
*Watch out for:* this quietly grades a real person's work using data that depends on a
lot of things outside their control — handled carelessly, it could feel like
surveillance and make workers less honest about problems, not more.
**Priority:** [ low ] **not required. risky

### F. What memory owes the farmer — knowing when to forget, and being honest

**F1 — Not cheerfully bringing up an animal that has died.**
If an animal has died or been sold, the bot should stop asking about it or reminding
the farmer about it — immediately, not eventually. Memory that only ever adds and never
removes is careless, not helpful.
*Watch out for:* the only way we'd know an animal died is often just something a
farmer mentioned once in passing — acting on that with full confidence, if it turns out
wrong, is its own kind of mistake.
**Priority:** [ low] **too risky

**F2 — Checking back on advice, and knowing when to stop offering something.**
If the bot suggested something for a sick animal, following up later ("did that help?")
turns one-time advice into something that actually learns. The same idea also means: if
a farmer has said no to hearing about a certain scheme four times, the bot should just
stop offering it — without being told to.
*Watch out for:* asking "did that work?" costs the farmer's time and attention too —
should be light and skippable, and never asked about something that ended badly.
**Priority:** [ low] **lets be careful about prompting the farmer, make very concious choices on when to ask farmer and have some blocks etc on it. 

**F3 — Some things this bot should probably never keep.**
Farmers will sometimes tell this bot things that are true and risky for them to have on
record — a side-sale outside the cooperative, a financial struggle, something they're
not supposed to have done. If the bot remembers everything and any of that could ever
reach the cooperative or a bank, farmers will learn to stop being honest with it — which
would defeat the whole point of memory.
*Watch out for:* this is a real trade-off, not something to solve with a clever trick.
Being more careful here means missing some chances to help; being less careful risks
real harm to farmers who trusted the bot. This should be a deliberate decision, ideally
with input from people who represent farmers, not just an engineering default.
**Priority:** [ high ] **we sohuld be careful with what we store, never store anything the farmer could be uncomfortable with later 

---

## 5. What would "Honcho" actually add, compared to building this ourselves?

Honcho is an existing, ready-made piece of software that other companies use to add
memory to a chatbot. The question is: what does it give us that we couldn't get by just
using the tools we already have (a database for storing information, and an LLM we
already use for chat)?

**The "remember new information" part is basically identical either way.** Honcho's
version of this and a version we'd build ourselves both work the same way: read a
conversation, ask an LLM to pull out the important facts, save them. No real advantage
either way.

**Where it's actually different — two things:**

1. **A smarter way to answer questions about the past.** If we build this ourselves in
   the simplest way, "remembering" means: take the current message, find the most
   similar-sounding things said before, and hand them to the bot. That's fast, but it
   can miss things — like a farmer complaining about the same problem three times, each
   time in different words. Honcho can instead take a few extra steps to actually look
   for a pattern — search a few different ways, check dates, follow a chain of related
   facts — before answering. This is genuinely useful for exactly the "has this come up
   before, and how many times" kind of question from Examples 2 and 7 above.
2. **A background step that looks for patterns on its own, ahead of time.** Beyond just
   storing facts, Honcho also has a separate process that periodically re-reads
   everything it knows about someone and writes down bigger-picture conclusions — like
   noticing on its own that a complaint has come up repeatedly and is still unresolved.
   Because this happens in the background, by the time anyone asks a question, the
   pattern is already written down and easy to find — no extra thinking needed at that
   moment. This is exactly the kind of "unlimited pre/post-session compute" our guiding
   principle (Section 2) already says we're fine spending.

**What it does *not* give us:**
- **No ready-made structure for simple facts.** It doesn't hand us a clean, fixed
  record like "cooperative: Banas, animals: 3" — it stores loose, free-text notes. For
  simple stable facts (Examples 1, 3, 4), we'd still want a simple, separate, structured
  record regardless of whether we use Honcho — this isn't something Honcho solves for
  us.
- **It doesn't solve our top concern (Example 8) at all.** Making sure the bot's words
  match reality — never implying a booking happened when it didn't — needs its own
  simple tracking (a checklist of "was this actually done, yes or no"), completely
  separate from any memory system. Neither Honcho nor a custom build gets this for
  free; it has to be built deliberately either way.
- **It's extra software to run and maintain.** Using Honcho means running its own
  database and its own separate background program, on top of what we already run.
  Building it ourselves means reusing what we already have running today (a database
  we've already set up for this).

**In plain terms:** Honcho is worth it specifically if we care most about the
"noticing a repeated, unresolved problem" kind of examples (2, 7, and similar). If we
mostly care about simple facts and making sure promises are kept (1, 3, 4, 8), a
much simpler homemade version gets us there without new software to maintain.

---

## 6. A simple, minimal option (if we build it ourselves)

- **A small background job**, separate from the main chatbot program, that after each
  conversation (or every so often) reads what was said and asks an LLM to pull out a
  few plain-language facts worth remembering — then saves them into a database built
  for fast lookups (we already Qdrant set up and ready to use).
- **During a live call or chat**, when the bot needs to check what it knows about a
  farmer, it does one fast, simple lookup (no "thinking" step, no extra wait) and adds
  a short summary of what it found to the top of the conversation — the same way the
  bot already adds a short, useful summary block for other things today.
- **No new software to run.** This reuses the database we've already set up, and the
  same LLM access the bot already has for chatting.
- **The tradeoff**: this handles the simple, stable-fact examples well (1, 3, 4), and
  reasonably well for straightforward repeats (Example 1). It's less reliable for
  cases where the same underlying problem gets described in very different words each
  time (Example 7) — that's the case where a smarter search (like Honcho's) has a real
  edge.

---

## 7. Open questions (not decided yet)

- Do we build this ourselves, use Honcho, or mix — simple facts ourselves, harder
  pattern-spotting via Honcho?
- Does this cover just farmers, or also the separate vet-facing mode?
- Does a farmer who hasn't signed in get any memory at all, or none (like today)?
- Same memory for phone calls and the chat app, or does one come first?
- What exactly do we keep forever, what do we forget quickly, and who's allowed to see
  it? (Section 2, principle 4 and example F3 — this needs a real answer, not a default.)

---

