# Amul memory backtest plan

Goal: before shipping any memory design (Option A/B/hybrid from
`memory-design-decisions.md`), validate it against Amul's real historical
conversations — check personalization actually improves, and check it **does not
regress existing answer quality or become an annoying/creepy user experience**. This
is a counterfactual replay, not a live A/B — see "Limitations" below.

## Data

- Source: Amul's Langfuse project(s) — `voice-production`, `chat-production`,
  `development` environments (per `Amul_understanding.md`'s Observability section,
  cross-checked as still accurate against `app/observability.py` in `amul-oan-api`).
  Same access pattern used for the mh-oan-api memory review
  (`oan-brain/tasks/20260818-mahavistaar-memory-review.md`): hit the self-hosted
  Langfuse public API directly with that project's own keys. Confirm where Amul's
  Langfuse keys live (likely `oan_creds/.api_keys`, same pattern as mh) before
  starting — not yet confirmed for this project specifically.
- Unit of analysis: a **farmer** (by normalized mobile — same identity key
  `agents/tools/farmer_animal_backends.py::normalize_phone` already uses), not a
  session — need farmers with **multiple calls/sessions across time** to have anything
  for memory to draw on. Given `voice-oan-api`'s history TTL is only 2 hours
  (`memory-design-decisions.md`'s "Current state"), a farmer's sessions today are
  already fragmented far more aggressively than mh's case — the backtest population
  needs sessions spread across **days**, not just minutes, to be a meaningful test of
  identity-level memory specifically (short-gap repeat sessions mostly test the
  existing 2h Redis TTL, not the new memory layer).
- If scoping the doctor persona too (open question in the design doc), pull that
  cohort separately — different identity space (vets, not farmers) and a different
  memory shape (per-animal case history), shouldn't be mixed into the same sample.
- Pull, per farmer: ordered list of (session_id, turn, timestamp, user query — English
  pretranslation if voice, agent response, tool calls made, which persona). Langfuse
  gotchas from `oan-brain/knowledge/langfuse-api-gotchas.md` apply (broken filters,
  timestamp quirks) — budget time for that.
- **PII flag, not yet resolved**: this is real farmer phone numbers and conversation
  content (herd/animal-health data, for the doctor persona also clinical content).
  Needs a decision on pseudonymization/handling before logs leave Langfuse into any
  local harness — don't assume this is fine by default, ask.

## Method — shadow replay

Reuse `oan-evaluation`'s existing harness shape
(`inference/run_sequential_scenario.py` → transform → `orchestrate_eval.py` → judge →
`collate_all_models.py`) rather than building a new pipeline from scratch, per this
org's stated preference for reusing existing patterns over inventing new ones.

For each farmer, walk their real sessions **in chronological order**:

1. **Before** each session, ask the memory system under test (Option A store, or a
   local Honcho instance seeded from this farmer's prior sessions) what it would
   inject: structured profile + any episodic recall.
2. **Generate two responses** for each real historical turn in that session:
   - **Baseline** — no memory injected; the real historical answer already exists in
     the log and can be used directly as a sanity-check anchor rather than
     re-generated (model versions drift over time, so exact re-generation isn't the
     point).
   - **Treatment** — memory-augmented: same prompt + the memory context from step 1,
     run through the same agent code path (`amul-oan-api`'s actual agent, not a
     standalone prompt harness, so tool-call behavior with memory present is real).
3. **After** the session, feed its real messages into the memory system so it
   updates/reasons over them — this is what makes it "as if memory had existed": by
   the farmer's Nth session in the backtest, the memory system has genuinely
   accumulated everything from their first N-1 real sessions, not synthetic data.

Run once per design variant under test (Option A vs. Honcho Option B vs. hybrid;
preload-only vs. +tool-call recall; reconciled vs. non-reconciled episodic) — output
one wide comparison table per variant, same shape as `oan-evaluation`'s
`all_models.csv`, so variants are comparable side by side.

## Scoring — what "no regression, not annoying" actually means

LLM-judge, pairwise (baseline vs. treatment), reusing the existing comparison-mode
config (`oan-evaluation/config/pipeline_config_goldenset_compare.py`) as a starting
point rather than a new judge from scratch. Score axes:

1. **Factual regression** — did treatment get anything *wrong* that baseline got
   right, especially by trusting stale memory over what the farmer/vet just said this
   turn (e.g. herd composition changed, animal was sold, memory says otherwise)? Hard
   gate — any regression here blocks shipping that variant.
2. **Personalization value-add** — did treatment meaningfully use history (skipped a
   question already answered, referenced a real prior issue accurately, tailored
   advice to the actual herd/animal) versus baseline giving generic advice? This is
   the reason to build memory at all — a variant that never improves on this axis
   isn't worth its added complexity/latency.
3. **Annoyance / unsolicited recall** — does treatment surface memory in a way the
   caller didn't ask for and wouldn't want (e.g. narrating "as you told me last time,
   your cow Ganga..." unprompted, over-personalizing small talk, repeating itself)?
   Voice specifically: any recall that costs airtime without being asked for is a
   worse failure than silence — score this explicitly, don't fold it into general
   "quality."
4. **Latency/cost overhead** — token count added by injected context, and for voice
   specifically, whether the chosen recall mechanism (preload vs. tool-call) actually
   respects the design doc's low-latency requirement in practice, not just in theory.

Gate, mirroring the existing 4-dimension/18-sub-dimension code-enforced pass/fail
pattern the org already uses for model evals (`Evaluation_understanding.md`): a
variant should not ship if it regresses (1) on more than some small threshold of
turns, or scores worse than baseline on (3) more often than it scores better on (2) —
i.e. it should not be net-annoying even where it's occasionally useful.

Spot-check a sample by hand — reuse the existing blind two-round + QC human-eval
process (`future_work/human_evals_alignment/`) rather than trusting the LLM judge
alone, same as the org already does for other quality dimensions.

## Limitations (be upfront about these)

- This is a **counterfactual replay**, not a live experiment: the farmer's real
  historical questions were asked to a bot with no memory, so they never had the
  chance to *rely on* memory being there (e.g. skip re-explaining something) — the
  backtest can only measure "would injecting memory into this exact historical turn
  have helped or hurt," not how conversations would actually reshape if callers knew
  the bot remembered them. Useful as a pre-launch gate, not a substitute for a real
  post-launch A/B once shipped.
- Re-generating "treatment" responses uses whatever model/prompt is current at
  backtest time, not the exact historical production model/prompt (both drift
  meaningfully in this repo — see the branch list of in-flight `feat/`/`fix/` work) —
  some divergence vs. the logged baseline is expected and isn't itself a regression
  signal.

## Open questions

- Who owns Amul's Langfuse credentials/access for this?
- What's the minimum number of multi-day, multi-session farmers needed for a
  meaningful sample? Not sized yet — depends on how common repeat callers actually are
  once filtered to "sessions on different days," which hasn't been checked.
- Does this run against a real Honcho instance (self-hosted, per Option B) for the
  treatment leg, or a mocked/stubbed representation for a first pass before standing
  up infra?
- Doctor-persona backtest: same harness, separate cohort — worth doing in the same
  pass or deferred until farmer-persona memory is further along?
