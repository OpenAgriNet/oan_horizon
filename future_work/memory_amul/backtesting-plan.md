# Amul memory — how we'd test it before shipping

Goal: before turning on any memory design for real, check it against Amul's real past
conversations — does it actually make answers better, and just as important, does it
**never make an answer worse or come across as annoying/creepy**? This is a replay
against history, not a live test with real farmers — see "Limitations" below for what
that does and doesn't tell us.

## Where the data comes from

- **Source**: Amul's production Langfuse (the system that logs every conversation) —
  keys live in `oan-brain/oan_creds/.langfuse_keys`. Confirm exactly where Amul's own
  keys are kept before starting.
- **What we're looking at**: a **farmer** (by phone number), not a single
  conversation — we need farmers with **multiple calls/chats spread across different
  days**, since a memory system has nothing to draw on otherwise. Because Amul's chat
  history today only lasts 2 hours, most "repeat" conversations close together are
  really just testing that short-term memory, not the new system — we specifically
  need farmers active on *different days*, not just multiple times in one sitting.
- If we test the vet-facing mode too, pull that group of users separately — different
  identities (vets, not farmers), different shape of memory, shouldn't be mixed into
  the same sample.
- For each farmer: pull every message and reply, in order, with timestamps, which
  mode they were in, and what tools/lookups the bot used. This part is fiddly — the
  logging system has some known quirks (documented in
  `oan-brain/knowledge/langfuse-api-gotchas.md`) — budget real time for it.
- **Not yet resolved — a real privacy question, not a formality**: this is real farmer
  phone numbers and real conversation content, including health/financial details.
  Needs an actual decision on how to handle that (e.g. anonymizing before it leaves
  the logging system) before any of it goes into a local testing setup — don't assume
  this is fine by default.

## How the test works — replaying history in order

Reuse the shape of testing pipeline the org already has for comparing chat models
(`oan-evaluation`) rather than building something new from scratch.

For each farmer, walk through their real conversations **in the order they actually
happened**:

1. **Before** each conversation, ask the memory system being tested what it would
   bring up — the quick facts, plus anything deeper it's noticed.
2. **Generate two versions** of each real historical reply:
   - **Without memory** — the real historical reply already exists in the logs, so we
     can just use that directly as a reference point rather than re-generating it
     (the model has changed since then anyway, so an exact re-run isn't really the
     point).
   - **With memory** — the same conversation, but with the memory context added in,
     run through the actual bot (not a stripped-down test version), so any behavior
     changes from having memory present are real.
3. **After** each conversation, feed it into the memory system so it updates —
   exactly as if memory had existed the whole time, so by a farmer's 5th
   conversation in the test, the memory system has genuinely built up everything from
   their first 4, not made-up data.

Run this once per version of the design being tested (e.g. different combinations of
what gets remembered, or different retrieval approaches) and produce one comparison
table per version, so they can be judged side by side.

## Scoring — what "doesn't regress, isn't annoying" actually means

Have an AI compare the two replies side by side (with a spot-check by an actual
person too, see below), scoring on:

1. **Got something wrong that the old version got right** — especially trusting
   stale memory over what the farmer is saying right now (e.g. herd changed, animal
   was sold, and memory says otherwise). This is a hard stop — any of this blocks
   shipping that version.
2. **Actually used the memory well** — skipped a question already answered, correctly
   referenced something real from before, gave more tailored advice instead of
   generic advice. This is the entire reason to build this — a version that never
   improves here isn't worth the added complexity.
3. **Came across as annoying or unsolicited** — bringing up something the farmer
   didn't ask about, repeating itself, over-personalizing small talk. On a phone call
   specifically, any unsolicited detail costs the farmer real time — treat this as its
   own serious failure, not a minor quality nitpick.
4. **Added real delay or cost** — how much extra content got added to the prompt, and
   for phone calls specifically, whether the actual response time matches what the
   design intended (see the speed principle in `memory-design-decisions.md`) rather
   than just assuming it in theory.

A version shouldn't ship if it regresses on (1) more than a small, defined amount, or
if it scores worse on (3) more often than it scores better on (2) — in other words, it
shouldn't be net annoying even if it's occasionally useful.

Also check a sample by hand, not just with an AI judge — the org already has a
two-person-plus-review process for other quality checks; reuse that here rather than
trusting an automated score alone.

## What this test can't tell us

- **It's a replay, not a live test.** These farmers' real questions were asked to a
  bot that had no memory, so they never had the chance to actually rely on it being
  there (skip re-explaining something, for instance) — this test can only show
  "would adding memory to this exact past moment have helped or hurt," not how real
  conversations would change if farmers knew the bot remembered them. Good as a
  before-launch check, not a replacement for watching it work with real farmers after
  launch.
- Replies generated "with memory" use whichever model/prompt is current when the test
  runs, not the exact one that was live back then (both change often) — some
  difference from the historical reply is expected and isn't itself a sign of a
  problem.

## Open questions

- Who has access to Amul's production logging system for this?
- How many multi-day repeat farmers do we actually need for this to mean anything?
  Not sized yet — depends on how common they turn out to be once we filter to
  "different days," which hasn't been checked.
- Should the vet-facing mode be tested in the same pass, or later?
