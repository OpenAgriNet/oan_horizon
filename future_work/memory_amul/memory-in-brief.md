# Amul memory, in brief

Current design as of 9 September 2026.

Memory helps a farmer continue without explaining everything again. It keeps preferences, plans, things tried, outcomes, unresolved concerns and relevant advice previously given. It does not copy every conversation or replace Amul's live milk, payment, price or herd records.

## What we store: three levels

An **episode** follows one situation across conversations—for example, trying to make silage and dealing with spoilage.

| Level | What it holds | When Amul uses it |
|---|---|---|
| **1. Standing record** | A small set of lasting preferences and conversational facts approved by the program team. | Included on every turn when memory is enabled. |
| **2. Episode summary and contents** | A short summary, plus a contents list with at most five rows pointing to numbered pieces of detail. | Relevant summaries are found automatically for the current question. |
| **3. Episode detail** | The fuller account: what the farmer reported, what the bot suggested, what changed and what remains uncertain. | The reply agent searches or opens the detail when needed. |

The program team controls Level 1's fields and size. Its seven optional fields cover conversational name, usual account preference, language/style, animal descriptions, recurring interests, explicit tone/topic boundaries and lasting instructions. These are **not required facts**; the model cannot add fields. The total limit is currently 700 characters.

Level 3 is split into searchable pieces, currently up to 1,200 characters each. Tools return whole pieces, with more available to read. This preserves the written account, not the complete chat transcript.

Episodes also store their last recorded state (`open`, `pending`, `resolved` or `n/a`), dates, source links and earlier versions.

## Traceability, dates and things still open

For each episode, we keep **which conversations and individual turns it came from**. The dreamer selects the supporting turns; code attaches their source IDs and dates. These let a reviewer return to the original conversation and distinguish the farmer's words from the bot's advice. The episode holds references, not another copy of the full transcript. References identify the evidence behind the episode; they do not prove that every sentence was summarized correctly.

| What is recorded | What it means |
|---|---|
| **First and latest mention** (`first_source_ts`, `source_ts`) | When the supporting conversation turns happened. These are not necessarily when the real-world event happened: a farmer can describe last month's problem today. |
| **Saved and replaced times** (`recorded_at`, `superseded_at`) | When this version was written and, if applicable, replaced. Running the dreamer today does not make an old conversation new. |
| **Known end date** (`expires_at`) | A supported deadline or end date, when available. Empty means no end date is recorded, not “valid forever.” |
| **Source references and count** | The individual turns and distinct conversations behind the account. The conversation count is not a count of failed attempts or real-world events. |
| **Previous version** (`previous_version`) | A link to the earlier account, so a reviewer can follow how it changed. |

An update saves a new version and then marks the old version as replaced. Ordinary lookups use the latest version; history remains available. A refused update leaves the old version in place. Reprocessing the same source turns against an episode does not count them again.

The recorded states are simple: **open** for an ongoing matter, **pending** when waiting for a next step or outcome, **resolved** when the evidence supports closure, and **n/a** when a progress state does not fit. They are model judgments about what was reported, not live verification.

**Time passing does not close a matter.** An overdue application can remain open. Giving advice does not prove the farmer followed it or solved the problem. An end date does not hide the episode from current results; replacement by a newer version does. The reply agent sees dates to judge relevance, confirms uncertain current circumstances, and uses live tools for changing facts. There is no general guarantee that a memory remains true until a particular date.

## Keys and the two ways to find memories

**Keys are optional details attached to an episode**, stored as a name and value. They make it possible to ask for matching records without searching through every episode.

| Illustrative episode | Possible keys | What they let the agent list |
|---|---|---|
| A farmer's maize silage trial | `crop=maize`, `storage_method=small_bags` | Episodes recorded about maize, or maize stored in small bags. |
| Another farmer's application follow-up | `scheme=calf_registration`, `application_stage=correction_requested` | Episodes recorded about that scheme or application stage. |

These are examples, not fields every farmer must have. The dreamer adds a key only when it is useful for filtering, reuses existing names where they fit, and documents new ones. There are **no mandatory episode categories**. Unlike Level 1's approved fields, episode keys can grow with the farmer's conversations.

When memory context is included, it can show the reply agent available keys, their meanings and example values from this farmer's records. All lookups stay within the signed-in farmer's memory.

The reply agent has two tools for **finding** memories:

| Tool | When to use it | Example |
|---|---|---|
| **`search_memories`** | Find relevant detail using ordinary words or keywords. It searches by meaning, without requiring keys; it can also search within one chosen episode. | “What went wrong with my silage?” → search for `silage rainwater torn cover`. |
| **`list_memories`** | List or count recorded episodes, optionally filtering by state and key/value matches. | “List my unresolved maize matters” → `state="unresolved"`, `filters={"crop": "maize"}`. |

Only **`list_memories` applies key/value filters**. Multiple keys must all match: `crop=maize` plus `storage_method=small_bags` narrows the list to records carrying both values. `unresolved` includes both open and pending records. With no filters or state restriction, the tool browses all current episodes, following further pages when needed.

