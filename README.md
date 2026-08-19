# oan_horizon

Living documentation for OpenAgriNet (OAN): what each bot currently does, how it's
architected, and what's being planned or discussed next. Two kinds of file live here:

- **`*_understanding.md`** (repo root) — current-state, code-grounded architecture docs.
  Treat these as a snapshot, not a guarantee — re-verify against the actual repo before
  relying on a specific detail for something high-stakes.
- **`future_work/<topic>/`** — planned or in-discussion work. Each has its own README;
  some are settled specs, some are open discussions with no decisions made yet — check
  each one's own status note rather than assuming either.

## Current state of the bots

| Bot | Backend repo(s) | Understanding doc |
|---|---|---|
| **BharatVistaar** ("OAN," the flagship advisory bot) | [`bharat-oan-api`](https://github.com/OpenAgriNet/bharat-oan-api) | [`Bh_understanding.md`](Bh_understanding.md) |
| **mahaVistaar** (Maharashtra-specific variant) | [`mh-oan-api`](https://github.com/OpenAgriNet/mh-oan-api) | [`Mh_understanding.md`](Mh_understanding.md) |
| **Amul** (voice + text, dairy-sector variant) | `voice-oan-api` + `amul-oan-api` | [`Amul_understanding.md`](Amul_understanding.md) |

Evaluation (model selection, language readiness, and current pipelines across all
three bots) is documented once, centrally: [`Evaluation_understanding.md`](Evaluation_understanding.md).

Brief current-state notes, expanded in each doc:

- **BharatVistaar** routes each request through named model aliases
  (`config/models.yaml` + `agents/model_registry.py`) with weighted/sticky per-use-case
  routing, capacity-based deflection, and a single-hop failover — more complex than the
  other two bots' static primary+fallback pattern. Has by far the largest tool surface
  of the three bots (31 tools — scheme status/grievance flows for PM-KISAN, PMFBY, SHC,
  SMAM, GFR, SATHI, all Beckn/BAP-network-backed), and a pest/disease image-analysis
  tool (NPSS) the other bots don't have. Voice is client-orchestrated (separate
  transcribe/TTS calls around a text-only chat loop), unlike mahaVistaar's more
  integrated voice pipeline. A real config-design gap remains open — moderation has no
  fallback path at all today, and an in-flight fix risks regressing a property agrinet's
  routing already gets right (see `future_work/model_routing_fallback/`). A fix for
  Indic-script mixing in agrinet's responses is built and verified but not yet merged
  to `bh-dev` — see `future_work/language_mixing/`. Has **no long-term/cross-session
  memory** — every conversation starts from zero.
- **mahaVistaar** is the only bot with real cross-session memory today: mem0 + Qdrant
  for episodic recall, plus a separate structured farmer-profile store, both wired in
  as agent tools and gated to logged-in farmers only. See `Mh_understanding.md`'s
  "LONG-TERM MEMORY" section, and `future_work/memory/` for open questions and
  speculative future direction.
- **Amul** is voice-first (RAYA telephony IVR) with a separate web/app text path;
  session ownership and history persist in Redis with its own claim/refresh/release
  locking to prevent concurrent requests on one session.

## Evaluation

[`Evaluation_understanding.md`](Evaluation_understanding.md) covers the full picture:
how a model gets selected (inference fit → benchmarks → LLM-as-judge pipeline), how a
new language is declared ready (the PT-team/State-team workflow), the current combined
metrics rubric, and each system's actual implementation today —
`oan-evaluation`'s text pipeline (4 dimensions / 18 sub-dimensions, code-enforced
pass/fail gates) and `amul_evals`' looser voice setup (execution scripts + a
judge-report scoring layer, not yet a code-enforced schema).

- `future_work/common_evals/` — the in-progress unification of both into one shared,
  YAML-configured rubric usable across projects (Amul, mahaVistaar, and beyond).
- `future_work/human_evals_alignment/` — the actual human eval results (blind,
  two-round + QC process) and the planned DSPy-based calibration of the automated
  judge against them.

## Other important repos

Not documented in depth here yet — pointers only:

| Repo | What it is |
|---|---|
| [`docs-pipeline`](https://github.com/OpenAgriNet/docs-pipeline) | Document ingestion: normalizes source files, supports human review/correction, chunks and publishes into the vector index the bots query against. No understanding doc here yet — worth adding. |
| `bharat-provider-backend` (in `network_network/`) | BharatVistaar's Beckn Provider Platform (BPP) — schemes/mandi/weather/services data source, NestJS. |
| `mh-vistaar-provider-backend` | mahaVistaar's BPP — separate org (`MH-Vistaar`), source not accessible from here. |
| `langfuse_mcp` (remote: `LLM_eval`) | LLM-as-judge scoring pipeline over Langfuse traces, plus a natural-language query UI over the same telemetry. |

## What's planned or being discussed next

| Topic | Status |
|---|---|
| [`future_work/memory/`](future_work/memory/) | **Exploratory, no decisions made** — a review of memory concepts/industry patterns/mahaVistaar's current state, plus a team whiteboard session folded in. |
| [`future_work/model_routing_fallback/`](future_work/model_routing_fallback/) | **Risk flagged on an in-flight fix** — `bh-dev` already gets alias-level fallback right for agrinet; the in-flight rework fixing moderation's real gap would regress that property back to per-use-case unless corrected. |
| [`future_work/language_mixing/`](future_work/language_mixing/) | **Implemented and verified, not yet merged** — constrains agrinet's output to the farmer's script via an allowlist derived from Unicode's own Script property, fixing a real UX/trust problem an earlier hand-picked-allowlist attempt missed. |
| [`future_work/language_expansion/`](future_work/language_expansion/) | Spec — readiness evaluation for adding a new language + LLM, human-scored, 800-sample fixed dataset design. Includes a [diversity sampler](future_work/language_expansion/diversity_sampler/) sub-spec. |
| [`future_work/scheme_input/`](future_work/scheme_input/) | Spec — PDF → structured, searchable scheme records pipeline. |
| [`future_work/synth_data_personas/`](future_work/synth_data_personas/) | Spec — synthetic farmer persona generation, building on `synth-data-bharat-oan-api`'s existing profile sampling. |
| [`future_work/common_evals/`](future_work/common_evals/) | Spec — unifying Amul + OAN evaluation into one YAML-configured, cross-project rubric. |
| [`future_work/human_evals_alignment/`](future_work/human_evals_alignment/) | Human eval results in hand (blind, two rounds + QC) — planned next step is DSPy-based automated calibration of the LLM-judge pipeline against them. |
| [`future_work/scheme_sync/`](future_work/scheme_sync/) | Proposed — replace "paste the full scheme list into every prompt" with a queryable, network-wide tool-search service, generalizing beyond schemes to every tool category. |

## A note on `oan-brain`

There's a separate, local-only knowledge base at `/mnt/raid/gautam/oan-brain/` — an
AI agent's own working memory across sessions (repo gotchas, environment quirks, task
history), never pushed anywhere. This repo (`oan_horizon`) is the human-facing,
version-controlled counterpart: durable, reviewed documentation meant to be read and
maintained by the team, not an agent's scratch memory.
