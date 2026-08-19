# Scheme Sync → Network-Wide Tool Search

## Where BV is right now

Scheme search in bharat-oan-api works today, but the full scheme list is pasted
directly into the system prompt on every single turn (Jinja-rendered), and the
`search_schemes` tool's own docstring is frozen once at process startup rather than
kept live — a scheme added after the process starts won't appear in that tool's schema
until the next restart. Live scheme lookups themselves already run over the network
(a Beckn `/search` call), with a separate local-Qdrant scheme search function that
exists in code but isn't actually used by the production tool path. This works, but
doesn't scale: every new scheme makes the prompt longer for every farmer's every
message, whether relevant to their question or not.

## Where to go next

[`extension_of_approach.md`](extension_of_approach.md) lays out the proposed fix:
replace "paste the whole list into every prompt" with a queryable tool-search service —
the model recognizes a question's category, searches for the relevant tool instead of
having it all pre-loaded, and falls back to querying other providers on the network if
nothing matches locally. The same service works in reverse, so other networks (e.g.
MahaVistaar) can query BV's tools the same way. Only the top 2–3 most-used tools (like
weather and mandi prices) stay pre-loaded for instant access; everything else, schemes
included, goes through search. This generalizes the fix beyond schemes to every tool
category, not just the one that prompted it.

Not yet implemented — no timeline decided.
