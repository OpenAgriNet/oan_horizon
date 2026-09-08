# Amul memory

Design work for adding conversation memory to Amul (PashuGPT dairy-farmer assistant:
`voice-oan-api` + `amul-oan-api`). Amul has no memory of past conversations today —
see `memory-design-decisions.md`'s "Current state" for what's verified in the code.

This mirrors the earlier mahaVistaar memory work (`mh-oan-api`; see
`oan-brain/knowledge/mh-oan-api-memory.md` and this repo's `future_work/memory/`) but
starts from a different base: Amul is voice-first (RAYA IVR) with tighter speed
requirements, and this round also weighed two off-the-shelf options —
[Honcho](https://github.com/plastic-labs/honcho) and
[Graphiti](https://github.com/getzep/graphiti) — against building it ourselves.

**Grounding note**: `Amul_understanding.md` (this repo, root) is a useful
high-level map but is stale in places (predates the `doctor` mode, some newer tools,
and the current session-history timing). Where they disagree,
`memory-design-decisions.md` defers to a direct read of
`github.com/OpenAgriNet/amul-oan-api` (checked 2026-09-04) — see that file for
specifics.

## What's here

- **`memory-overview.md` — start here.** A single, plain-language document with
  everything: guiding principles, real examples from actual farmer conversations
  sorted by priority, the feature ideas that came out of reviewing them, made-up
  examples to broaden the thinking, and the technology comparison. Written to be
  marked up, not just read.
- `memory-design-decisions.md` — the technical companion: exactly what exists in the
  code today, what makes Amul different from mahaVistaar, and the decided direction
  (build it ourselves on the vector database already running, not Honcho or
  Graphiti — see that file for why).
- `backtesting-plan.md` — how to test any built version against Amul's real past
  conversations before turning it on for real: replay old conversations as if memory
  had existed, compare against what actually happened, and check for both real
  improvement and any sign of feeling intrusive or annoying.
- `api-and-integration.md` — what's actually built and running: every API path on
  the memory service, the entry shape, how the three levels are served (1 and 2
  injected every turn, 3 via a deliberate query), how it's wired into the bot, and
  an explicit list of what is *not* built yet.
- `log-findings.md` — the real cases this is all based on, found by reading 8
  heavy-repeat farmers' actual month of conversations, plus a second section of
  made-up scenarios (vet mode, loans, the farming calendar, shared phones, patterns
  across farmers, and what memory should deliberately never keep) written to explore
  past what one month of real logs could show.

## Status

**Decided**: build it ourselves, on top of the vector database (Qdrant) already
running for this work — not Honcho, not Graphiti. Reasoning in
`memory-design-decisions.md`.

**Not yet decided**: which specific examples in `memory-overview.md` to actually
build first (priorities are marked, not all agreed), and the open questions listed at
the end of `memory-design-decisions.md` and `memory-overview.md`.
