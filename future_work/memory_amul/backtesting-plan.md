# Backtesting the revised memory design

The first 20-farmer paired replay was run on 9 September 2026. See
[the backtest review](backtest-review-2026-09-09.md) for outcomes, artifacts and limits.
The remaining sections describe the broader evaluation needed before wider use.

## Compare the same bot, with and without memory

For each held-out question, run the same model, prompt, and live-tool fixtures twice:
memory off and memory on. Historical production replies are useful additional context,
not the sole control, because the bot itself has changed since those replies.

Build each farmer's memory only from turns before that question's cutoff. Process
turns in chronological order, including interleaved sessions; no trace after the memory cutoff may
enter extraction, consolidation or profile evidence. Replay operational tool results
as they existed for the held-out question, never from after that question. `--days`
is now anchored to `--until` when supplied. Use separate test settings and an isolated
collection, never turn live farmer flags on/off to implement this comparison.

## Cover ordinary conversations as well as memorable cases

Include useful ongoing situations, explicit preferences, ambiguous animal references,
multiple issues in one turn, repeated sessions, different wording/languages, incomplete
bookings, sensitive admissions, routine fully answered questions, and irrelevant
questions where memory should not be mentioned. Include farmers with little/no memory
and different metadata vocabularies. Log-study examples are starting cases, not the
whole test set and not a mandatory classification scheme.

## Exercise the actual agent path

Inject the configured standing record and relevant headlines. Let the normal reply
agent choose search/list/read tools; do not hand it arbitrary extra detail. Record:

- Which context and farmer-specific keys reached the prompt, including omissions.
- Queries, optional filters, selected references, list cursors and whole-chunk next pages, and
  whether broader search recovered a relevant untagged memory.
- Whether the reply preserved uncertainty and avoided irrelevant or intrusive recall.
- Every write decision, selected supporting turns, exact trace/session provenance,
  repeated-run duplicates, incorrect merges, and failures reported for retry.
- Waiting time, timeout behavior, extra requests, and prompt/output size.

Test disabling separately: global off, default-on user setting, explicit user off,
and unavailable settings. Background learning must not flip a reply-use flag.

## Judge usefulness and harm separately

Review whether memory reduced repetition or improved advice, and independently review
false recall, stale certainty, wrong account/animal attribution, sensitive retention,
and unsupported action confirmations. Require evidence for a claimed improvement.
A lower score on intrusive or misleading replies cannot be averaged away by more
convenient personalization.

Offline tests establish mechanical behavior. They do not measure extraction quality,
semantic merge correctness, or real response improvement. Program owners should agree
release criteria and review the resulting examples before rollout. Voice and doctor
mode require their own evaluation and are not covered automatically by farmer chat.

## Evaluation scope after the one-farmer demo

See [the demo review](demo-review-2026-09-09.md) for actual failures. The next run
should first use the full Amul agent/prompt and the model configured for replies;
the local Gemma smoke test alone cannot establish that the production agent makes
the same tool choices. Record the model/provider and all prompt/config versions.

Completed first batch: **20 farmers, 100 held-out turns**, with a frozen memory
snapshot per cutoff. Choose farmers by conversation depth and coverage rather than
cherry-picking attractive memories. Include low-memory farmers and ordinary questions.
Use all prior turns needed to understand a held-out question, but never train on the
question or later replies. Fixture live tools with identical question-time responses
for memory-off/on runs; no bookings, orders or messages should be executed by a replay.

Measure three things separately:

1. **Memory construction:** can reviewers find important source details in current
   episodes? Inspect late facts such as missing receipts, incorrect omissions,
   unnecessary retention, overly broad safety refusals, duplicate fragments and
   incorrect merges. Check every supplied source reference, but remember that a valid
   reference does not prove its facts were retained. Include a few repeated generation
   runs to measure variability.
2. **Agent retrieval:** does an ordinary list/count question use list and follow its
   cursor? Does search broaden when a specific fact is absent? Does direct read open
   the suggested chunk? Compare returned chunks with stored text byte-for-byte. Test
   missing metadata tags and independent farmer vocabularies. Tools control sizes;
   the agent should not need to calculate budgets or offsets.
3. **Reply quality:** fewer repeated questions and better continuity, judged separately
   from false recall, unsupported bookings, wrong animal attribution and unnecessary
   historical details in live-record answers. Blind the memory condition for human
   reviewers where practical. Do not average harmful recall away against convenience.

Report paired outcomes, not only average scores. Include failure transcripts, all
model/tool latencies, context size, request counts, and p50/p95 from the larger sample.
The one-farmer median is only a warm smoke-test observation. Keep exact-list
completeness and source-detail retention as explicit release criteria.

After the baseline, compare semantic-only discovery with allowing contents-guided
reads, using the same stored episodes and tools. Add a dedicated keyword index only
if measured failures justify it. Do not add required category labels to make tests
easier. The first paired replay and a separate selected cross-session follow-up
study are complete; see [the follow-up review](followup-review-2026-09-09.md).
The follow-up study produced 2 improved, 12 equivalent and 1 worse answer, with
no memory tool calls. Agentic retrieval therefore still needs its own test set.
Keep these cohorts separate: the ordinary-traffic sample mostly contained current
record lookups, while the follow-up set was deliberately selected for continuity.
The small 10/5/3-turn extraction experiment found no recovery gain from smaller
batches. Repeat a fixed annotated case set before changing the default of 10.
