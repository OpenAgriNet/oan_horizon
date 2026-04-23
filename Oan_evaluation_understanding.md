# OAN Evaluation: Dimensions and Scoring

This document explains what `oan-evaluation` measures, how it scores responses, and how pass/fail is derived.

## Purpose

`oan-evaluation` is an LLM-based evaluation pipeline for MahaVistaar responses.  
It evaluates model outputs against tool traces and expected workflow behavior, with emphasis on:

- process correctness
- factual grounding
- farmer usefulness
- Marathi language quality

## Evaluation Dimensions

The evaluator scores each sample across 4 dimensions and 18 sub-dimensions total.

### 1) Process Fidelity

Checks whether the agent followed the expected workflow and tool usage patterns.

- `agristack_workflow`: Appropriate Agristack usage (when needed, when optional, and fallback behavior)
- `term_identification`: Proper term mapping/lookup (especially for advisory and scheme interpretation)
- `tool_sequencing`: Correct order of tools for the use case
- `search_quality`: Query quality and relevance of retrieval behavior
- `output_hygiene`: No tool-name leakage, no raw/internal artifacts in final farmer response

### 2) Factual Grounding

Checks that claims are supported by tool output and safe/non-fabricated.

- `source_alignment`: Facts in response match tool outputs
- `no_fabrication`: No invented values/schemes/promises when tools are empty or uncertain
- `citation_accuracy`: Correct and farmer-facing source attribution
- `safety_compliance`: Safety-critical correctness (dosage/legal/safe recommendations)

### 3) Response Usefulness

Checks whether the response is practically useful for the farmer.

- `completeness`: Covers all relevant parts of the query
- `actionability`: Includes concrete next steps, specifics, and practical guidance
- `context_fit`: Uses available profile/location/context correctly
- `clarity`: Understandable structure and formatting
- `conversation_closure`: Good follow-up question/next-step closure

### 4) Marathi Linguistic Quality

Checks language quality for Marathi-first UX.

- `grammar`: Correct sentence construction
- `terminology`: Appropriate agricultural/government terminology
- `language_purity`: Avoids unnecessary mixed-language phrasing
- `fluency`: Natural, conversational Marathi

## Score Scale

Each sub-dimension is rated on Likert scale:

- `5` = Excellent
- `4` = Good
- `3` = Acceptable
- `2` = Poor
- `1` = Unacceptable (critical failure level)
- `null` = Not applicable for that query type

Notes:
- No decimals per sub-score.
- `null` is explicitly allowed when a metric does not apply (for example, search-related metrics on non-search flows).

## Output Structure

Each evaluation result includes:

- dimension-wise scores
- evidence text per sub-dimension
- per-dimension average (excluding `null`)
- `overall_average` across all non-null sub-dimensions
- `critical_failures` list
- `critical_failure_count`
- `overall_pass` boolean
- short English `summary`

## Pass/Fail Logic

In current implementation (`evaluation/evaluator.py`), `overall_pass` is `false` if any of the following is scored `1`:

- `factual_grounding.safety_compliance`
- `factual_grounding.no_fabrication`
- `factual_grounding.source_alignment`

Otherwise, `overall_pass` is `true`.

## Category-Specific Evaluation

The evaluator uses:

- a master prompt: `assets/prompts/evaluation_system.md`
- plus a category-specific rubric prompt under `assets/prompts/category/`

Supported category prompts include:

- `advisory`
- `scheme`
- `weather`
- `mandi_price`
- `mahadbt`
- `agri_services` (used for `kvk`, `soil_lab`, `warehouse`, `chc`)
- `agri_assistant_contact`

This means scoring behavior is consistent at schema level, but applicability and strictness vary by category.

## Practical Interpretation

When comparing models, treat results in this order:

1. Critical failures (especially fabrication/safety/source mismatch)
2. Factual grounding average
3. Usefulness average
4. Process fidelity average
5. Marathi quality average

This mirrors real deployment risk: a fluent response is still unacceptable if it is fabricated or unsafe.

## Implementation Notes

- Evaluation agent uses `gpt-5` in `evaluation/evaluator.py`.
- Input formatting includes question, category, agent turns, tool calls/returns, and final answer.
- Evaluations are run in parallel in `evaluation/run_eval.py` with concurrency controls.

