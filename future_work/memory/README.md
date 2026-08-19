# Memory (exploratory — no decisions made yet)

This is a discussion in progress, not a spec. Nothing below is committed. It exists so
the next conversation about memory starts from what's already been explored instead of
from zero.

## What this covers

- A review of what "memory" means for an LLM agent, how production systems elsewhere
  build it (ChatGPT, Mem0, Letta/MemGPT, Zep/Graphiti, Amazon Alexa+, LangGraph),
  what mh-oan-api's own production logs show happening today, mh-oan-api's actual
  current implementation (see `Mh_understanding.md`'s "LONG-TERM MEMORY" section for
  the verified current state), and a set of speculative future use cases.
- A team whiteboard session's design principles and priorities, folded into the same
  document after a round of clarification — "intentional memory" (curate what's kept,
  don't log everything by default), a dependency-ledger framing for a farmer's core
  profile, a proposed MFU/LRU-style retention mechanism, a vote-ranked priority list,
  a crop-calendar/goal-coaching direction, and a community-memory-to-policy idea.

Full write-up: [`memory-review.html`](memory-review.html) (self-contained copy in this
repo) — also live at
**[Memory in mahaVistaar](https://claude.ai/code/artifact/4f92f1a1-2615-4d11-b0f4-080d2d691652)**

## Open questions this raised, not yet answered

- Is profile preload actually firing/populating reliably on every new session for
  farmers who already have saved facts? (Observed gap in production logs, not yet
  instrumented to confirm the cause.)
- What should happen for guest/unauthenticated users, who get no memory at all today —
  nothing, or something ephemeral/session-scoped?
- Should the voice channel get the same identity-linked memory as text? (Not currently
  wired in either direction.)
- What does a real retention/forgetting policy look like in practice, beyond the
  MFU/LRU framing floated on the whiteboard?
- How much of this is worth backporting to bharat-oan-api, which has no memory layer
  at all today?

## Status

Discussion only. Revisit and turn into a real spec (with a decision on what to build,
in what order) once there's alignment on priorities.

