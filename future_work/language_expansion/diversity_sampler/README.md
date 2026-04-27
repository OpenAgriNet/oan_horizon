# Diversity sampling (queries)

How we pick a **diverse** set of evaluation queries so a language readiness run reflects real failure modes, not a narrow slice of the domain.

- **Maximize token and topic coverage** — prefer a query set that, taken together, hits a large share of important domain vocabulary, entities, and document regions (coverage-driven selection over a random grab).
- **Span difficulty and context length** — mix short, single-hop questions with multi-step, long-context, and ambiguous or underspecified requests so the sample catches brittle behavior.
- **Layer modality of truth** — include questions where the answer is strictly in-doc, partially inferred, and tool-dependent, so you stress grounding, reasoning, and agentic paths differently.
- **Oversample high-risk and edge cases** — explicitly include safety and policy-relevant asks, name/number-sensitive queries, and known failure patterns from production, in addition to the “typical” middle of the distribution.
