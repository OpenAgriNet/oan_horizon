# Real memory-value cases, found in Amul's actual logs

Where this came from, and what it means for the plan in `memory-overview.md` and
`memory-design-decisions.md`.

## How we found these

- **Where we looked**: Amul's real, live conversation logs (`langfuse.prod.amulai.in`,
  keys at `oan-brain/oan_creds/.langfuse_keys`). Chat conversations are logged with
  the actual full text of what was said, under the label `chat.translation`. Phone
  call conversations are logged with only a short preview and a scrambled version of
  the text (for privacy) — not useful for a close read, so this pass focused on chat.
- **Finding farmers who use the bot a lot, without scanning everything**: the logging
  system can rank every user by how many messages they sent over the last 30 days in
  one quick query — no need to page through every single message to find repeat
  users. That query found **77,495 different people** who'd used the chat in the last
  30 days.
- **Who we actually read**: the top 8 by message count, double-checked to make sure
  they were real farmers and not test accounts (their questions were clearly genuine
  — daily milk/payment checks, not scripted testing). Each one's full month of
  conversations was pulled and read start to finish, in order.
- **How names are shown below**: only the last 4 digits of each farmer's phone number
  (e.g. `...3007`) — enough to tell them apart in this document, not enough to
  identify anyone.
- **What this isn't**: a scientifically representative sample (8 heavy users, not a
  random sample), and it can only show what actually happened with no memory — see
  `backtesting-plan.md` for how we'd test an actual memory-equipped version against
  these same real conversations.

## The different kinds of memory value we found

Five genuinely different patterns showed up — not the same thing repeated. A design
that only handles the simplest one would miss the more valuable (and harder) ones:

1. **Remembering a plain fact** — something asked again that was already answered,
   sometimes even earlier in the *same* conversation. Cheapest to fix — just a lookup.
2. **Noticing the same unresolved problem keeps coming back** — the same unanswered
   question or complaint recurring over days or weeks, with the bot treating each one
   as brand new. Needs the system to actually notice a pattern and its count, not
   just remember one fact.
