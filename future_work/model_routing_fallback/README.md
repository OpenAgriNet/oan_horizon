# Model Routing & Fallback: Don't Regress Alias-Level Defaults (bharat-oan-api)

Ideal setup defined here - https://github.com/OpenAgriNet/bharat-oan-api/issues/176

## What bh-dev actually does today

`config/models.yaml` defines named model aliases (`gemma_vllm`, `azure_gpt41`, plus a
dormant `bharat_ai_grid_gemma`) under `models:`, and per-use-case (`agrinet`,
`moderation`) routing under `use_cases:`. **Fallback is already defined on the model
alias itself**, not per-use-case:

```yaml
models:
  gemma_vllm:
    kind: vllm
    fallback: {to: azure_gpt41, on_error: [...], on_concurrency_above: 10}
use_cases:
  agrinet:    {aliases: [gemma_vllm, azure_gpt41], proportions: [50, 50], ...}
  moderation: {aliases: [azure_gpt41], ...}   # single alias — nothing to route to
```

`app/services/agrinet_routing.py` resolves this — session-sticky routing (Redis,
7200s TTL), a weighted-random pick on a fresh session, capacity-based deflection when
the vLLM alias is saturated, and a **single-hop** failover (not a chain) on error,
scoped only to the `agrinet` use case. See `Bh_understanding.md`'s "MODEL ROUTING
LAYER" section for the full mechanism.

**The real, still-present gap**: moderation has no fallback path at all — its use case
has exactly one alias, `agrinet_routing.py` doesn't cover it, and no other shared
execution mechanism does either. This is the actual problem issue #176 was raised
against, and it remains unfixed on `bh-dev` 

## The risk in the in-flight fix

PRs #205 and #206 introduce a shared `ModelService.run()` (BFS-based fallback chain
resolution) to generalize routing/fallback across *both* agrinet and moderation —
correctly fixing the gap above. But in doing so, both PRs move `fallback` from the
model alias to **per-use-case** config instead:

```yaml
use_cases:
  moderation: {fallbacks: {azure_gpt41: [gemma_vllm]}}
  agrinet:    {fallbacks: {gemma_vllm: [azure_gpt41], azure_gpt41: [gemma_vllm]}}
```

This is a regression on a property `bh-dev` already has correctly today: a new use
case added later gets **zero fallback** unless someone remembers to also write its own
`fallbacks:` block for it — the same "forgot to wire up a new use case" failure mode
issue #176 was about, just moved from the code layer back into the config layer at
the moment it's being fixed for moderation specifically.

## Recommendation

When generalizing to a shared `ModelService`, keep the default `fallback` **on the
model alias** (as `bh-dev` already does for agrinet), so a new use case inherits sane
behavior for free — plus an optional per-use-case `fallback_overrides: {alias: target}`
for the rare case where a specific use case genuinely needs to disagree with the
alias's default:

```yaml
models:
  gemma_vllm:  {kind: vllm, fallback: azure_gpt41}
  azure_gpt41: {kind: azure-openai, fallback: gemma_vllm}
use_cases:
  agrinet:    {}                                    # inherits both defaults, free
  moderation: {fallback_overrides: {azure_gpt41: some_other_alias}}  # only if needed
```

Note: `capacity.max_concurrency` and related fields are correctly kept at the alias
level in both #205 and #206 already — this recommendation only concerns `fallback`.

## Status

| PR | State | Notes |
|---|---|---|
| #199 | Merged into `bh-dev` | Introduced `config/models.yaml` + `model_registry.py`, with alias-level fallback for agrinet. Moderation was never wired into any shared execution/fallback mechanism — still true today. |
| #205 | Closed, not merged | Added `ModelService.run()` — a real shared execution path that would fix moderation's gap. Reviewed and given the alias-level-default feedback above; moved fallback to per-use-case instead. |
| #206 | Open (`feature/unified-llm-fallback-service`) | A fresh resubmission of the same lineage, not a revision of #205. Verified directly against its `config/models.yaml` and `model_registry.py`: reproduces the exact same per-use-case-only design. |

**Neither #205 nor #206 is merged.** `bh-dev`'s current alias-level fallback (agrinet
only) and moderation's total lack of fallback are both real, current facts — verify
`config/models.yaml`'s actual structure before relying on any description here,
including this one.



## Appendix 
