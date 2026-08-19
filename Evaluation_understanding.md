# Evaluation (across OAN)

How OAN picks and gates the LLM at the core of its agents, how a new language gets
declared ready, and how quality is measured once a model is live — for both text
(BharatVistaar/mahaVistaar) and voice (Amul).

Repo: [`oan-evaluation`](https://github.com/OpenAgriNet/oan-evaluation), aggregate
branch `common_evals_dev`.

## How a model gets selected

Model selection narrows through three stages. First, **inference fit**: does the
model's size and serving profile work for us — can it run on our hardware at the
concurrency and latency we need? Models that clear that bar are then **benchmarked**
on open-source metrics for reasoning and tool-calling, alongside Indic benchmarks that
test the same capabilities in Indic languages, to screen out models weak in Indic. The
shortlisted models are finally run through the **custom OAN evaluation pipeline**,
where a large model acts as an LLM-as-judge across multiple metrics to decide which one
best fits our needs across languages. That judge is itself calibrated against human
evaluations on the same metrics, so the automated pipeline stays tracked to human
judgement (see `future_work/human_evals_alignment/`).

### 1. Benchmarks used for selection

**Tool calling and intelligence** — mostly English, published by most big model
releases:

- MMLU-Pro — knowledge/reasoning
- GPQA — hard reasoning
- IFEval — instruction following
- BFCL, τ²-bench — agentic/tool-calling, most relevant to OAN

**Indic** — language-specific tasks (translation, QA, summarization, instruction
following) used to exclude models that perform poorly in required Indic languages:

- FloresIN — translation accuracy
- XorQA-IN — cross-lingual question answering
- CrossSumIN — summarization ability for Indic docs
- IndicIFEval — instruction-following capability in Indic

Example cutoffs evaluated for Gemma 4 31B vs. Qwen 3.6 27B:

| Benchmark | Proposed cutoff | Gemma 4 31B | Qwen 3.6 27B |
|---|---|---|---|
| MMLU-Pro | ≥ 82 | 85.2 | 86.2 |
| GPQA Diamond | ≥ 80 | 84.3 | 87.8 |
| τ²-bench (agentic) | ≥ 72 | 76.9 | 73.4 |
| BFCL (function calling) | ≥ 60 | 63.4 | 63.3 |
| IFEval | ≥ 80 (provisional) | 93.5 | 94.3 |
| Latency (p50) | ~5 sec | 5 | 5 |
| Load (concurrent req, 1 node) | 20 | 20 | 20 |

Indic benchmark cutoffs (FloresIN/chrF, XorQA-IN/F1, CrossSumIN/ROUGE-L, IndicIFEval/
accuracy) are tracked the same way; specific cutoff values are still being defined.

### 2. Custom eval benchmark (LLM-as-judge on simulated queries)

A benchmark question set across languages, scored by a judge model (a large model,
never the same model being evaluated), calibrated to human evals. Metrics scored by
the judge in the current pipeline:

- **Factual grounding** — no_fabrication, citation_accuracy, citation_comprehensiveness
- **Response usefulness** — accuracy_completeness, actionability, context_fit,
  conversation_closure, source_data_comprehensiveness, safety_compliance
- **Linguistic quality** — grammar_fluency, terminology, language_purity,
  translation_accuracy
- **Voice channel** — brevity, voice_ready_text, comprehensiveness, tone, WER/MOS
  (ASR/TTS layer, human-scored)
- **Process fidelity / agentic** — agristack_workflow, term_identification,
  tool_sequencing, search_quality, output_hygiene
- **Runtime/performance** (deterministic) — elapsed_seconds, ttfb, word_count,
  token_usage.input, token_usage.output, error

### 3. Keeping the eval benchmark fresh

Logs are used as seed data, then new questions are simulated using the new docs/APIs/
tool calls that keep getting added to the system: generate candidate questions →
human-validate a sample → add to a versioned set. Repeated periodically. Guardrail:
the generator model is never the judge model, so questions aren't graded by the model
that wrote them.

### 4. Self-hosting vs. calling APIs

Pay-per-call scales linearly and punishes more calls; owning GPUs turns cost into
fixed infrastructure instead.

## Language selection (readiness)

Defines the division of responsibility between the program team (PT) and the
respective State teams for evaluating and onboarding a new language.

### Readiness definition

A language is considered ready only when all of the following hold:

**Text LLM layer:**
- Translation quality is strong.
- Direct native-language answering is strong.
- Tool calling and search terms based on the new language work with good accuracy.
- A supporting glossary of key agri words is integrated and tested.
- Moderation/safety behavior is reliable.
- Persona consistency is maintained in the new language.

**Voice layer:**
- ASR quality is good across noisy background, accents, gender/age, etc.
- The LLM produces TTS-ready text output — compact, no extra symbols, necessary
  preprocessing for symbols and numbers is present.
- TTS voice is engaging and natural.

### Evaluation workflow

| Step | Owner | Duration |
|---|---|---|
| Define benchmark, metrics, and cutoffs | PT team | 1 day |
| Provide/verify Agri Term Glossary | State team | 2 days |
| Run automated evaluation, share preliminary results | PT team | 1 day |
| Define H-Eval guidelines, train evaluators if needed | PT team | 2 days |
| Conduct comprehensive human evaluation (H-Eval) on the defined rubric | State team | 10 days |
| Provide qualitative language-based feedback on weaknesses | State team | — |
| Review H-Eval data + feedback, compare against cutoffs, final readiness decision | PT team | 3 days |
| Go-live, or define a focused iteration/training plan if not ready | Both | — |

See `future_work/language_expansion/` for the fixed-dataset (800-sample) evaluation
spec this workflow feeds into, and `future_work/human_evals_alignment/` for how human
eval results get used to calibrate the automated pipeline.

### Further training & fine-tuning SOP

When a language doesn't clear cutoffs, the iteration loop is:

1. State team provides specific feedback on translation, instruction-following, and
   moderation issues, ideally following the evaluation framework (10 days).
2. PT team calibrates the eval setup to match state feedback (2 days).
3. PT team creates sample synthetic data from the provided datasets plus team feedback,
   generated through multiple LLMs for comparison (3 days).
4. State team reviews a small sample of synthetic data, gives feedback on which LLM
   generates the best outputs (3 days).
5. PT team creates the final fine-tuning dataset (SFT format): 40% feedback data, 60%
   general categories including moderation (2 days).
6. PT team fine-tunes using LoRA and evaluates checkpoints for the best outputs (10 days).
7. PT team integrates the new checkpoint into the dev setup and continues the
   evaluation cycle (2 days).

At least 2 iterations are expected; state-action time in each subsequent iteration
should reduce by roughly 50%.

## Eval framework metrics (current combined rubric)

The metrics below are the shared rubric once an LLM has been decided for a language
(LLM selection itself is based on IndicIFEval, IndicMMLU, IndicGenBench). The final
readiness decision combines these as required.

| Dimension | Metric | Human eval required |
|---|---|---|
| Factual Grounding | citation_comprehensiveness (1-4) | Yes — domain knowledge |
| Factual Grounding | no_fabrication (0/1) | Yes — language expert |
| Factual Grounding | citation_accuracy (1-4) | Yes — language expert |
| Response Usefulness | completeness (1-4) | Yes — language expert |
| Response Usefulness | actionability (1-4) | Yes — language expert |
| Response Usefulness | safety_compliance (0/1) | Yes — language expert |
| Response Usefulness | context_fit (0/1) | Yes — language expert |
| Response Usefulness | conversation_closure (0/1) | Yes — language expert |
| Linguistic Quality | grammar (1-4) | Yes — language expert |
| Linguistic Quality | terminology (1-4) | Yes — language expert |
| Linguistic Quality | language_purity (1-4) | Yes — language expert |
| Linguistic Quality | fluency (0-1) | Yes — language expert |
| Linguistic Quality | translation (1-4) | Yes — language expert |
| Voice Channel | brevity | No (word length) |
| Voice Channel | voice_ready | No |
| Voice Channel | comprehensiveness (1-4) | Yes — language expert |
| Voice Channel | tone (1-4) | Yes — language expert |
| Voice Channel | input WER/CER | Yes — language expert |
| Voice Channel | output WER & MOS (tone, pronunciation) | Yes — language expert |
| Voice Channel | MOS (naturalness) | Yes — language expert (1-4) |
| Runtime/Performance | elapsed_seconds, ttfb, word_count, token_usage.input/output, error | No |
| Process Fidelity (Agentic) | agristack_workflow | No |
| Process Fidelity (Agentic) | term_identification | Yes — language expert |
| Process Fidelity (Agentic) | tool_sequencing | No |
| Process Fidelity (Agentic) | search_quality | No |
| Process Fidelity (Agentic) | output_hygiene | No |

Full per-metric scoring guidance (what a 4 vs. a 1 looks like, worked examples) lives
in the team's human-evaluator guidelines, not duplicated here.

## Current implementation: `oan-evaluation` (text pipeline)

The code-level evaluator as actually implemented (`evaluation/evaluator.py`):

- 4 dimensions, 18 sub-dimensions total: **Process Fidelity** (agristack_workflow,
  term_identification, tool_sequencing, search_quality, output_hygiene), **Factual
  Grounding** (source_alignment, no_fabrication, citation_accuracy, safety_compliance),
  **Response Usefulness** (completeness, actionability, context_fit, clarity,
  conversation_closure), **Marathi Linguistic Quality** (grammar, terminology,
  language_purity, fluency).
- Likert scale per sub-dimension: `5` excellent → `1` unacceptable/critical failure,
  or `null` when a metric doesn't apply (e.g. search-related metrics on non-search
  flows). No decimals.
