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

### Current implementations: 

============================================================================
                    MODEL ROUTING LAYER (bharat-oan-api specific)
============================================================================
This is the single biggest architectural difference from mh-oan-api's
static "primary model + one hardcoded Azure fallback" pattern. It is
config-driven, session-sticky, capacity-aware, and (for the "agrinet"
use case only) has a one-hop failover retry. It does NOT match an
earlier internal description of this layer as an `agents/model_service.py`
`ModelService.run(use_case, runner, ...)` with a BFS-based, cycle-safe
`registry.get_fallback_chain()` — no such file, class, method, or BFS
logic exists anywhere in `origin/bh-dev`. That abstraction only exists on
unmerged feature branches (PRs #205/#206) proposing to REPLACE the
mechanism below — see the MODEL ROUTING & FALLBACK FUTURE WORK note.
What actually exists on bh-dev today:

  config/models.yaml
    models:                                  # named model aliases
      azure_gpt41:          kind: azure-openai   (deployment/endpoint/key/version)
      gemma_vllm:            kind: vllm            (model_name/base_url/api_key)
        fallback: {to: azure_gpt41, on_error: [ModelHTTPError, TimeoutError],
                   on_concurrency_above: 10, metrics_cache_ttl: 2}
      bharat_ai_grid_gemma:  kind: bharat_ai_grid  (defined, but NOT referenced
                             by any use_case's `aliases` — dormant/staged alias)
    use_cases:
      moderation: {default_alias: azure_gpt41, aliases: [azure_gpt41],
                   timeout_seconds: 20}       # single alias — nothing to route
      agrinet:    {default_alias: azure_gpt41, aliases: [gemma_vllm, azure_gpt41],
                   proportions: [50, 50], routing_ttl_seconds: 7200,
                   timeout_seconds: 45}

  IMPORTANT: fallback is defined on the MODEL ALIAS itself here
  (models.gemma_vllm.fallback), not per-use-case. This is the design
  property the #205/#206 rework (see future_work/model_routing_fallback/)
  proposes moving to a per-use-case `fallbacks:` block instead — i.e. that
  rework would regress this specific property on today's bh-dev, even
  though it separately fixes a real gap (moderation has no fallback path
  through any shared mechanism at all today — see below).

  agents/model_registry.py — ModelRegistry class, get_registry() (lru_cache
    singleton). Loads the YAML once, resolves every "${ENV_VAR}" string via
    os.environ, and lazily builds+caches one pydantic-ai OpenAIChatModel per
    alias through a kind-keyed builder table:
      {"openai": _build_openai, "vllm": _build_vllm,
       "bharat_ai_grid": _build_vllm, "azure-openai": _build_azure}
    (bharat_ai_grid intentionally reuses the vllm builder — same OpenAI-
    compatible wire protocol — but that is a protocol fact, not a guarantee
    about the backend; see the guided-decoding note below.) Azure models are
    built from an `openai.AsyncAzureOpenAI` client wrapped in
    `OpenAIProvider(openai_client=...)`; vllm/bharat_ai_grid/openai use
    `OpenAIProvider(base_url=..., api_key=...)`.
    Other methods: get_use_case_aliases/get_use_case_proportions (falls back
    to an even split if `proportions` is omitted), get_default_alias,
    get_routing_ttl, get_timeout, get_fallback_alias, get_fallback_on_
    concurrency, get_metrics_cache_ttl, get_metrics_url (derives
    "{base_url minus /v1}/metrics" unless overridden), and
    validate_use_case() (startup config validation — checks aliases exist,
    proportions sum to 100, ttl > 0, default_alias resolvable).
    NOTE: this class has no `get_kind()` method on bh-dev — that method
    only exists on the unmerged OD-2764_v1 branch (added for the
    guided-decoding vllm-only gate; see below).

  app/services/agrinet_routing.py — the actual per-request decision logic,
    scoped to the "agrinet" use case only:
    resolve_agrinet_route(session_id, has_history) -> AgrinetRouteDecision
      (route, model_name, source), where source is one of:
        "routing_disabled"      — settings.agrinet_routing_enabled is False
                                   (env AGRINET_ROUTING_ENABLED, default
                                   "false") -> always returns the fixed
                                   default_alias, i.e. behaves exactly like
                                   mh's static single-model routing.
        "redis"                 — a sticky pick already exists for this
                                   session (Redis key "{session_id}_
                                   AGRINET_ROUTE", TTL = routing_ttl_seconds
                                   = 7200s, refreshed every successful turn).
        "session_start_weighted"— no history and no sticky pick yet: a fresh
                                   weighted-random choice via
                                   choose_weighted_agrinet_route() (cumulative-
                                   weight roll against aliases/proportions,
                                   e.g. 50/50 gemma_vllm vs azure_gpt41),
                                   then written to Redis for the session.
        "state_repair"          — history exists but no sticky Redis pick
                                   (e.g. TTL expired mid-conversation):
                                   repairs to the use case's default_alias
                                   and logs a warning, rather than re-rolling.
        "capacity_deflect"      — the picked alias's own vLLM /metrics
                                   endpoint (vllm:num_requests_running +
                                   num_requests_waiting, regex-parsed) shows
                                   concurrency >= fallback.on_concurrency_above
                                   (10 for gemma_vllm); this turn only is
                                   deflected to the default_alias. The
                                   concurrency reading itself is cached in
                                   Redis for metrics_cache_ttl seconds (2s)
                                   to avoid hammering /metrics every turn.
                                   Deliberately does NOT rewrite the session's
                                   sticky Redis route — saturation is
                                   transient, so treating it as permanent
                                   would silently drain the canary cohort.
        "failover"               — see below.
    get_alternate_agrinet_route(route) -> registry.get_fallback_alias(route)
      or the default_alias if none configured. This is a SINGLE hop, not a
      chain: gemma_vllm's only configured fallback is azure_gpt41, and
      azure_gpt41 has no `fallback:` block at all in config/models.yaml.

  Failover mechanics (app/services/chat.py):
    _run_agrinet_with_failover_streaming wraps one attempt on the initial
    route; on any exception, IF settings.agrinet_routing_enabled AND no
    chunk has reached the client yet (_StreamChunkSink.emitted is False),
    it resolves the alternate route via get_alternate_agrinet_route(),
    retries once with source="failover", and on success overwrites the
    session's sticky Redis route to the fallback alias
    (set_session_agrinet_route) so subsequent turns stay there. If a chunk
    has already streamed to the farmer, the retry is skipped and the
    exception propagates — a half-delivered answer is never doubled.
    NOTE: config/models.yaml's `fallback.on_error: [ModelHTTPError,
    TimeoutError]` list is declarative only — ModelRegistry has no getter
    for it (only get_fallback_alias/get_fallback_on_concurrency/
    get_metrics_cache_ttl/get_metrics_url exist) and chat.py's failover
    catches a bare `except Exception`, not a type-filtered one. In
    practice, any exception triggers the one-hop failover (subject to the
    "no chunk streamed yet" gate above), regardless of what the yaml lists.
    If agrinet_routing_enabled is False, no failover is attempted at all;
    the exception just propagates (matches mh's simpler failure mode).
    A non-streaming twin of this whole path (_run_agrinet_with_failover /
    _run_agrinet_once, further up in chat.py) exists in source but is
    never called from any router — /api/chat/ and /api/chat/analyze-image
    both go through the streaming path only.
    Moderation has NO equivalent failover path at all — its use case has
    exactly one alias (azure_gpt41), so there is nothing to route to on
    failure. This is the real, still-present gap the #199/#205/#206
    history is about: moderation was never wired into any shared
    execution/fallback mechanism, agrinet's routing module doesn't cover
    it, and no other code path does either.

  Startup validation: main.py's lifespan() calls
    agents.models.validate_agrinet_routing_config() (after
    token.validate_multi_provider_auth_config()) — only runs its checks
    (validate_use_case("agrinet") + force-building every agrinet alias's
    model object) if agrinet_routing_enabled is True; otherwise it is a
    no-op, so a misconfigured gemma_vllm alias does not block startup
    while routing is off.

  Whether AGRINET_ROUTING_ENABLED=true in the actual deployed bh-dev
  environment is not verifiable from source