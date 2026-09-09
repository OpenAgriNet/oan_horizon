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

Episodes also store their last recorded state (`open`, `pending`, `resolved` or `n/a`), dates, source links and earlier versions. Optional keys such as `crop=maize` help list records. Keys can differ between farmers; there are **no mandatory episode categories**. Filtered lists can miss untagged records; ordinary search remains available.

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