- Output per evaluation: dimension-wise scores, evidence text per sub-dimension,
  per-dimension average (excluding null), `overall_average`, `critical_failures` list,
  `critical_failure_count`, `overall_pass` boolean, a short English `summary`.
- **Hard fail gate**: `overall_pass = false` if any of `factual_grounding.
  safety_compliance`, `factual_grounding.no_fabrication`, or `factual_grounding.
  source_alignment` scores `1` — otherwise `true`.
- A master prompt (`assets/prompts/evaluation_system.md`) plus a category-specific
  rubric prompt (`assets/prompts/category/`) — advisory, scheme, weather, mandi_price,
  mahadbt, agri_services (kvk/soil_lab/warehouse/chc), agri_assistant_contact — so
  scoring stays consistent at the schema level while applicability/strictness vary by
  category.
- Practical read order when comparing models: critical failures first (especially
  fabrication/safety/source mismatch), then factual grounding average, usefulness
  average, process fidelity average, Marathi quality average — mirrors real deployment
  risk, since a fluent response is still unacceptable if fabricated or unsafe.
- Evaluator model: `gpt-5` (`evaluation/evaluator.py`). Input formatting includes
  question, category, agent turns, tool calls/returns, and final answer. Runs in
  parallel with concurrency controls (`evaluation/run_eval.py`).

