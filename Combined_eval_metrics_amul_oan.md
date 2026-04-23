# Combined Metrics: OAN Text Evals + Amul Voice Evals

This document collates evaluation metrics used across:

- `oan-evaluation` (text/chat evaluator pipeline)
- `amul_evals` (voice evaluation setup)

It also explicitly marks which metrics are voice-chat-specific.

## 1) Snapshot by System

- `oan-evaluation`
  - Structured evaluator with rubric prompts and schema output
  - 4 dimensions, 18 sub-dimensions
  - deterministic `overall_pass` logic in code

- `amul_evals`
  - Execution scripts collect outputs, latency, and token/word stats
  - Quality dimensions are currently documented in judge report (`voice_eval_judgement_full.md`)
  - no code-enforced scoring schema/pass-fail gate in this folder

## 2) OAN Text Evaluation Metrics

## Process Fidelity
- `agristack_workflow`
- `term_identification`
- `tool_sequencing`
- `search_quality`
- `output_hygiene`

## Factual Grounding
- `source_alignment`
- `no_fabrication`
- `citation_accuracy`
- `safety_compliance`

## Response Usefulness
- `completeness`
- `actionability`
- `context_fit`
- `clarity`
- `conversation_closure`

## Marathi Linguistic Quality
- `grammar`
- `terminology`
- `language_purity`
- `fluency`

## OAN scoring/output fields
- per-subdimension score: `1..5` or `null`
- per-dimension average
- `overall_average`
- `critical_failures`
- `critical_failure_count`
- `overall_pass`
- short evaluator `summary`

## OAN hard fail gates in code
`overall_pass = false` if any score is `1` for:

- `factual_grounding.safety_compliance`
- `factual_grounding.no_fabrication`
- `factual_grounding.source_alignment`

## 3) Amul Voice Evaluation Metrics (Judge Dimensions)

From `amul_evals/voice_eval_judgement_full.md`:

- `brevity` **[Voice-specific]**
  - checks voice-appropriate response length
- `accuracy` **[Shared with text in spirit]**
  - correctness and relevance
- `voice_ready` **[Voice-specific]**
  - no markdown/list artifacts in spoken output
- `tone` **[Mostly shared, but voice-sensitive]**
  - respectful, warm, conversational assistant style
- `translation` **[Voice-specific in current setup]**
  - Gujarati naturalness, spoken terminology, number rendering

## Amul run-time measured KPIs (script-collected)

These are captured programmatically by `run_voice_eval.py` / `run_voice_e2e.py`:

- `word_count` **[Voice-specific usage]**
- `elapsed_seconds` / `elapsed` **[Shared infra KPI]**
- `ttfb` (time to first chunk) **[Voice-streaming-specific]**
- `token_usage.input` / `token_usage.output` **[Shared infra KPI]**
- `error` **[Shared infra KPI]**

## 4) Crosswalk: Shared vs Voice-Specific

## Shared or conceptually shared across both
- `accuracy` (Amul) ~ `source_alignment` + `no_fabrication` + correctness aspects of OAN
- usefulness/readability signals:
  - OAN: `actionability`, `clarity`, `conversation_closure`
  - Amul: `tone` (partly), practical concision under `brevity`
- infra/perf:
  - latency/tokens/errors are operational in both ecosystems (though surfaced differently)

## Explicitly voice-chat-specific
- `voice_ready`
- `brevity` as strict spoken-length control
- `translation` as spoken Gujarati quality and numeric verbalization
- `ttfb` (stream start responsiveness)
- conversational spoken style constraints (non-markdown, no list-heavy output)

## Text-eval-specific in current OAN setup
- `term_identification`
- `agristack_workflow` (as formal rubric dimension)
- `tool_sequencing`
- `search_quality`
- `citation_accuracy` as a rubric score
- `safety_compliance` as formal gated score

## 5) Practical Read

- For **text assistant quality**, OAN metrics are deeper and strongly workflow/risk grounded.
- For **voice assistant quality**, Amul emphasizes spoken UX, latency, and translation clarity.
- If you want one unified evaluator, a good next step is mapping Amul metrics into OAN-style schema output (dimension scores + hard fail gates + JSON result per case).

