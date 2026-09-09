# Local demonstration plan

Use the reviewed search/list/read design in [the overview](memory-overview.md).
Demonstration is separate from rollout. Mechanical edge cases use synthetic farmers
and a disposable store. Gautam also authorized one existing farmer with repeated
conversations: suffix 5951, selected by the most distinct stored sessions.

1. Show a general ongoing situation with no category. A later conversation should
   update its account and preserve an earlier version rather than add an unrelated
   duplicate. Include uncertainty: a visit was offered, not confirmed.
2. Add a useful new metadata key, document it, and list matching records. Demonstrate
   different keys for different farmers and never expose another farmer's sample values.
3. Ask in different wording. The live agent can search, inspect summaries, and open a
   chosen reference directly. It should stop when it has enough evidence.
4. Ask for recorded open/pending items. Follow listing pagination. Include a past
   deadline that remains recorded open, and an untagged memory that filtered listing
   misses but broad search can still find.
5. Show the team-owned standing configuration. Populate allowed fields, reject excessive
   values, and demonstrate that an invented field cannot enter every-turn context.
6. Set a synthetic farmer's reply setting off. Automatic context and all live read
   tools should return no memory, while the background writer can inspect existing
   entries without changing the flag. Missing settings default on under the global
   switch, per the current temporary policy.
7. Make a check unavailable: retry, then leave the change unwritten and report why.
   Show that a failed update leaves the old memory current.
8. Demonstrate long-detail continuation, older-version references, missing IDs,
   malformed service responses, and a service timeout without inventing absence.

Record what the current bot actually received and requested. Do not prefetch detail
that its agent did not choose to open. Measure total waiting and prompt size. A local
demo passing is not a substitute for the held-out evaluation in the backtesting plan.
The Amul memory collection was backed up before the authorized reset. Settings are
preserved, other collections untouched. Real-source training uses 326 turns before
2026-09-07T16:16:53.389Z; the later 12 turns in two sessions are held out.
The configured vLLM is Gemma 4 31B IT. No proactive messages or production bot global
enablement is part of this demo. The local read-only agent probe registers only the
actual memory tools; full chat routing/live Amul-tool behavior needs broader testing.

The completed one-farmer observations and limitations are in [the demo review](demo-review-2026-09-09.md).
