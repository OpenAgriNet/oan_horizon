# Documentation: Query Lifetime (mh-oan-api)

```text============================================================================
             MAHAVISTAAR OAN - BACKEND AGENTIC ARCHITECTURE
                           (mh-oan-api)
============================================================================
                            ┌─────────────────┐
                            │   CALLER/USER   │
                            └────────┬────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               │                     │                     │
      ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
      │ WEB/APP CLIENT  │   │ VOICE CLIENT    │   │ FUTURE CHANNELS │
      │ (React/Next)    │   │ (mobile app)    │   │ (WhatsApp etc.) │
      └────────┬────────┘   └────────┬────────┘   └─────────────────┘
               │ HTTP GET/POST       │ Audio + text APIs
               ▼                     ▼
┌────────────────────────────────────────────────────────────────────┐
│      mh-oan-api / MahaVistaar AI API (FastAPI :8000)               │
│      api_prefix from settings (default /api)                       │
│                                                                    │
│  GET  /api/chat/        -> StreamingResponse (text/event-stream)   │
│       Query: session_id, query, source_lang, target_lang, user_id  │
│       Auth: Bearer JWT (RS256; public key from JWT_PUBLIC_KEY_PATH)│
│  POST /api/transcribe/  -> JSON (text + lang_code + session_id)    │
│  POST /api/tts/         -> JSON (base64 audio_data)                │
│  GET  /api/suggest/     -> JSON (cached list of suggestion strings)│
│  GET  /api/health/live  -> liveness                                │
│  GET  /api/health/ready -> readiness + Redis                       │
│  GET  /api/health/      -> app metadata + dependency health        │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                  CHAT PRE-PROCESSING PIPELINE                      │
│                                                                    │
│  1) Build FarmerContext(deps):                                     │
│     - query (Bhili bhb: translated to English before agent)        │
│     - lang_code = target_lang (response / agent language)          │
│     - farmer_id from JWT payload (user_info.get('farmer_id'))      │
│                                                                    │
│  2) Extract recent conversation pairs from history                 │
│     - include up to last 3 user/assistant exchanges (moderation)   │
│                                                                    │
│  3) Moderation pass (moderation_agent)                             │
│     Categories:                                                    │
│       valid_agricultural, invalid_language,                        │
│       invalid_non_agricultural, invalid_external_reference,        │
│       invalid_compound_mixed, unsafe_illegal,                      │
│       political_controversial, cultural_sensitive, role_obfuscation│
│                                                                    │
│  4) Suggestion trigger (background task)                           │
│     - only when category == valid_agricultural                     │
│     - create_suggestions(session_id, target_lang)                  │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    PYDANTIC AI AGENT LOOP                          │
│                                                                    │
│  Main agent: agrinet_agent (registered name: "Vistaar Agent")      │
│  Model: AGRINET_MODEL from agents/models.py                        │
│    Primary:  vLLM endpoint (VLLM_AGRINET_MODEL_URL)                │
│              model name: LLM_AGRINET_MODEL_NAME                    │
│              concurrency limit: VLLM_AGRINET_MAX_CONCURRENT (60)   │
│    Fallback: Azure OpenAI (AZURE_OPENAI_DEPLOYMENT_NAME)           │
│              triggers on: ModelAPIError, APIError,                 │
│              ConcurrencyLimitExceeded, UnexpectedModelBehavior     │
│  Prompt: agrinet_system_{lang_code}.md                             │
│          (Jinja context: today_date, crop_season)                  │
│  Settings:                                                         │
│    - max_tokens=32768                                              │
│    - parallel_tool_calls=True                                      │
│    - request_limit=10                                              │
│    - retries=3                                                     │
│    - end_strategy='exhaustive'                                     │
│    - instrument=False                                              │
│                                                                    │
│  Support agents:                                                   │
│    - moderation_agent                                              │
│        Model: MODERATION_MODEL (same vLLM+Azure fallback pattern,  │
│               separate endpoint: VLLM_MODERATION_MODEL_URL)        │
│        vLLM settings: temperature=1.0, max_tokens=1024,            │
│                       reasoning_effort='low'                       │
│        retries=3, request_limit=5                                  │
│        instrument=False                                            │
│        output: PromptedOutput(QueryModerationResult)               │
│                                                                    │
│    - suggestions_agent                                             │
│        Model: AGRINET_MODEL (same as main agent)                   │
│        output: NativeOutput(List[str])                             │
│        retries=3, instrument=True                                  │
│        end_strategy='exhaustive'                                   │
│        No tools registered                                         │
│                                                                    │
│  Tooling surface (registration order in agents/tools/__init__.py): │
│    - Glossary: search_terms                                        │
│    - Knowledge: search_documents, search_videos                    │
│    - Geo: reverse_geocode, forward_geocode (Mapbox-backed)         │
│    - Weather: weather_forecast, weather_historical                 │
│    - Market: mandi_prices                                          │
│    - Services: agri_services, contact_agricultural_staff           │
│    - Identity/profile: fetch_agristack_data                        │
│    - Long-term memory (mem0 + profile; hidden entirely from guests │
│      via _require_farmer_identity — not just refused, not offered  │
│      to the model at all): recall_farmer_memory, save_farmer_memory,│
│      edit_farmer_memory, delete_farmer_memory, update_farmer_profile,│
│      remove_farmer_profile_value                                   │
│    - Schemes: get_scheme_codes, get_scheme_info                    │
│    - MahaDBT: get_scheme_status                                    │
│    - Pest detection: analyze_pest_disease_image                    │
│                                                                    │
│  Agent loop shape:                                                 │
│    user_prompt + message_history + deps                            │
│      -> stream tokens                                              │
│      -> if tool_call: execute tool -> feed result back -> continue │
│      -> if text: stream delta to client                            │
│    History trim: trim_history(..., max_tokens=80_000,              │
│      include_system_prompts=True, include_tool_calls=True)         │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DELIVERY LAYER                              │
│                                                                    │
│  CHAT:    streaming output; Bhili (bhb): buffer by paragraph,      │
│           translate EN -> bhb per paragraph for stream             │
│  SUGGEST: cached strings; for target_lang=bhb cache in EN then     │
│           Bhashini-translate on read                               │
│  STT:     POST /transcribe implements service_type=bhashini only   │
│           (Whisper helper exists but router returns 400 otherwise) │
│  TTS:     Bhashini; source_lang=bhb uses Bhili/cloned voice path   │
│           (text_to_speech_bhili); else pipeline TTS                │
│                                                                    │
│  Post-stream side effects:                                         │
│    - Append newly generated messages and persist history in Redis  │
│      under key {session_id}_SVA                                    │
│    - Moderation messages persisted separately under                │
│      key {session_id}_SVA_MODERATION                               │
└────────────────────────────────────────────────────────────────────┘
============================================================================
                         EXTERNAL INTEGRATIONS
============================================================================
  - LLM PROVIDERS
    - Primary: vLLM-compatible endpoint (VLLM_AGRINET_MODEL_URL /
               VLLM_MODERATION_MODEL_URL); OpenAI-compatible API
    - Fallback: Azure OpenAI (AZURE_OPENAI_ENDPOINT +
                AZURE_OPENAI_DEPLOYMENT_NAME + AZURE_OPENAI_API_KEY)
  - PLATFORM BACKEND (Beckn/BAP via BAP_ENDPOINT, BAP_ID, BAP_URI)
    - weather
    - mandi
    - agri services
    - staff contacts
    - scheme info/codes
    - Agristack farmer data
    - MahaDBT scheme status
  - VECTOR SEARCH
    - Marqo (document/video search)
  - VOICE / LANGUAGE
    - Bhashini: STT, TTS, translation (incl. suggestions for bhb)
    - Bhili-specific TTS path for code bhb
    - helpers/transcription.transcribe_whisper available but not exposed
      on /api/transcribe/
  - GEO
    - Mapbox: geocoding/reverse geocoding for tools
  - OBSERVABILITY
    - helpers.telemetry + app.tasks.telemetry (e.g. send_telemetry);
      telemetry API URL in app.config settings
============================================================================
                           MODERATION
============================================================================
  Prompt used:
    - assets/prompts/moderation_system.md

  Model used:
    - MODERATION_MODEL (agents/models.py)
    - Primary:  vLLM endpoint (VLLM_MODERATION_MODEL_URL)
                model name: LLM_MODERATION_MODEL_NAME
                concurrency limit: VLLM_MODERATION_MAX_CONCURRENT (100)
                settings: temperature=1.0, max_tokens=1024,
                          reasoning_effort='low'
    - Fallback: Azure OpenAI (same as main agent)
                triggers on: ModelAPIError, APIError,
                ConcurrencyLimitExceeded, UnexpectedModelBehavior

  Runtime moderation settings:
    - retries=3
    - request_limit=5
    - instrument=False

  Structured output contract (QueryModerationResult):
    - category (one of):
      valid_agricultural, invalid_language, invalid_non_agricultural,
      invalid_external_reference, invalid_compound_mixed, unsafe_illegal,
      political_controversial, cultural_sensitive, role_obfuscation
    - action (English recommendation string)

  How moderation is applied in request flow:
    - Input to moderation includes:
      - recent conversation summary (up to last 3 message pairs)
      - user query + selected language + agristack availability marker
    - moderation_agent.run(...) executes before agrinet_agent.run_stream(...)
    - moderation result is injected into FarmerContext for main-agent reasoning
    - suggestion generation is triggered only when category == valid_agricultural
============================================================================
                        LONG-TERM MEMORY
============================================================================
  mh-oan-api is the only OAN backend with real cross-session memory today
  (bharat-oan-api has none of this — Marqo/Qdrant there is query-time content
  search only, never a per-user store).

  Two parallel stores, both real and wired into the agent as tools:
    - Episodic (app/services/memory.py, MemoryService):
        wraps mem0.Memory over Qdrant collection
        vistaar_chat_farmer_memories
        Embedder: text-embedding-3-small (1536-dim, OpenAI-compatible)
          -> genuine semantic search, not a placeholder
        search(): client.search(query, filters={"user_id": ...}, top_k=5,
                                 threshold=0.3)
        add_fact(): mem0 infer=True extraction, additive with exact-hash
          dedup (does NOT supersede a contradicting fact, e.g. a crop change)
    - Structured profile (app/services/profile.py, FarmerProfile model):
        village, district, state, preferred_mandi, crops, land_area_acres,
        irrigation, soil_type, livestock, language, preferred_call_time,
        schemes, open_threads (topic/advice_given/status), notes
        One Qdrant point per farmer, collection vistaar_farmer_profiles
        _PLACEHOLDER_VECTOR = [0.0] -> NOT semantic search, a plain keyed
          document store (own docstring: "1-d placeholder vector")

  Identity (app/services/identity.py, resolve_memory_user_id()):
    - Priority 1: JWT phone claim, SHA-256 hashed (normalized +91XXXXXXXXXX)
    - Falls back through other stable JWT ids
    - Explicit guest detection (_is_guest_value) returns None
      -> memory tools aren't merely refused, they're never even shown to
         the model for a guest session (see Tooling surface, and
         _require_farmer_identity in agents/tools/__init__.py)

  Preload (app/services/memory_context.py, preload_farmer_profile()):
    - Fires only on a session's first turn (`memory_user_id and not history`)
    - Pulls the structured profile only — episodic memories are recall-tool
      -only, never preloaded
    - Since session_id is NOT mapped to user identity (a farmer can start a
      fresh session at any time), this preload is the only mechanism that
      can carry continuity across visits — session continuity itself is not
      the design's job

  Known gaps (not yet built, no committed timeline):
    - Capture is entirely tool-call-gated — memory.py's own docstring notes
      "no post-session job"; nothing forces consolidation at end of session
    - mem0's additive-only extraction has no season/time boundary — a crop
      change doesn't supersede the old fact, it just adds alongside it
    - If Qdrant/mem0 is unreachable, both services fail silently with a 60s
      retry backoff — memory degrades to nothing with no visible error
    - No farmer-facing view of stored memory; only internal admin/debug
      routes (app/routers/memories.py, app/routers/profile.py), gated by
      INTERNAL_ADMIN_TOKEN
  Full review, live production-log findings, and speculative future use
  cases: see oan_horizon/future_work/memory/README.md and the linked
  artifact there.
============================================================================
                      TOOL CALL INPUT OUTPUT
============================================================================
  Format used by agent:
    - Input  -> tool_name(arguments)
    - Output -> plain text/markdown string returned to the LLM

  1) search_terms
    - Input:
      search_terms(
        term="urea",
        max_results=5,
        threshold=0.7,
        language=Language.ENGLISH  # optional: en / mr / transliteration
      )
    - Output:
      fuzzy-matched glossary rows (en / mr / transliteration) as text

  2) search_documents
    - Input:
      search_documents(
        query="cotton pest control in kharif",
        top_k=10
      )
    - Output:
      "> Search Results for `...` ..."
      (ranked document snippets from Marqo)

  3) search_videos
    - Input:
      search_videos(
        query="drip irrigation setup",
        top_k=3
      )
    - Output:
      "> Videos for `...` ..."
      (video titles/links/snippets)

  4) weather_forecast
    - Input:
      weather_forecast(
        latitude=19.7515,
        longitude=75.7139,
        days=5
      )
    - Output:
      formatted weather forecast text for requested location/date range

  5) weather_historical
    - Input:
      weather_historical(
        latitude=19.7515,
        longitude=75.7139,
        days=5
      )
    - Output:
      formatted historical weather summary text

  6) mandi_prices
    - Input:
      mandi_prices(
        commodity="soybean",
        district="Nashik"
      )
    - Output:
      mandi price rows/summary as formatted text

  7) agri_services
    - Input:
      agri_services(
        latitude=19.7515,
        longitude=75.7139,
        service_type="kvk"
      )
    - Output:
      nearby agricultural services list (name/contact/location)

  8) contact_agricultural_staff
    - Input:
      contact_agricultural_staff(
        latitude=19.7515,
        longitude=73.8567
      )
    - Output:
      staff contact details as formatted text

  9) forward_geocode / reverse_geocode
    - Input:
      forward_geocode(location_name="Pune, Maharashtra")
      reverse_geocode(latitude=18.5204, longitude=73.8567)
    - Output:
      normalized location text + coordinates/address components

  10) fetch_agristack_data
    - Input:
      fetch_agristack_data(ctx)  [uses ctx.deps.farmer_id]
    - Output:
      "> Farmer Information (Agristack) ..."
      (masked farmer profile/location/farm details)

  11) recall_farmer_memory
    - Input:
      recall_farmer_memory(query="cotton pest advice")
    - Output:
      mem0 semantic search results (threshold 0.3, top_k 5) as formatted
      text; falls back to the 3 most recent saved memories on no match;
      "No farmer memory available for this session." if not logged in.
      (Not offered to guests at all — see Tooling surface.)

  12) save_farmer_memory
    - Input:
      save_farmer_memory(memory="Farmer's cotton field near Yavatmal had
        pest issues last kharif")
    - Output:
      mem0 infer=True extraction result — "Saved to farmer memory." or
      "Already saved — nothing new to store." on exact-hash duplicate.
      Additive only: does not supersede a contradicting earlier fact.

  13) edit_farmer_memory
    - Input:
      edit_farmer_memory(memory_id="<id from recall_farmer_memory>",
        new_memory="Farmer switched from cotton to soybean this kharif")
    - Output:
      "Updated farmer memory." after verifying the memory belongs to this
      farmer; "Memory not found for this farmer." otherwise.

  14) delete_farmer_memory
    - Input:
      delete_farmer_memory(memory_id="<id from recall_farmer_memory>")
    - Output:
      "Deleted farmer memory." after ownership check, else not-found text.

  15) update_farmer_profile
    - Input:
      update_farmer_profile(field="crop", value="cotton")
    - Output:
      "Saved profile {field}: {value}." — writes into the structured
      FarmerProfile (Qdrant-as-document-store, no semantic search).

  16) remove_farmer_profile_value
    - Input:
      remove_farmer_profile_value(field="crop", value="cotton")
    - Output:
      "Removed profile {field}: {value}." for an explicit retraction
      ("I no longer grow cotton"), or "No matching profile value found."

  17) get_scheme_status (MahaDBT)
    - Input:
      get_scheme_status(ctx)  [uses ctx.deps.farmer_id]
    - Output:
      "## MahaDBT Scheme Status Information ..."
      (application status summary + masked IDs)

  18) get_scheme_codes / get_scheme_info
    - Input:
      get_scheme_codes()
      get_scheme_info(scheme_code="XYZ123")
    - Output:
      scheme code/details text blocks used by agent response synthesis

  19) analyze_pest_disease_image
    - Input:
      analyze_pest_disease_image(upload_id="pest_5a466793-...")
    - Output:
      Formatted text: bold crop name, bold disease/pest name,
      then preventive and curative sections.
      (calls Mahapocra predict API -> advisory API -> store API)

============================================================================
                      CODE FLOW
============================================================================

main.py
├── app.config → Settings() singleton
├── app.routers.chat
│   ├── app.services.chat
│   │   ├── agents.agrinet → Agent("Vistaar Agent") created
│   │   ├── agents.moderation → Agent("Moderation Agent") created
│   │   ├── agents.models
│   │   │   ├── httpx.AsyncClient (shared, module-level)
│   │   │   ├── ConcurrencyLimiter × 2 (agrinet + moderation)
│   │   │   ├── vLLM OpenAI clients × 2
│   │   │   └── Azure OpenAI client × 1  ← crashes here if creds missing
│   │   └── helpers.langfuse_helper → Langfuse init
│   └── app.utils → Redis helpers (pool not opened yet)
├── app.routers.upload
│   └── app.utils (already cached)
└── ... (other routers, lighter dependencies)


```

