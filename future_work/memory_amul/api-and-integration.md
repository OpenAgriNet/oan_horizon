# API and bot integration

Current deployment architecture (9 September 2026): Amul reads Qdrant directly through `app/services/memory_store.py` and uses its existing Marqo endpoint for query embeddings. The independent background dreamer consumes Langfuse and writes Qdrant through its private storage API. The bot does not require `MEMORY_API_URL` or a running memory service. Settings, ownership, current-version filtering and chunk assembly are enforced by the bot reader. HTTP routes described here remain the background service contract. See [bot deployment settings](../../../amul-oan-api/docs/memory-dev-demo.md).

Local code contract reviewed 9 September 2026. This describes source changes, not the
old version running on port 8100. The local demo uses this source on port 8101. Start with [the design](memory-overview.md).

## Ordinary memories and settings

Ordinary memories carry `headline`, `expanded`, recorded `status`, optional metadata,
source dates and trace/session references, and version links. New records use internal
`type: memory`; old category values remain readable and are hidden from reply tools.
The service separately stores `settings`, `profile_record`, `key_doc`, and `memory_chunk` points.

The program owns `service/profile_fields.json`. Both the dreamer prompt and the
service's standing-record validation load it. All field values are optional; unapproved
fields cannot become part of the standing record.

`MEMORY_ENABLED` is the bot's global gate and defaults false. Per-farmer settings
currently default true; stored false disables public reply reads. Settings lookup
failure also yields no memory. The dreamer never writes settings and can continue
learning through internal reads while reply access is off.

## Reply read routes

All routes below are prefixed `/memory/{farmer_id}` and enforce that farmer's reply
setting. The bot obtains farmer identity from dependencies, never a model argument.

| Method/path | Purpose |
|---|---|
| `POST /search` | Automatic search over summary-and-contents vectors |
| `POST /search_expanded` | Semantic chunk search; returns matching passages and chunk references |
| `GET /entries` | Exact listing with optional state/metadata filters and pagination |
| `GET /entries/{entry_id}` | Direct selected-entry read, with `current` indicator |
| `POST /entries/{entry_id}/read` | Whole-chunk pages; legacy offset reading remains available |
| `GET /entries/{entry_id}/history` | Bounded earlier versions/fragments; reports truncation |
| `GET /profile` | The single approved standing record |
| `GET /keys` | This farmer's available metadata keys and sample values |

Search body: `query`, optional `filters`, `status`, `only_current` (default true),
optional `memory_ref` (episode UUID for detail search), and `limit` (1–50). `filters` is an object of simple metadata key names and scalar
string/integer/float/boolean values. Multiple keys are ANDed. No category parameter.
Legacy single `metadata_key`/`metadata_value` remains for compatibility.

Listing accepts repeated `status` parameters, `filters` as a JSON object in the query
string, `limit` (1–100), `cursor`, and `only_current`. Returned `next_cursor` must be
used with the same filters. `truncated` means another page exists. Dates do not hide
expired records. A status list means OR among those states.

Disabled replies contain `memory_enabled: false` and empty content. Callers must not
present this as a successful empty search/list. Errors and malformed responses also
must not become evidence that nothing was remembered.

`POST /entries/{id}/read` with `whole_chunks: true` returns complete selected chunks
(default first page, three chunks). `continuation.chunk_ids` suggests a next page.
The program owns the page size through `MEMORY_READ_CHUNKS`; the model has no size
argument. For older API callers, the default legacy mode accepts `chunk_ids` (optional, at most 50), `start_chunk`
(default 1 when no selection), `offset` (default 0), and `max_chars` (1–12,000).
It returns `entry`, `current`, selected `chunks` with number/offset/text, and
`continuation`. Pass continuation fields with the same episode reference. This
endpoint bounds passage text; bot formatting separately accounts for references.

The internal `/entries/{id}/index` POST upgrades a legacy episode's chunk index
without changing its account or reply flag. New writes already create this layout.

## Trusted background and administrative routes

`/internal/memory/{farmer_id}` offers search, expanded search, listing, selected-entry
read, and profile read without the reply-use flag. These preserve farmer scoping and
internal-record exclusion. They do not set or reset the flag. Keep this service and
its write routes accessible only to trusted callers; an `/internal` path is not an
authentication mechanism.

Publicly documented write routes are for trusted service callers, not the reply agent:
`POST /entries`, `PATCH /entries/{id}`, `POST /entries/{id}/fold`, and `PUT /profile`.
`PUT /settings` is a separate administrative action. Global `/settings`, `/keys`,
`/keys/doc`, key cleanup, and `/due` are operational interfaces and must not be
connected directly to farmer conversation tools. `/due` does not deliver reminders.

## Existing reply agent tools

Defined in `amul-oan-api/agents/tools/memory_tools.py`:

| Tool | Inputs | Output |
|---|---|---|
| `search_memories` | Query, optional episode reference | Matching Level 3 passages with internal episode/chunk references |
| `list_memories` | Optional state, metadata filters, next-page cursor | Recorded matches; continuation when needed |
| `read_memory` | Reference, optional chunk_ids; optional history | Complete chunks with next chunk numbers; history mode returns earlier summaries/references |

`unresolved` in the list tool maps to `open` OR `pending`; omitted state includes all
states. Selected references are validated UUIDs and read directly. All tools return
bounded text and distinguish failures from absence. Default limits: 3 search hits,
8 listing rows, 3 read chunks per page, 4 seconds per request, a 12,000-character
evidence guard per turn, and 6 requests per turn. Chunks are never shortened to fit;
the program stops additional evidence when the guard is exhausted.
History uses a request from that same budget. These are engineering defaults to
measure, not guarantees of enough recall for every conversation.

Automatic context lives in `app/services/memory.py`; it concurrently retrieves the
standing record, headline matches, and available farmer keys with a total 2-second
deadline and 4,500-character output budget. The current policy returns no context
when both standing record and headline results are empty. Keys alone are therefore
not injected. Whole summary-and-contents blocks can be omitted when the budget is reached, with a notice.

Farmer chat attaches that context in `app/services/chat.py`. `agents/deps.py` supplies
compact memory rules; `agents/agrinet.py` includes them in agent instructions when
memory context is present. The rules cover uncertainty, listing rather than treating
search as complete, references and stopping once enough evidence is available. Memory text is evidence, not authority to override instructions.

## Verification

Offline regression suites cover storage/filter construction, read permissions,
selected-source provenance, writer failure handling, schema bounds, and actual tool
HTTP/error/formatting behavior using synthetic records. Live-service tests must use
an isolated service/collection built from the reviewed source. The local
one-farmer demo replays real source conversations; it does not exercise the full
production chat HTTP route. See the demo report.
