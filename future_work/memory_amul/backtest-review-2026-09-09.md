# 20-farmer backtest: completed 9 September 2026

The first paired replay does **not demonstrate a net benefit from memory**: one
answer improved, 98 were equivalent, and one became worse. The mean review score
was -0.01 on a -2 to +2 scale. A zero score means no material difference, including
cases where both answers were wrong.

Open the private workspace artifacts:

- [100-row CSV: questions, complete answers, scores and reasons](../../../amul-memory-backtest/20260909-20-farmers/memory_comparison.csv)
- [Full report and limitations](../../../amul-memory-backtest/20260909-20-farmers/backtest_report.md)
- [20-farmer summary and cutoffs](../../../amul-memory-backtest/20260909-20-farmers/farmer_summary.csv)

The cohort was selected in deterministic order from recent active farmers before
memory outcomes were inspected. Twenty distinct session-boundary cutoffs separated
1,266 training turns from 100 later questions, five per farmer. The dreamer used
the configured local vLLM model and a separate collection,
`amul_memory_backtest_20260909`. Cutoff/provenance checks passed and the memory
snapshot remained unchanged throughout generation.

Each question was replayed with and without memory using Gemma `gemma-4-31b-it`,
the recorded full Amul system prompt/history and frozen question-time operational
tool results. Memory-on added the current context, instructions and actual memory
tool schemas/functions. The runner uses an OpenAI-compatible tool loop, not the
full HTTP/translation/voice pipeline. No operational actions were performed.

The Codex assistant directly reviewed all 100 pairs with A/B condition labels
hidden, independently of the Gemma generator. Complete reasons are in the CSV.
Arithmetic differences were checked against the recorded tables in code. All 200
final answers completed; an initial output-limit failure for one long monthly
statement was preserved and both conditions retried with the same larger limit.

Only one farmer produced episodic memories (two episodes); ten farmers had a
standing record. Automatic memory context reached 55 questions. None called a
memory search/list/read tool. Most questions were current milk-record lookups, and
the one farmer with episodes did not ask a related follow-up. This sample therefore
does not establish retrieval quality or resolve the earlier demo's list-tool failure.

The +1 example gave useful daily totals instead of leaving the farmer to add table
rows. The -2 example changed a correct total to an incorrect one. Neither difference
demonstrates historical recall. Both conditions also made other arithmetic errors,
recorded as shared failures rather than rewarded for having different numbers.
Deterministic calculation in record tools is a separate, concrete follow-up.

Twenty-one pairs have a fixture limitation: twenty reused the same question's
recorded result despite different generated arguments, and one lacked a recorded
milk-tool result. These remain flagged in the CSV. This is one run per condition and
one independent model review per pair, not a production trial or domain-expert audit.

Before the run, checked same-trace merges were repaired to preserve distinct
fragments and combine provenance while validating source ownership/current state.
Frozen training input now rejects post-cutoff turns, and Langfuse reads request only
needed core/input/output fields. The earlier merge-input clipping was removed.
Mechanical validation: 83 offline tests passed, and the 37 service-dependent cases
were separately passed with disposable Qdrant/fixture API infrastructure. Final CSV
checks passed for counts, cutoffs, complete answers, scores/reasons and snapshot hash.

Keep this ordinary-traffic baseline. The next evaluation should separately select
real cross-session follow-ups before generation, then test retrieval and source
fidelity explicitly. See [the updated backtesting plan](backtesting-plan.md).


## Follow-up source audit: why so few episodes

A closer audit after the initial report found that the low count cannot be explained
only by routine traffic. Across the run, the dreamer called `nothing_to_remember`
153 times. It proposed three episodic writes across two farmers. Two were stored;
the proposal for `farmer_10` (cow mastitis) was refused as "sensitive content". The
log does not contain a specific reason beyond that generic fallback. The judge's
prompt blocks "Family conflict, illness, or personal distress" without explicitly
distinguishing human illness from livestock health. This is a plausible cause of
the refusal, not a proven explanation of the model's internal decision.

The extractor also says "Most runs of turns produce NOTHING" and excludes fully
answered questions. Those instructions may over-discourage useful continuity. For
example, `farmer_19` asked why the August 18 milk entry was missing and was directed
to the society without a resolution; no episode was saved. This is a candidate
omission worth reviewing, distinct from copying routine milk values. The initial
report's explanation of low coverage was incomplete; the unchanged CSV scores do
not evaluate these extraction misses.

For the wrong-total case (`farmer_05_q04`), the only retrieved standing fact was
"language register: Gujarati". Neither condition called a tool on that turn, and
both already had the same eight milk amounts in conversation history. No remembered
payment amount supplied the incorrect total. Memory context/rules/tool availability
changed the input, but this single comparison cannot isolate which change caused
the model's arithmetic to differ.

Amul does append `MEMORY_INSTRUCTIONS` to the system prompt, currently only when
automatic memory context is nonempty. Memory tools can still be offered with empty
context, so general tool-use guidance should be reviewed for that case. No prompts,
memories or recorded answers were changed during this follow-up audit.
