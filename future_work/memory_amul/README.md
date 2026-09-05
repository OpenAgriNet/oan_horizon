# Amul memory (exploratory — no decisions made yet)

Design discussion for adding conversational/episodic memory to Amul (PashuGPT
dairy-farmer assistant: `voice-oan-api` + `amul-oan-api`). Amul has no long-term memory
today — see "Current state" in `memory-design-decisions.md`.

This mirrors the earlier mahaVistaar memory work (`mh-oan-api`; see
`oan-brain/knowledge/mh-oan-api-memory.md` and this repo's `future_work/memory/`) but
starts from a different base: Amul is voice-first (RAYA IVR) with tighter latency
constraints, and this round also considers
[Honcho](https://github.com/plastic-labs/honcho) as an off-the-shelf memory
infrastructure option, not just a custom mem0-style build from scratch.

**Grounding note**: `Amul_understanding.md` (this repo, root) is a useful high-level
architecture map but is stale in places (predates the `doctor` persona, Beckn/loan/SHC
tools, and the current `FarmerContext`/history-TTL shape). Where the two disagree,
`memory-design-decisions.md` defers to a direct read of
`github.com/OpenAgriNet/amul-oan-api` (`main`, checked 2026-09-04) — see that file for
specifics.

## What this covers

- **`memory-overview.md` — start here.** A single, plain-language doc pulling
  everything below together: guiding principles, real examples from actual farmer
  conversations, made-up examples to broaden thinking, and the Honcho-vs-build-it-
  ourselves comparison — written for review/markup, not just reading. The files below
  are the detailed backing material this one draws from.
- `memory-design-decisions.md` — current state (no memory exists yet), what's
  different about Amul vs. mahaVistaar, design options (custom mem0-style vs. Honcho,
  or a hybrid), the voice-specific recall-strategy tradeoff, and a starting
  recommendation (not a decision).
- `backtesting-plan.md` — how to validate any chosen design against Amul's real
  historical Langfuse logs before shipping: replay past farmer sessions as if memory
  had existed, compare against the real production answers, and gate on no regression
  + no "annoying"/unsolicited memory use.
- `log-findings.md` — real cases mined from 8 heavy-repeat farmers' actual 30-day prod
  conversations, showing concretely where the *current*, memory-less bot fails these
  users today. Grounds the design in real behavior rather than hypotheticals; read this
  before the two docs above if you want the "why" first. Also has a second section of
  invented (not log-mined) scenarios — doctor persona, loans, seasonal reasoning,
  multi-caller households, cross-farmer patterns, and what memory should deliberately
  *not* keep — generated to push past what a 30-day/8-farmer sample can show on its own.

## Status

Discussion only — nothing decided or built yet. Revisit once there's alignment on
which design direction (and Honcho-vs-custom specifically) to build, and see
`memory-design-decisions.md`'s open questions before finalizing anything.