3. **Following up on something, without being asked** — a fact the system already has
   (something it said it would check on, a health status that's gone stale) that
   never gets brought up again on its own. Needs a sense of time passing, not just
   recall.
4. **Remembering a specific worry, not just a general topic** — a farmer's particular,
   named concern that the bot has no memory of, leading to real misunderstandings.
5. **Knowing whether something actually happened** — whether a requested action (like
   booking a vet visit) really went through, especially when the bot's own wording
   makes it sound like it did when it didn't. The most serious category found — see
   Case 8.

A sixth thing came up too, worth calling out as a **non-issue**: some repeated
questions are perfectly normal — checking today's milk total several times a day is
supposed to pull fresh numbers every time, not be remembered. Don't try to "fix" that
kind of repetition with memory — some of what looks repetitive is just normal use.

## The cases

### 1. The same question, answered the same unhelpful way, for two weeks (`...3007`)
Asked some version of "when will this month's payment arrive?" across 8+ separate
conversations (Aug 7 – Aug 21). Same answer every time — "I don't have exact payment
dates, contact your society" — worded slightly differently, with no sign the bot
remembered saying this to this same person before. The simplest possible case: even
just recognizing "I've said this 6 times already" would make the exchange feel less
robotic.

### 2. An unexplained deduction, asked about for weeks, never resolved (`...3007`, `...7788`, `...1036`)
Three different farmers, three different confusing charges on their account:
- `...3007`: a recurring ₹1,200 charge, asked about 7+ times over a week (Aug 13–20),
  a different vague non-answer each time.
- `...7788`: a ₹4,400 charge, asked about across 6 conversations over a week — at one
  point the answer actually got *worse* ("I can't see your total due amount") than
  earlier attempts.
- `...1036`: a ₹5,460 → ₹10,480 charge whose account label was literally broken/
  garbled in the system — asked about once, then silently kept showing up in every
  weekly report for 4+ more days, ending the month net-negative, with no
  acknowledgment it was the same unresolved thing.

None of these ever got "you've asked this before and I still don't have an answer" —
which would at least be honest. This is the clearest case for **noticing a repeated
problem**: the same unanswered question 5+ times is a real signal something needs a
person to step in, not something a lookup alone fixes.

### 3. Asked for the same basic fact, sometimes twice in one conversation (`...3007`, `...7788`, `...7896`)
- Two different farmers were asked "which dairy cooperative are you with?" — even in
  conversations where the bot had *just* used that exact fact minutes earlier for a
  different question. Happened 5+ times each across the month.
- One farmer has two linked accounts on file. Disambiguation was asked **three times
  in a row within one 10-minute conversation**, until the farmer finally spelled out
  the full name themselves to force it through — then in the very next conversation,
  the bot silently picked the *other* account without asking, inconsistently.

The cleanest case in the whole set for "just remember the plain fact" — something
that should be set once and never asked again, currently re-asked even within a
single conversation.

### 4. Asked a question the bot already had the answer to (`...5963`)
Farmer asked to book an artificial-insemination vet visit; bot asked "cow or
buffalo?" The conversation ended before the booking finished. About 1.3 hours later,
same request, new conversation — same question, "cow or buffalo?" — even though the
bot had already looked up this farmer's animals the day before and knows they have
exactly one, a cow. The question was unnecessary.

### 5. A real health issue nobody followed up on for 10 months (`...5963`)
The bot's own records: last insemination attempt 10 months ago, still not
successfully pregnant. The bot itself had once said "if this doesn't work, book a
health check" — nobody ever did, and nothing ever reminded the farmer. **The
strongest case for using memory to proactively bring something up**, not just answer
when asked — the facts needed are already there, what's missing is noticing that a
lot of time has passed with no follow-through.

### 6. A misunderstood complaint that made things worse (`...5951`)
Farmer said, clearly upset: *"remember, I am not going to sell any animal"* and
referenced that one of their buffaloes was "deleted" from the system two months
earlier — a real, specific complaint. The bot **misread "deleted" as calving news**
and congratulated them — making things worse, not better. A bot that remembered this
farmer's specific past complaint wouldn't have misread what they meant.

### 7. The same complaint, raised repeatedly for three weeks, never connected (`...5951`)
"I have 12 animals but only 5 show online" / "nobody in my cooperative is getting
scheme benefits" / "it shows 0 milking animals but I deliver 40 liters a day" —
raised across at least 4 separate days over three weeks, restarting from scratch
every time. One conversation ran 56 turns covering the same ground plus a broader
complaint about their whole cooperative. Nothing ever acknowledged this was already a
known, weeks-old, unresolved issue for this specific farmer.

### 8. A farmer who believed help was already coming, when it wasn't — our top concern (`...3048`)
A sick-animal case (skin problem, then coughing, worried it might be contagious)
played out across **7 different conversations in one afternoon** (Aug 20). The bot
offered to book a vet visit **eleven times** — but never actually confirmed a
booking, at one point saying plainly *"you haven't scheduled a visit yet, so the
doctor hasn't been informed... is this for a cow or a buffalo?"*, which the farmer
never answered.

**Nine days later** (Aug 29), the farmer asked *"until then, what medicine can I give
the cow?"* — language that only makes sense if they believed a vet visit was already
arranged. The bot's own reply used the phrase *"you are waiting for the doctor"* in
the same breath as urging them to book — **its own wording reinforced the farmer's
false belief that help was already coming**, when nothing had ever been booked.

**Twelve days after the original complaint** (Sep 1), the same animal could no longer
stand, and the farmer was still just asking about home remedies.

This is the single most serious case found: a farmer may have delayed getting real
help for a worsening animal because they believed help was already on the way.
Memory here isn't a nice-to-have — it's the difference between honestly saying "we
never actually confirmed this booking" and letting a real situation drift for nearly
two weeks. **Making sure the bot's own words match what actually happened should be
treated as a hard requirement, not an optional extra.**

### 9. Something suddenly looked wrong, with no explanation (`...3007`, `...7896`)
- `...3007`: after 13 straight days of normal daily milk records, two conversations
  on Aug 19 suddenly returned "no records found" — with zero context, for a farmer
  who might reasonably worry they'd lost their delivery record.
- `...7896`: three separate conversations 6 days apart (Aug 11, 15, 17) all returned
  "no milk records found," with the farmer directly asking "is my account even set up
  right, can my name be changed?" — getting the same unhelpful answer each time, with
  no sign the bot noticed this was the same unresolved problem recurring.

The value here isn't recall — it's **noticing something's broken a normal pattern**
and saying so, instead of a flat, alarming non-answer.

### 10. Useful details, given once, then lost (`...5951`)
A farmer once explained, in real detail, exactly what feed they were using and what
it cost, wondering if it was worth it. Exactly the kind of information that could
power a genuine "is this actually working for you" answer later — but it disappears
the moment the conversation ends.

## Repeated questions that are NOT memory problems

A few things that looked like memory gaps turned out to be something else:
- **`...7472`** mostly asks the same narrow, routine questions many times a day —
  that's supposed to pull fresh numbers every time, not be remembered. The one real
  issue found here: asking the *exact same* question minutes apart returned a
  **different number each time** (₹2,596.35 → ₹2,596.75 → ₹2,758.28 → ₹2,619.58
  within about an hour) — that's a data-accuracy bug, not a memory gap, but it could
  easily read to a farmer as "the bot is unreliable."
- Two farmers (`...1036`, `...7788`) hit account labels that were literally broken/
  garbled in the underlying system — memory can't fix a broken label, only an actual
  data fix can.
- Repeated "when will my payment arrive → I don't know" exchanges (`...3007`,
  `...3048`): memory can't invent an answer that doesn't exist anywhere. The fact
  that the same question always fails the same way is worth flagging to whoever owns
  that missing data — but that's a data-completeness problem, not something memory
  fixes.

## What this means for the design

- **Case 8 (the false "help is coming" belief) should be the top scenario tested
  before shipping anything** — it's the one case with real safety stakes, not just
  convenience. Worth specifically replaying this exact situation (`...3048`, Aug 20 –
  Sep 1) with a memory-equipped version and checking whether it would have either
  actually completed the booking, or at least never implied it had.
- **Cases 2, 6, and 7** (noticing a problem keeps recurring) need real thinking, not
  just a lookup — a plain "find similar things" search on its own won't produce "you've
  asked this 5 times" as a fact on its own; something has to count and reason about it.
- **Cases 1, 3, and 4** (plain, stable facts) are cheap — a small, structured,
  low-latency lookup, no reasoning needed.
- **Cases 5 and 10** (following up proactively, remembering volunteered details) need
  timestamps and a "did we ever follow up on this" mechanism on top of plain recall.
- **The non-issues above** are a reminder that the goal isn't "make repeated questions
  go away" — some things genuinely should be looked up fresh every time; memory
  shouldn't get in the way of that.

## Made-up scenarios (not from real logs — written to think beyond what 8 farmers over one month could show)

Everything above actually happened. The scenarios below are **invented** — written
(with a larger model, briefed on how Amul's bot actually works, and told specifically
not to repeat the categories above) to explore territory the real logs are too small
or too short a time window to reach: the vet-facing mode, the loan feature, things
tied to the farming calendar, more than one person sharing a phone, patterns across
different farmers, and — deliberately included, not left out — the real limits of
what this kind of memory should even try to do. Every scenario below names a genuine
downside, not just an upside — more memory isn't automatically a good thing.

### A — The vet-facing mode: case files, not one-off visits

#### 1. No vet ever sees the full picture on a repeat case

Buffalo tag ending 4471 in Nandotra has now been inseminated four times in seven months. In March, Dr. Prajapati palpated her and noted a mild endometritis; in May a stand-in vet on the same round gave a routine PGF2α and told the farmer "try again next heat"; in July a third vet is looking at a cold animal and starts, again, from zero. Each of them had exactly one visit's worth of context, so nobody ever crossed the threshold where "unlucky" becomes "this is a repeat breeder, stop inseminating and investigate — mineral deficiency, cystic ovary, silent heat, or a semen-handling problem at the sub-centre." A vet on a 30-animal round has maybe ninety seconds per animal; the memory has to hand him the pattern, not the archive.

**Memory would need to track:** a clinical timeline for each specific animal (not each farmer) — insemination dates, drugs given, what's already been ruled out, which vet said what — plus a flag that fires on its own ("4th attempt, still not pregnant"). Has to survive the animal changing vets, villages, and owners.

**Downside to watch for:** if one vet's early guess gets treated as settled fact by the next vet, memory has narrowed the search instead of widening it. Every remembered clinical note needs to carry who said it and how sure they were, and unconfirmed guesses should fade or be clearly marked as unverified.

#### 2. Forgetting a treatment could spoil milk for a whole village

Kanubhai's crossbred cow gets medicine for an udder infection that means her milk must be thrown away for a few days. He's told to discard it, understands it as "don't pour tomorrow," and on Thursday morning pours all four animals' milk into the shared collection as usual anyway. The pooled sample from his village then fails a safety test because of it — his mistake, everyone's loss. The bot knew about the treatment and knew his usual pouring pattern, and said nothing on either the vet side or the farmer side.

**Memory would need to track:** which drug means how many days before milk is safe again, tied to that specific animal, shared between the vet's records and the farmer's own conversations; and the farmer's usual routine, so a reminder lands the evening before, not after.

**Downside to watch for:** this is the clearest case where memory creates real liability. If a reminder like this is ever late, wrong, or just fails to send, the farmer will reasonably say "the bot told me it was fine." A safety reminder that only sometimes works may be worse than never having one.

### B — Money that only makes sense looked at over months

#### 3. Told "no" for a loan, never told when that changes

Bhikhabhai applied for a small loan in January to buy a second buffalo and was turned down — his average income was too low and he had an outstanding feed bill. He didn't understand why, so he asked again in February, April, and June, got the same unclear "no" each time. By August his situation has actually flipped — the feed bill is cleared, his income is up 40% — and nobody tells him, because nothing remembers a door was ever closed.

**Memory would need to track:** the specific reason for each past rejection, and a way to re-check only that reason later without re-litigating the whole application every time.

**Downside to watch for:** proactively telling someone they now qualify for a loan is a nudge toward taking on debt — that needs real care, not just "we technically can now tell them."

#### 4. A farmer tried something new and never found out if it worked

Alkaben mentioned, in passing, that she'd started adding a feed supplement because a neighbor's milk yield had gone up. Months later she asks if it was worth it — and with memory, the bot could actually check: did her income rise more than her costs did?

**Downside to watch for:** lots of other things changed in that window too (season, calving) — confidently blaming or crediting the feed change when it might really be something else is worse than admitting we can't tell for sure.

### C — The farming year has its own calendar

#### 5. Personal breeding-season advice, not generic advice

A specific farmer's buffaloes reliably struggle to conceive every hot summer — this farmer already lost time last year re-trying through the worst months. A bot that knows *this herd's* history specifically, not just the general seasonal pattern, could flag the right timing window in advance instead of giving the same generic advice everyone gets.

**Downside to watch for:** pushing a farmer to act by a calendar date without knowing an animal's actual physical condition could cause real harm — memory knows dates, it doesn't know whether an animal is actually healthy enough right now.

#### 6. Bringing up vaccination at the right time, sensitively

A farmer lost an animal to a disease outbreak once and still thinks about it. The vaccine for that disease needs to happen before the rainy season, and every year she asks about it just after the rains start — too late. Memory could prompt this conversation at the right time instead.

**Downside to watch for:** bringing up the loss itself every single year, even with good intentions, could feel hurtful rather than caring — the reminder should just come at a better time, not turn into re-opening old grief.

#### 7. Remembering a wish, for when it becomes possible

A farmer once mentioned wanting to buy equipment but couldn't afford it at the time. Months later a relevant government subsidy opens for a short window — memory could connect the two and let the farmer know.

**Downside to watch for:** an old wish can go stale — he may have already bought one another way. An eight-month-old passing comment shouldn't be treated as still true; it should be double-checked ("is this still something you're looking for?"), never assumed.

### D — Whoever's actually on the phone

#### 8. More than one person uses the same phone number

A household's registered number gets used by the father, his adult son, and his wife, each usually asking about different things. Memory that can tell them apart could give each person the right context — but this is risky territory, see below.

**Downside to watch for:** getting this wrong is worse than not trying at all — showing one family member's private information (like a loan application) to whoever else happens to pick up the phone would be a real, serious problem.

#### 9. A call drops mid-booking, and the farmer assumes it worked

A call drops right as a vet-visit booking is being confirmed. The farmer doesn't call back, assuming it went through — this exact failure already showed up in the real logs above (Case 8). With memory, a text message afterward could catch it: "your booking wasn't actually completed — reply to confirm."

**Downside to watch for:** this only makes sense for things that genuinely matter (a real booking) — doing it for every dropped call, given how common call drops can be, would quickly just become annoying, constant notifications.

#### 10. Learning how a specific person talks, to stop mishearing them

If the voice system keeps mishearing the same farmer's numbers or names the same way every single call, and he corrects it every time, that correction is currently thrown away and never learned from.

**Downside to watch for:** if a "correction" is ever learned wrong, it becomes a new, harder-to-notice mistake — this needs to be easy to undo, and probably reviewed by a person before it changes anything live.

### E — Looking across many farmers at once, not just one

#### 11. Spotting a possible disease outbreak early

If several unrelated farmers in the same area independently describe similar animal symptoms within a few days — invisible to any single conversation — that pattern could be an early warning worth telling a real vet or the cooperative about.

**Downside to watch for:** this is the sharpest privacy line in this whole document — no farmer's information should ever leak to another farmer, and a false alarm here could unnecessarily scare a whole local market.

#### 12. Spotting a quality problem with a service, not a person

If one particular vet technician's visits consistently lead to worse outcomes than others nearby, that's worth checking (equipment, technique) — but no single farmer could ever see this pattern on their own.

**Downside to watch for:** this quietly grades a real person's work using outcomes that depend on a lot of things outside their control. Handled carelessly, it starts to feel like surveillance and makes staff less honest about problems, not more.

### F — What memory owes the farmer: forgetting, grief, and honesty

#### 13. Not cheerfully bringing up an animal that has died

If an animal has died or been sold, the bot should stop asking about it or reminding the farmer about it — right away, not eventually. Memory that only ever adds and never removes anything is careless, not helpful.

**Downside to watch for:** the only way we'd usually learn an animal died is something a farmer mentioned once in passing — acting on that with full confidence, if it later turns out wrong, is its own kind of mistake.

#### 14. Checking back on advice, and knowing when to stop offering something

If the bot suggested something for a sick animal, following up later ("did that help?") turns one-time advice into something that actually learns. The same idea works the other way too: if a farmer has said no to hearing about a certain scheme four separate times, the bot should just stop offering it — without being told to.

**Downside to watch for:** following up costs the farmer's time and attention too — this needs to be light, easy to skip, and never asked about something that clearly ended badly.

#### 15. Some things this bot should probably never keep

Farmers will sometimes tell this bot things that are true and risky for them to have on record — a side-sale outside the cooperative, a financial struggle, something they weren't supposed to do. If the bot remembers everything, and any of it could ever reach the cooperative or a bank, farmers will learn to stop being honest with it — which defeats the entire point of having memory.

**Downside to watch for:** this is a real trade-off, not something a clever trick solves. Being too careful means missing real chances to help; being too loose risks real harm to farmers who trusted the bot. This needs a deliberate, considered decision — ideally with people who represent farmers' interests in the room — not just a default engineering choice.
