# Common Evaluation Spec (Vistaar)

This folder defines a shared evaluation approach so teams can score model responses in a consistent way across projects.

The goal is simple:

- clearly define evaluation metrics
- keep metric definitions open and readable
- configure evaluation behavior in YAML
- run the same rubric across different models
- compare quality across both models and projects

## Why this exists

Without a common rubric, each team evaluates differently and results are hard to compare.  
This setup standardizes how we evaluate quality so everyone uses the same definitions.

## Core idea

Each project has a YAML config (`amul.yaml`, `mahavistaar.yaml`) that controls:

- which test data to evaluate
- which model is used as the judge
- which metric rubrics are applied

Metric definitions themselves live in prompt files under `prompts/` and are referenced from YAML.

This gives us a clean separation:

- YAML = what to run
- rubric markdown = what each metric means
- data files = what examples are evaluated

## Evaluation metrics

Metrics are organized into:

- shared metrics (used across projects)
- specific metrics  (voice-specific vs text-specific)

Examples:

- shared: factual quality, usefulness, clarity
- voice-specific: brevity for spoken UX, voice-readiness, translation quality
- text-specific: process fidelity, grounding, language quality

The important principle is that each metric has a clear definition and scoring intent, so evaluations are repeatable.

## How a new metric is added

1. Define the metric clearly in a rubric prompt file.
2. Reference that metric rubric from YAML.
3. Run eval again to generate new scores.

This means metric changes are mostly config-driven and easy to evolve.

## How comparison works

Because rubric definitions are centralized and reused:

- you can compare multiple models inside one project
- you can compare quality trends across projects
- you can track whether model updates improve the same metric set over time

## Human-eval alignment (next step)

LLM-as-judge is useful, but it should be calibrated.

Next step for this framework:

1. Add a human evaluation layer using the same metric definitions.
2. Compare human scores vs LLM judge scores on the same samples.
3. Tune judge prompts and thresholds until LLM scoring matches human judgment closely.

This creates trust in automated evaluation and makes model comparison more reliable.

## Spec mindset

Treat this folder as an evaluation spec:

- metrics are explicit
- definitions are transparent
- configuration is centralized in YAML
- results are comparable and reproducible

That is the foundation needed for consistent model quality governance across Amul, Mahavistaar, and future projects.

## One-Command, Config-Only Workflow

This setup is already designed so the full evaluation pipeline can be run with a single Promptfoo command (using the target YAML config).  
For onboarding a new model, metric, or program, no code changes are required in the evaluation engine. You only update:

- YAML config (what to run, model/provider, test data, metric wiring)
- rubric markdown files (metric definitions and scoring guidance)

Example:
```bash
npm install promptfoo
npx promptfoo eval -c amul.yaml
```

Everything else in the evaluation flow is already structured to work through this configuration layer.
