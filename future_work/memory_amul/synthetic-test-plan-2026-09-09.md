# Controlled synthetic memory diagnostic

Use the existing test farmer specified by Gautam (number ending 57046), with
invented source conversations in a separate Qdrant collection. Do not merge
these invented events with real history or upload them as real Langfuse traces.
This tests the memory machinery for that identity, not the farmer's actual life.

The fixture is frozen before memory generation: 34 turns in seven conversations,
then 20 independent fresh-chat questions after the cutoff. Ten questions require
specific earlier facts. Ten need no supported personal history: general questions,
current-record fixtures and unsupported assumptions the bot should reject.
The expected facts come from the source, not from whatever the extractor retained.

Positive cases cover a chosen notebook layout, original-versus-copy document
locations, a corrected calf birth date, an unconfirmed vet booking, a resolved
missing entry, lack of electricity, a failed silage attempt and next plan,
an outstanding supplier photograph, a complete list of three named unresolved
matters, and collected-versus-submitted documents. The unrelated controls include
arithmetic, definitions, current milk records and the unverified feed-package
scheme question. Some negative cases share topic words with memory deliberately.

## Measurement

For every positive case, inspect each expected fact at three stages:

1. **Stored:** present and correct in a current episode/standing record; check
   correction and resolution against the newest source, not a superseded entry.
2. **Retrieved:** supplied automatically or returned by a memory tool. A stored
   fact absent from all supplied evidence is a retrieval miss.
3. **Used:** answer includes the requested fact without inventing confirmation,
   mixing episodes, or substituting stale information for current tool results.

Report positive fact recall and fully correct answers separately. For the ten
controls, report unsupported personal claims, irrelevant history and incorrect
replacement of current facts. A harmless standing style preference is not unwanted
memory intrusion. Keep severe failures visible rather than averaging them away.

Compare memory off/on using the same question, base prompt and external fixtures.
The memory-off arm should admit missing personal history; that is an appropriate
baseline rather than a hallucination failure. Direct assistant review supplies
scores and reasons; substring presence alone is not correctness. A manual supply
of verified facts can diagnose failed cases later, but must be reported as a
separate assisted condition and must not overwrite the original pair.

## Execution and limitations

The test uses the current Amul English translation-pipeline prompt template,
Gemma, automatic memory context and actual search/list/read tool functions.
Each question has no earlier in-session conversation, avoiding the confound from
the real-follow-up study. The existing identity is used for farmer scoping; no
real registered profile or historical conversation is imported into these fixtures.
Operational tools return synthetic fixed results and never execute actions.

English source turns isolate memory behavior from translation. Multilingual and
full HTTP/translation validation remain separate. This is a deliberately balanced
diagnostic, not an estimate of how often real Amul traffic benefits from memory.
One farmer and a single run do not measure population coverage or stability.

Private files are in `amul-memory-backtest/20260909-synthetic-57046/`:
`source_conversations.csv`, `test_questions.csv`, `expected.json`, `prepare.py`,
frozen `cases/`, and `fixture-manifest.json`. Expected answers and source hashes
must remain fixed when scoring the generated results.

## Current status

The first synthetic run and a separate direct-Qdrant-reader replay are complete and scored. Both used 34 invented training turns, eight current episodes plus one standing record, and 20 paired held-out questions. The original run had 9 better, 9 similar and 2 worse answers with memory; the direct-reader run had 9 better, 10 similar and 1 worse. These are relative answer judgments, not full-pass or causal memory-error counts. Both runs are preserved under `amul-memory-backtest/20260909-synthetic-57046*`, with answer CSVs and separate retrieval diagnostics.

Authenticated dev Qdrant access works over HTTPS. The bot now reads Qdrant directly and uses Marqo for embeddings; the memory API remains private to the independent background writer. A live read-only audit verified pagination, detail search, history and ownership isolation with zero memory API requests. No production collection was moved or reset, and no fake conversation was added to real history or Langfuse.

The unverified scheme name was absent from stored and retrieved memory. Its appearance in one answer is classified as an answer-grounding failure; causation by memory is not established. The clear memory-specific gaps are detail left unread, contents/headline overstatements, one lost identifying mark and failure to invoke the listing tool. See each run's README and CSV for the evidence and fixture limitations.
