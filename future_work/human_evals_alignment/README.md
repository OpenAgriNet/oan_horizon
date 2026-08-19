# Human Evals → Automated Judge Alignment

We have human evaluation results across all answers in this folder, produced through a
two-stage independent scoring pass plus a QC reconciliation stage:

- `Stage 1 Evaluations_Results.xlsx` — first evaluator, per language, on the shared rubric.
- `Stage 2 Evaluations_Results.xlsx` — second evaluator, independently, same rubric.
- `Stage 3_QC_Review_Results.xlsx` — a QC reviewer sees both stages' scores and remarks
  side by side and assigns the final, adjudicated score per response.

No analysis of the results themselves lives here — these are the raw sheets. Read them
directly for anything about what the scores actually show.

## Why blind, two rounds

A human eval is only trustworthy enough to calibrate an automated judge against if:

- **Scoring is blind** — each evaluator scores without seeing the other's scores, so one
  rater's judgment can't anchor the other's.
- **There are two independent rounds, plus reconciliation** — a single rater's score is
  noisy on its own; two independent passes reconciled by a third reviewer (Stage 3 here)
  is what turns individual judgment into a reliable ground truth.

## Next step: automated calibration against these results

The current LLM-as-judge eval pipeline (`oan-evaluation`) should be tuned so its scores
track this human ground truth, rather than trusting the judge prompt as written. The
planned approach is to use an automated prompt-optimization framework — **DSPy** is the
current candidate — to calibrate the judge:

1. Treat each Stage 3-adjudicated row as a labeled example: (question, response, rubric
   metric) → human score.
2. Wrap the existing judge (rubric prompt + scoring call) as a DSPy program.
3. Run a DSPy optimizer (e.g. `MIPROv2` / `BootstrapFewShot`) against the labeled set,
   with agreement-to-human-score as the metric being optimized.
4. Hold out a slice of the labeled data to check the optimized judge actually
   generalizes, rather than just fitting the examples it was tuned on.
5. Re-run this calibration whenever the rubric changes or a new batch of human evals
   lands, rather than treating it as a one-time fit.

Not yet implemented — this is the plan, not a status report.
