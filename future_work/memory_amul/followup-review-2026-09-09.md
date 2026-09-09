# Retention tuning and real cross-session follow-ups — 9 September 2026

The revised rule recovers useful situations that the earlier gate missed. The
answer evaluation remains mixed: **2 improved, 12 equivalent, 1 worse** across
15 recorded questions from five farmers. This is evidence for better retention
of some concerns, not evidence that memory reliably improves Amul replies.

## What changed

The agent and pipeline now share a neutral usefulness rule. They evaluate each
statement in a batch, including personal interests and unresolved concerns among
routine lookups. There is no target number of memories and no instruction that
most batches should produce nothing. An answer does not establish resolution;
interest does not establish a commitment or completed action.

The sensitive-content judge explicitly distinguishes human illness from ordinary
livestock symptoms, care and treatment. Ordinary missing-record concerns are not
automatically financial distress. The honesty check still rejects unsupported
diagnoses and unconfirmed bookings. Failed checks still leave proposals unwritten;
these changes do not introduce a fail-open path or a durable retry scheduler.
Skip explanations are now retained in tool notes and printed without shortening.

No bot code or deployment changed in this tuning study. In
`amul-oan-api/agents/agrinet.py`, the existing condition
`if ctx.deps.memory_context` appends `MEMORY_INSTRUCTIONS`. The base Amul prompt
therefore receives that extra instruction block only when memory context is
nonempty. Global disable, a farmer's explicit disable flag, or no standing record
and no recalled episodes produces no injected memory. The memory tool schemas
have their own enablement checks; an enabled farmer can still search when the
automatic context is empty. “No extra instruction block” does not mean “no tools.”

## Review of skipped conversations

We screened all 1,266 training questions from the original 20 farmers and read
candidate answers and surrounding turns. Routine tabular answers were not all
individually audited. The audit CSV records 12 findings across six farmers,
including some deliberate skips and some findings spanning multiple turns.

Misses included individual-cow production tracking, an unexplained deduction,
an August 18 missing milk entry, earlier buffalo fat/SNF concerns, and a cow-health
proposal rejected by the old privacy wording. A payment drop explained by a
partial-month comparison was correctly left out. These are examples for the
generic usefulness rule, not new mandatory categories.

## Rebuild and paired replay

The final study uses 628 historical turns from four original-cohort farmers and
the existing demo farmer. Each has a cutoff before the selected later sessions.
Training and held-out session IDs do not overlap, and stored episode sources
belong to the allowed training traces. The service and collection are isolated;
the original 20-farmer baseline and initial tuning attempt remain unchanged.

| Farmer alias | Training turns | Current episodes | Detail chunks |
| --- | ---: | ---: | ---: |
| farmer_10 | 164 | 3 | 4 |
| farmer_12 | 77 | 1 | 1 |
| farmer_13 | 139 | 2 | 3 |
| farmer_19 | 39 | 3 | 3 |
| demo_21 | 209 | 18 | 20 |
| Total | 628 | 27 | 31 |

Three farmers also have standing records. The initial tuning attempt on the same
cutoffs produced 18 episodes; the final attempt produced 27. This is one run per
revision, not a controlled estimate of the prompt's effect. The original
20-farmer baseline used different cutoffs and questions, so its two episodes
cannot be compared directly with these 27 as an accuracy metric.

We selected 16 real later-session questions before answer generation. One delivery
question, `demo_21_q06`, lacked a complete recorded Amul agent request and was
excluded with the reason saved; no replacement was chosen. The remaining 15
questions produced 30 complete answers using `gemma-4-31b-it`, temperature 0 and
an output limit of 1,800 tokens per call. All received memory context in the on
condition. One answer pair was identical; no generation errors occurred.

Codex directly reviewed blind A/B answers, then checked material differences
against supplied history, memory and tool results. Scores are -2 to +2, with
reasons and confidence in every row. This is one independent reviewer, not a
panel, and does not certify veterinary advice or current scheme eligibility.

| Outcome | Cases |
| --- | ---: |
| Modest improvement (+1) | 2 |
| Equivalent (0) | 12 |
| Material regression (-2) | 1 |
| Mean score | 0 |

The improvements are `demo_21_q03` and `demo_21_q04`: remembered calf-registration
and missing-benefit reports give continuity and make escalation more specific.
The latter still overstates repeated discussions as multiple attempts; that
wording needs caution.

The regression is `demo_21_q05`: the memory-on answer confidently identifies a
15/50/350 kg supply package as a particular government scheme without supporting
evidence in the supplied context. The memory-off answer keeps the package's
identity uncertain and recommends checking. Remembering the farmer's grievance
does not establish current scheme rules. The observed difference is not proof
of a single causal mechanism inside the model.