## Current implementation: `amul_evals` (voice pipeline)

Looser and script-based rather than a code-enforced schema:

- Three artifacts: `run_voice_eval.py` (single-turn runner), `run_voice_e2e.py`
  (multi-turn end-to-end, session persistence + translation), `voice_eval_judgement_
  full.md` (LLM-as-judge analysis report with scoring and conclusions). Outputs:
  `voice_eval_results.json`, `voice_e2e_results.json`, `voice_conversation_test_
  cases.json`.
- Split into an **execution/collection layer** (scripts: responses, timing, token
  usage, word count) and a **judgement layer** (markdown report: quality scores 1-5,
  qualitative verdicts) — scoring is documented in the report, not computed by a
  dedicated scorer in this folder.
- Judge dimensions (1-5 each): `brevity` (voice-appropriate length), `accuracy`
  (correctness/relevance), `voice_ready` (no markdown/list artifacts in spoken
  output), `tone` (warm, respectful, professional), `translation` (Gujarati
  naturalness and terminology fidelity — appears as `Tr` in multi-turn sections,
  absent from single-turn English sections).
- No explicit code-level `overall_pass` — the final verdict is a narrative judgement
  (e.g. single-turn "EXCELLENT," multi-turn "GOOD with one critical gap").
- Data coverage as last documented: 31 single-turn cases, 8 multi-turn conversations
  (25 turns), 56 judged responses total. Recurring weakness noted: verbosity in
  multi-turn RAG-rich turns, and occasional "did not understand" on clear follow-ups.
- Natural upgrade path: a structured scorer (JSON schema, per-dimension scores,
  automatic pass/fail gates) matching `oan-evaluation`'s stricter pattern — this is
  exactly what `future_work/common_evals/` is working toward.

## Text vs. voice: shared and specific metrics

- **Shared or conceptually shared**: Amul's `accuracy` maps to OAN's
  `source_alignment` + `no_fabrication` + general correctness; usefulness/readability
  signals overlap (OAN: actionability/clarity/conversation_closure; Amul: tone,
  brevity-as-concision); latency/tokens/errors are operational metrics in both.
- **Voice-chat-specific**: `voice_ready`, `brevity` as strict spoken-length control,
  `translation` as spoken-Gujarati quality and numeric verbalization, `ttfb` (stream
  start responsiveness), conversational spoken-style constraints (non-markdown,
  no list-heavy output).
- **Text-eval-specific in the current OAN setup**: `term_identification`,
  `agristack_workflow` as a formal rubric dimension, `tool_sequencing`,
  `search_quality`, `citation_accuracy` as a rubric score, `safety_compliance` as a
  formally gated score.
- **Practical read**: OAN's text metrics are deeper and more workflow/risk-grounded;
  Amul's voice metrics emphasize spoken UX, latency, and translation clarity. The unified
  rubric above (from the language-readiness framework) is the actual convergence point
  for both — see `future_work/common_evals/` for the YAML-configured implementation of it.

## Where this is headed

- [`future_work/common_evals/`](future_work/common_evals/) — unifying Amul + OAN
  evaluation into one YAML-configured, cross-project rubric.
- [`future_work/human_evals_alignment/`](future_work/human_evals_alignment/) — the
  actual human evaluation results (blind, two independent rounds + QC reconciliation)
  this pipeline should be calibrated against, and the planned DSPy-based approach for
  doing that calibration automatically.
- [`future_work/language_expansion/`](future_work/language_expansion/) — the detailed,
  fixed-dataset (800-sample) spec for the human-evaluation step in the readiness
  workflow above.