A filtered list covers **recorded matches**: an older maize episode without the `crop` key can be missed. The agent can remove filters or broaden its search. Search results are a relevance sample, so they should not be used as a complete list or total count.

A third tool, **`read_memory`**, opens a selected episode's detail, additional chunks or earlier versions. It does not filter by keys.

## Example: silage

Illustration based on the recent demo:

| Level | Example content |
|---|---|
| **1** | “Keep answers short and practical”—only if the farmer expressed that preference. |
| **2** | “Wants to retry small-bag silage after rainwater entered through a torn cover; considering stronger materials.” Contents: “Chunk 1: failed attempt, cover problem and next steps.” |
| **3** | The farmer reported trying small bags and losing fodder after rainwater entered through a torn cover. They are considering stronger covering. The bot suggested stronger bags and protective storage; those are suggestions, not confirmed purchases or actions. |

Later, “How can I avoid what went wrong last time?” can lead to a document search for **silage, rainwater, torn covers and sealing**. Memory supplies personal context; the tool supplies guidance.

Only the farmer's words establish what they said or reported doing. Bot advice stays attributed to the bot. Its mention of a manual cutter does not establish that the farmer uses one.

## How the background agent works

The **dreamer** works separately from the replying bot. It reads Langfuse chat logs in chronological batches of up to ten turns per farmer.

1. **Decide what is useful.** Would this help later? There is no target memory count. Routine lookups can be skipped; useful plans and concerns can be retained.
2. **Look before writing.** Search existing memories, rephrase searches and read detail. Update an existing situation where appropriate.
3. **Propose and check.** Select supporting turns. Separate model checks review sensitive content, unsupported claims and unnecessary or duplicate keys. Failed checks leave proposals unwritten; unavailable checks are retried and reported if still unsuccessful.
4. **Save and maintain.** Save approved detail and summary/contents, retain sources and earlier versions, consolidate duplicates and refresh approved standing fields.

Checks can make mistakes: the silage demo needed an attribution correction. A saved memory is not proof of a completed action or current status.

The memory API writes to **Qdrant**, the database. Amul chat reads Qdrant directly; its existing reply agent searches, lists or reads memories. There is no separate live memory agent. The memory API and Qdrant have different addresses.

A separate user setting controls memory use in replies; the dreamer cannot change it. This implementation does not yet provide automatic reminders or a durable retry queue.

For further detail, see [the full design](memory-overview.md).

## A real demo update: before and after

On 9 September, the silage episode for test user ending **7046** was updated from two new dev conversation turns. Its earlier history was **synthetic demo data**, dated 4 September; it should not be mistaken for verified historical farmer activity.

**Before:** the account described an earlier silage failure from rain entering a torn cover, a plan to replace the cover, and a need for a method without electricity. The state was open.

**New farmer statements:**

> “I want to try making silage in small bags.”
>
> “Okay, I tried this but rainwater entered through a torn cover and it spoiled. Maybe I shoud try something other than flimsy covers next time”

The first turn was at **08:12:46.970 UTC** and the second at **08:13:55.731 UTC**, both on 9 September. They belong to **one** new session. The later sealing question was not yet present in Langfuse when this update ran.

**Final stored summary:**

> The farmer wants to retry small-bag silage after rainwater entered through a torn cover and spoiled it, and is considering stronger covering materials.

The detail preserves the earlier context, adds the small-bag account, and explicitly says it is unclear whether this describes another failed batch or the earlier failure again. The bot's stronger-cover and storage suggestions remain attributed as advice, not confirmed actions. Review removed the unsupported claim that the farmer used a manual cutter; this correction was not fully automatic.

| Field | Before | After the update and review |
|---|---|---|
| Recorded state | `open` | `open`—no successful retry was reported. |
| First mention | 4 Sep, 08:00 UTC | Unchanged. |
| Latest mention | 4 Sep, 08:02 UTC | 9 Sep, 08:13:55.731 UTC. |
| Version saved | 9 Sep, 04:57:48 UTC | 9 Sep, 08:20:26 UTC. |
| End date | None recorded | None recorded; no deadline was invented. |
| Source conversations | 1 synthetic session | 2 sessions: the synthetic history and the new dev session. |
| Supporting turns | 3 synthetic turns | Those 3 plus the 2 dev turns. |
| Optional keys | None | Still none; this update did not add the illustrative maize keys above. |

The retained version chain is **original account → dreamer update → reviewed correction**. There is still one current silage episode, with one detail chunk, and eight current episodes for the user overall. Reviewing the wording did not increase the source-conversation count or change when the farmer last spoke.

For tracing this example, the two new Langfuse trace IDs are `ed0ff8c491c88f422a66b675e913b287` and `a913e26d33709b52152ea7a7d3c1f637`. The final episode ID is `ed947f9f-1e0e-4fad-be4d-57e5b24045a9`. Its earlier accounts can be inspected through the memory API:

```http
GET /memory/9924457046/entries/ed947f9f-1e0e-4fad-be4d-57e5b24045a9/history
```

If the farmer later reports that a retry worked, the next update can record that outcome and mark the matter resolved. Until then, the last supported state stays open.
