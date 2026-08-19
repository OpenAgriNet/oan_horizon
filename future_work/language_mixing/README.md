# Language-Mixing Guardrail (bharat-oan-api)

Constrain agrinet's response text to stay within the farmer's selected language and
script, instead of letting the model drift into another script mid-answer.

## Why this matters

For Indic-language users, an answer that suddenly switches script mid-sentence (e.g.
a Kannada response lapsing into Hindi or English) is jarring and undermines trust —
it reads as broken, not just imperfect. This is a real, observed failure mode for the
base model on several Indic languages, not a hypothetical edge case.

An earlier attempt at fixing this used a hand-picked list of "extra" punctuation and
symbols allowed alongside the target script. It missed real characters actually used
in practice — things like the danda (the Devanagari-family sentence-ending punctuation
mark) and the zero-width joiner/non-joiner used to form correct Indic conjuncts — so
legitimate output got incorrectly blocked, and the fix had to be pulled.

## Goal

Every gated language's response should be enforceable to only ever contain: its own
script, standard ASCII, and the Unicode characters that are legitimately shared across
all scripts (punctuation, common symbols, emoji, combining marks used for conjuncts).
Nothing hand-picked, nothing guessed — the shared-character set should be derived from
Unicode's own classification of what's universal versus script-specific, so nothing
legitimate gets missed the way the earlier attempt missed it.

## Approach

- **Allowlist, not denylist.** Define what's allowed (own script + ASCII + universally
  shared characters), rather than trying to enumerate everything to block. A denylist
  has to guess every possible foreign character it needs to exclude; an allowlist only
  has to correctly describe what's actually valid, which is the smaller and more
  stable problem.
- **Derive the shared-character set programmatically.** Rather than hand-picking
  "extra" punctuation, compute it from Unicode's own Script property — specifically,
  the codepoints Unicode itself classifies as common-to-all-scripts or inherited
  (combining marks). This is what correctly includes things like the danda and
  zero-width joiner/non-joiner without anyone having to think to add them by hand.
- **Enforce via constrained decoding.** Rather than checking and rejecting output
  after the fact, constrain what the model is structurally allowed to generate at
  each step, so it can't produce an out-of-script character in the first place.
- **Scope the gate to where it's needed and where it's reliable.** Only apply the
  constraint to languages actually observed to mix scripts — not every supported
  language needs it, and applying it where it isn't needed only adds cost for no
  benefit. Similarly, only apply it on the specific model-serving path where the
  constrained-decoding mechanism is actually known to work correctly; a mechanism
  that behaves correctly on one serving backend can't be assumed to work identically
  on a different one without separately verifying it.
- **Precompute, don't rebuild per request.** The per-language allowed-character
  pattern only depends on the language, not on the request — build it once when the
  service starts, not on every incoming message.

## What "done" looks like

- Every gated language's responses are verified to stay within its own script, ASCII,
  and shared characters — including under adversarial prompting that tries to induce
  a script switch.
- No legitimate shared punctuation, symbol, or conjunct-forming mark is ever
  incorrectly blocked — this was the specific way the earlier attempt failed, so it's
  the main regression to guard against.
- No measurable cost to answer quality or latency versus not having the constraint at
  all.

## Status

Implemented and verified against the criteria above; not yet merged into the main
development branch.