No answer called search/list/read memory tools. These results exercise automatic
Level 2 context, not agentic Level 3 retrieval. Many follow-ups already have useful
same-session history in both arms, which reduces memory's incremental benefit.
The live-record controls did not substitute old memory values for tool records.

Median generation time was 3.687 seconds without memory and 4.129 with memory.
These are local replay measurements, not full user-perceived service latency.

## Does reducing batch size help Gemma?

We ran the actual extractor and judges in dry-run mode on three missed-memory
examples and one routine control, using caps of 10, 5 and 3 turns. No dry-run
proposals were stored in the replay collection.

| Maximum turns | Useful candidates recovered | Routine control skipped | Batches for all 628 training turns |
| --- | ---: | ---: | ---: |
| 10 | 2 / 3 | Yes | 81 |
| 5 | 2 / 3 | Yes | 153 |
| 3 | 2 / 3 | Yes | 243 |

All sizes retained the per-cow tracking interest and missing milk entry. All
missed the unexplained deduction. The 10-turn useful-case inputs contained only
about 2,100–4,700 source characters, while the correctly skipped routine control
contained about 19,100. These counts exclude the system prompt, tool schemas and
other request overhead. At 5 and 3 turns, the missing-entry proposal first hit a
privacy refusal and was accepted after rewording, so smaller was not consistently
faster or more reliable.

An earlier run of the same final 10-turn gate produced different keep/skip
decisions. The test is small and batch boundaries change neighbouring context;
it is not a pure context-length experiment or a stable recall benchmark.
It does not support long context alone as the explanation for the missed cases.

**Keep `DREAMER_CHUNK_TURNS=10` for now.** Before reducing it, run repeated trials
on a fixed annotated set. If long inputs prove problematic, test a source-text
budget alongside the turn cap and preserve nearby conversational context. A turn
count alone cannot bound the size of long tables or answers. This additional
budget has not been implemented or validated by this study.

## Remaining failures and limits

- Retention is still inconsistent. Some useful concerns are missed, while some
  general inquiries are saved with little demonstrated future value.
- One saved episode copies a reported daily 40-litre delivery figure, contrary
  to the rule against retaining live production values as lasting memory.
  Several generic care, membership and scheme inquiries are also questionable.
  The frozen inventory preserves these failures for inspection.
- Animal-health wording now passes focused checks, but generated diagnosis
  wording still needs attribution. A farmer-reported symptom and an earlier
  assistant interpretation must not silently become a verified diagnosis.
- Five reply cases use a frozen tool result despite changed tool arguments.
  In particular, `farmer_19_q03` broadens the date lookup but receives the same
  captured empty result. Its broader no-records claim cannot be validated here.
- The recorded translation for `farmer_13_q01` appears to turn SNF into an animal
  being in heat; both arms inherit this. The replay intentionally preserves the
  original request instead of silently repairing one condition.
- Operational tools use captured results; actual read-only memory tools are
  available. There are no live bookings, orders or messages. This does not run
  the HTTP translation pipeline. No new missing-tool-result fallback occurred.

Eight focused live-model privacy/honesty checks passed. Offline unittest discovery
passed 120 tests with 37 service-dependent skips (83 executed). These establish
specific policy examples and mechanical contracts, not general extraction quality.
The final artifact audit verifies source cutoffs, complete scored answer pairs,
unchanged generation source hashes and an unchanged frozen memory snapshot.

For a demo, show the useful grievance-continuity example alongside the recorded
failure. This study does not support calling the whole memory flow reliable.
The next evaluation should keep retention quality, completeness of tool retrieval
and correctness of replies as separate measures, with explicit false-recall and
unsupported-claim failures rather than only an average score.

## Inspect the artifacts

Private artifacts are outside git in
`/amulpfsdata/gautam/amul-memory-backtest/20260909-followups-v2/`:

- [Scored with/without-memory answers](../../../amul-memory-backtest/20260909-followups-v2/memory_comparison.csv)
- [Skipped-conversation audit](../../../amul-memory-backtest/20260909-followups-v2/skipped_conversation_audit.csv)
- [Current memory inventory](../../../amul-memory-backtest/20260909-followups-v2/memory_inventory.csv)
- [Batch-size comparison](../../../amul-memory-backtest/20260909-followups-v2/batch_size_comparison.csv)
- `selection.json`, `policy-checks.json`, `batch-size-checks.json`, `summary.json`,
  `artifact-audit.json`, `replay-manifest.json` and `memory-snapshot.json` preserve
  selection, raw model outcomes, counts and provenance.
