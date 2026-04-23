# Documentation: Query Lifetime (mh-oan-api)

```text
============================================================================
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
│  Model: LLM_MODEL from agents/models.py via env:                   │
│    - LLM_PROVIDER=openai -> OpenAIModel(LLM_MODEL_NAME) + OPENAI_API_KEY│
│    - LLM_PROVIDER=vllm -> OpenAI-compatible INFERENCE_ENDPOINT_URL │
│    - LLM_PROVIDER=azure-openai -> AsyncAzureOpenAI client +        │
│      AZURE_OPENAI_* env vars (deployment name as model id)         │
│  Prompt: agrinet_system.md (+ Jinja context: today_date)           │
│  Settings:                                                         │
│    - max_tokens=8192                                               │
│    - parallel_tool_calls=True                                      │
│    - request_limit=50                                              │
│    - retries=3                                                     │
│    - end_strategy='exhaustive'                                     │
│                                                                    │
│  Support agents:                                                   │
│    - moderation_agent (structured moderation output)               │
│    - suggestions_agent (List[str], 3–5 strings; search_documents   │
│      tool only; parallel_tool_calls=False; retries=1)              │
│                                                                    │
│  Tooling surface (registration order in agents/tools/__init__.py): │
│    - Glossary: search_terms                                        │
│    - Knowledge: search_documents, search_videos                    │
│    - Geo: reverse_geocode, forward_geocode (Mapbox-backed)         │
│    - Weather: weather_forecast, weather_historical                 │
│    - Market: mandi_prices                                          │
│    - Services: agri_services, contact_agricultural_staff           │
│    - Identity/profile: fetch_agristack_data                        │
│    - Schemes: get_scheme_codes, get_scheme_info,                   │
│               get_multiple_schemes_info, get_scheme_status         │
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
│  Post-stream side effect:                                          │
│    - append newly generated messages and persist history in Redis  │
│      under key {session_id}_SVA (see app/utils.py)                 │
└────────────────────────────────────────────────────────────────────┘
============================================================================
                         EXTERNAL INTEGRATIONS
============================================================================

  - LLM PROVIDERS
    - OpenAI (LLM_PROVIDER=openai)
    - vLLM-compatible endpoint (LLM_PROVIDER=vllm)
    - Azure OpenAI (LLM_PROVIDER=azure-openai)

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

  Exact model used:
    - moderation_agent uses model=LLM_MODEL (same resolution as main agent)
    - agents/models.py:
      - LLM_PROVIDER=openai -> OpenAIModel(LLM_MODEL_NAME)
      - LLM_PROVIDER=vllm -> OpenAI-compatible endpoint
      - LLM_PROVIDER=azure-openai -> Azure deployment as model
    - LLM_MODEL_NAME and provider credentials come from environment (currently using gpt-oss-moderator)

  Runtime moderation settings:
    - retries=2
    - temperature=0.1
    - max_tokens=128
    - timeout=5 seconds
    - instrument=True

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

  11) get_scheme_status (MahaDBT)
    - Input:
      get_scheme_status(ctx)  [uses ctx.deps.farmer_id]
    - Output:
      "## MahaDBT Scheme Status Information ..."
      (application status summary + masked IDs)

  12) get_scheme_codes / get_scheme_info / get_multiple_schemes_info
    - Input:
      get_scheme_codes()
      get_scheme_info(code="XYZ123")
      get_multiple_schemes_info(query="drip irrigation subsidy")
    - Output:
      scheme code/details text blocks used by agent response synthesis

```

