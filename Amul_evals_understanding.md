# Amul Evaluations: Dimensions and Current Measurement Setup

This document summarizes how `amul_evals` currently evaluates voice quality, what dimensions are used, and where scoring comes from.

## What `amul_evals` Contains

The current folder has three evaluation artifacts:

- `run_voice_eval.py`: single-turn runner for real production-style queries
- `run_voice_e2e.py`: multi-turn end-to-end voice pipeline runner (session persistence + translation)
- `voice_eval_judgement_full.md`: LLM-as-judge analysis report with scoring dimensions and conclusions

It also stores outputs:

- `voice_eval_results.json` (single-turn run outputs)
- `voice_e2e_results.json` (multi-turn run outputs)
- `voice_conversation_test_cases.json` (test case source)

## Important Distinction

Current setup is split into two layers:

- **Execution/collection layer (Python scripts)**: runs queries, captures responses, timing, token usage, and word count
- **Judgement layer (Markdown report)**: applies quality scoring dimensions (1-5) and gives qualitative verdicts

So the scoring dimensions are currently documented and applied via the judge report, not computed in a dedicated scoring script inside this folder.

## Evaluation Dimensions Used (LLM Judge)

From `voice_eval_judgement_full.md`, each response is scored 1-5 on:

- `brevity`: voice-appropriate length
- `accuracy`: correctness and relevance of advice
- `voice_ready`: no markdown/list artifacts in spoken output
- `tone`: warm, respectful, professional assistant behavior
- `translation`: Gujarati naturalness and terminology fidelity

Notes:
- For single-turn section, the report table uses `B`, `A`, `V`, `T` (no explicit translation column in that table because responses are English there).
- For multi-turn Gujarati E2E section, the report adds translation as `Tr`.

## Score Scale

The report uses an implicit 1-5 quality scale per dimension:

- `5` = excellent
- `4` = good
- `3` = acceptable
- `2` = weak
- `1` = poor/critical problem

No formal machine-enforced schema is present in `amul_evals` for these scores; they are presented in the judgement markdown.

## What the Runners Actually Measure Programmatically

### 1) `run_voice_eval.py` (single-turn)

Per case, it records:

- `id`, `category`, `query`, `response`
- `elapsed_seconds`
- `token_usage` (`input`, `output`, when available)
- `word_count`
- `error`

This run executes the agent directly and writes outputs to `voice_eval_results.json`.

### 2) `run_voice_e2e.py` (multi-turn)

Per turn, it records:

- `query`, `response`
- `elapsed` (full turn latency)
- `ttfb` (time to first chunk)
- `word_count`
- `error`

This run executes the voice service layer directly (full pipeline minus HTTP auth) and writes outputs to `voice_e2e_results.json`.

## Current Data Coverage (as documented)

- **Single-turn set**: 31 cases
- **Multi-turn E2E set**: 8 conversations, 25 turns
- **Judged total**: 56 responses (31 + 25)

## Reported Aggregate Findings (Current)

From `voice_eval_judgement_full.md`:

- Single-turn quality is strong: concise, voice-clean, high factual quality
- Multi-turn Gujarati quality is generally good for translation and terminology
- Main recurring weakness is **verbosity** in multi-turn RAG-rich turns
- Additional issue: occasional "did not understand" on clear follow-up utterances

## Current Pass/Fail Logic

There is no explicit code-level `overall_pass` field in the runner outputs.

Instead, the final quality verdict is stated in the judge report narrative:

- Single-turn: "EXCELLENT"
- Multi-turn: "GOOD with one critical gap" (verbosity under RAG-rich context)

## Practical Interpretation

Today, `amul_evals` behaves as:

1. deterministic data collection via scripts
2. human/LLM-judge quality scoring documented in markdown

If needed, this can be upgraded later into a structured scorer (JSON schema with per-dimension scores and automatic pass/fail gates), similar to the stricter pattern used in `oan-evaluation`.

