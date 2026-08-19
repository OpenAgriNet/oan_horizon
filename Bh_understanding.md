# Documentation: Query Lifetime (bharat-oan-api)

Scope note: bharat-oan-api's canonical aggregate branch is `bh-dev`. All facts below were read directly from `origin/bh-dev` via `git show` (the local working tree was checked out on an unrelated feature branch, `OD-2764_v1`, at the time of writing, and was not used as a source). Where the working branch contains an unmerged change relevant to this document, it is called out explicitly and labeled as unmerged.

```text
============================================================================
             BHARATVISTAAR OAN - BACKEND AGENTIC ARCHITECTURE
                           (bharat-oan-api, branch bh-dev)
============================================================================
                            ┌─────────────────┐
                            │   CALLER/USER   │
                            └────────┬────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               │                     │                     │
      ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
      │ WEB/APP CLIENT  │   │ MOBILE APP      │   │ (no IVR/telephony│
      │ (chat + image)  │   │ (voice utility  │   │  channel found   │
      │                 │   │  endpoints)     │   │  in this repo)   │
      └────────┬────────┘   └────────┬────────┘   └─────────────────┘
               │ HTTP GET/POST       │ POST /transcribe, /tts
               ▼                     ▼ (client stitches voice<->text itself;
┌────────────────────────────────────────────────────────────────────┐    the backend never does STT->chat->TTS in one call)
│      bharat-oan-api / Bharatvistaar AI API (FastAPI :8000)         │
│      uvicorn main:app --workers 8 (supervisord); api_prefix        │
│      from settings (default "/api")                                │
│                                                                    │
│  GET  /                       -> app info (no auth)                │
│  GET  /api/chat/               -> StreamingResponse text/event-    │
│       stream. Query via ChatRequest=Depends(): query, session_id,  │
│       qid, source_lang="hi", target_lang="hi", user_id="anonymous",│
│       latitude, longitude. Auth: Depends(get_current_user) (JWT).  │
│  POST /api/chat/analyze-image  -> DEPRECATED (docstring says use    │
│       /api/image/upload then send image_id in a normal chat msg).  │
│       multipart Form fields; same StreamingResponse shape. Auth: JWT│
│  POST /api/image/upload        -> {"image_id": uuid}. Auth: JWT.   │
│  GET  /api/image/{image_id}    -> FileResponse. NO auth (UUID is   │
│       the capability; used internally by analyze_crop_image tool). │
│  POST /api/transcribe/         -> {status,text,lang_code,session_id}│
│       Body: TranscribeRequest(audio_content, service_type=bhashini │
│       |whisper, session_id, qid). Auth: JWT.                       │
│  POST /api/tts/                -> {status,audio_data(b64),session_id}│
│       Body: TTSRequest(text, target_lang="hi", service_type=       │
│       bhashini|eleven_labs, qid). Auth: JWT. NOTE: schema allows    │
│       "eleven_labs" but the handler 400s on anything != "bhashini" │
│       — ElevenLabs is not implemented despite settings.eleven_labs_│
│       api_key existing in config.                                  │
│  GET  /api/health/, /live, /ready, /master-catalog -> no auth.      │
│  GET  /api/file/{file_hash}    -> cached HTML (e.g. SHC report PDFs)│
│       from Redis via app.core.cache. No auth.                      │
│  POST /api/token, /api/token/api-key, /api/token/play-integrity     │
│       -> JWT issuance (guest / per-client API key / Play Integrity  │
│       attestation). No auth on these (they ARE the auth mechanism). │
│  POST /api/telemetry/feedback, /events, /error -> relay to gov      │
│       observability-service; feedback also writes a Langfuse score.│
│       Auth: JWT.                                                    │
│  (DISABLED) GET /api/suggest/  -> app/routers/suggestions.py exists │
│       and is fully implemented, but main.py comments out both its   │
│       import and its app.include_router() call — not reachable.     │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│              PER-TURN ROUTING + PRE-PROCESSING PIPELINE             │
│              (app/services/chat.py: stream_chat_messages)           │
│  1) Fire "question" telemetry event (background task).              │
│  2) resolve_agrinet_route(session_id, has_history) — see MODEL      │
│     ROUTING LAYER box below. Runs BEFORE moderation, every turn.    │
│  3) Build Langfuse trace metadata/tags (env, channel, model,        │
│     moderation model) via propagate_attributes(); trace_name=       │
│     "bharat-vistaar-chat"; write qid->trace_id into Redis           │
│     (chat_turn_map) so /telemetry/feedback can score this trace     │
│     later.                                                          │
│  4) Build FarmerContext(deps): query, lang_code=target_lang,        │
│     session_id, question_id=qid, latitude, longitude.               │
│  5) format_message_pairs(history, limit=3) -> "**Conversation**"    │
│     block prepended to the user message; find_pending_npss_image_url│
│     checks history for an NPSS tool result still waiting on location│
│  6) Run moderation_agent on the assembled user message (see          │
│     MODERATION section) -> QueryModerationResult; its str() is      │
│     embedded into the user message as "**Moderation Compliance:**   │
│     ..." before the agrinet agent ever sees it.                     │
│  7) trim_history(history, max_tokens=64_000) then                   │
│     filter_thinking_from_history(...) (strips pydantic-ai            │
│     ThinkingPart — vLLM chokes on it being replayed as <think> tags,│
│     "Unknown role: final" errors otherwise).                        │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    PYDANTIC AI AGENT LOOP                           │
│  Main agent: agrinet_agent = Agent(name="Vistaar Agent") in          │
│    agents/agrinet.py. deps_type=FarmerContext, output_type=str,      │
│    retries=3, end_strategy="exhaustive", instrument=False,           │
│    tools=TOOLS (31 tools, agents/tools/__init__.py).                 │
│  model_settings: temperature=0.7, top_p=0.95, max_tokens=4096,       │
│    timeout=120, parallel_tool_calls=True.                            │
│  Model at call time is NOT the agent's static `model=` attribute —   │
│    app/services/chat.py overrides it per-turn via                    │
│    agrinet_agent.run_stream_events(..., model=                       │
│    get_agrinet_route_model(decision.route)) using whatever alias     │
│    the routing layer (below) picked for this session.                │
│  Prompt: assets/prompts/agrinet_{lang_code}.md (10 files: as, bn,     │
│    en, gu, hi, kn, ml, mr, ta, te), Jinja2-rendered fresh EVERY TURN  │
│    via @agrinet_agent.system_prompt(dynamic=True) with context       │
│    {today_date, crop_season, last_weekday_table,                     │
│    vector_schemes_bullets, vector_schemes_identifiers,                │
│    vector_scheme_count} (helpers/utils.get_prompt +                  │
│    helpers/scheme_qdrant_search.format_vector_schemes_prompt_block). │
│    Contrast: the search_schemes TOOL's docstring is frozen ONCE at   │
│    process startup (see TOOL CALL INPUT OUTPUT, search_schemes).     │
│  Support agent: moderation_agent (agents/moderation.py) — fixed      │
│    model (no per-turn override), output_type=PromptedOutput(         │
│    QueryModerationResult), model_settings temperature=0.0, top_p=1.0,│
│    timeout=env LLM_MODERATION_TIMEOUT_SECONDS (default 20s).         │
│  Dead/unwired agent: suggestions_agent (agents/suggestions.py) — its  │
│    router is disabled (see above) and its own import is broken       │
│    (`from agents.models import LLM_AGRINET_MODEL`, which does not    │
│    exist in agents/models.py — only AGRINET_MODEL does). Only        │
│    reachable via app/tasks/suggestions.py, which nothing imports.    │
│  Instrumentation: agents/__init__.py calls Agent.instrument_all(     │
│    False) globally — pydantic-ai's own OpenTelemetry auto-trace is   │
│    off; all tracing is manual Langfuse @observe spans                │
│    (chain.chat -> agent.moderation / agent.vistaar -> tool:*).        │
│  Turn timeout: asyncio.timeout(registry.get_timeout("agrinet")) =    │
│    45s (config/models.yaml). Note: registry.get_timeout("moderation")│
│    (=20s in yaml) is defined but never called anywhere — moderation's│
│    real timeout comes only from its own ModelSettings.timeout above. │
│  History passed as message_history=trimmed_history (pydantic-ai      │
│    ModelMessage list), not re-summarized.                            │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DELIVERY LAYER                                │
│  Streaming: agrinet_agent.run_stream_events() emits PartStartEvent /  │
│    FinalResultEvent / PartDeltaEvent / AgentRunResultEvent; chat.py's │
│    _run_agrinet_once_streaming state machine strips <think> blocks   │
│    live and pushes visible text chunks into an asyncio.Queue that    │
│    the router yields as raw SSE text (media_type="text/event-stream",│
│    no JSON envelope, no "data:" framing added in this layer).         │
│  NPSS image-analysis answers are NOT streamed token-by-token — they  │
│    are buffered (defer_npss_output) and yielded as one final block    │
│    after post_process_npss_response() runs (per-language label        │
│    localization + "**Source:** NPSS" line handling).                  │
│  Client disconnect: a client hang-up does not kill the in-flight      │
│    agent run — chat.py detaches it (_spawn_detached) and lets it       │
│    finish for up to 180s so history/telemetry are still recorded.     │
│  Post-turn side effects (on success): update_message_history(session_ │
│    id, [...history, new pydantic-ai messages with the post-processed  │
│    text swapped in]) -> Redis key sva-cache-{session_id}__SVA (2h     │
│    TTL); refresh_session_agrinet_route_ttl() extends the sticky-route │
│    key's TTL; "answer" telemetry event queued; get_client().flush()   │
│    (Langfuse). On error: an "error" telemetry event is queued and the │
│    in-flight agent task is cancelled.                                 │
│  Voice: NOT part of this pipeline. /api/transcribe/ and /api/tts/     │
│    are separate, stateless, non-streaming JSON endpoints the CLIENT   │
│    calls independently (speech-to-text before calling /api/chat/,    │
│    text-to-speech after receiving the SSE answer). There is no        │
│    server-side voice-in/voice-out orchestration around the chat loop. │
└────────────────────────────────────────────────────────────────────┘

============================================================================
                         EXTERNAL INTEGRATIONS
============================================================================
  - LLM PROVIDERS: gemma_vllm (self-hosted vLLM OpenAI-compatible server,
    AGRINET_GEMMA_BASE_URL/MODEL_NAME/API_KEY env vars) and azure_gpt41
    (Azure OpenAI, AZURE_OPENAI_DEPLOYMENT_NAME/ENDPOINT/API_KEY/
    API_VERSION), both defined in config/models.yaml. A third alias,
    bharat_ai_grid_gemma (kind bharat_ai_grid, BHARAT_AI_GRID_BASE_URL/
    MODEL_NAME/API_KEY), is configured but not wired into any use_case.
  - VECTOR SEARCH — TWO separate stores, for different purposes (this
    corrects an earlier assumption that only Marqo was in use):
      * Marqo (`marqo.Client(url=MARQO_ENDPOINT_URL)`, package marqo==
        3.18.2) — used directly inside agents/tools/search.py for
        search_documents (index MARQO_INDEX_NAME, default
        "sunbird-va-index") and search_pests_diseases (index
        MARQO_PESTS_DISEASES_INDEX_NAME). Hybrid search
        (retrievalMethod=disjunction, rankingMethod=rrf, alpha=0.5,
        rrfK=60).
      * Qdrant (`qdrant_client.QdrantClient`, package qdrant-client==
        1.18.0, embeddings via sentence-transformers==5.6.1 model
        "intfloat/multilingual-e5-large") — helpers/scheme_qdrant_search.py
        (collection "schemes-index" / settings.qdrant_collection_name) and
        helpers/video_qdrant_search.py (collection "video_data_collection"
        / settings.qdrant_video_collection_name, eNAM training videos).
        video search (search_video tool) genuinely queries Qdrant directly
        in-process. Scheme search is more layered: this module's own
        module-level `search_schemes()` function (direct Qdrant
        `query_points`) is DEFINED but never called by anything else in
        the repo — the actual `search_schemes` TOOL (agents/tools/
        search.py) instead POSTs a Beckn-style `/search` request to
        `BAP_ENDPOINT` (category `scheme-agri-qdrant`) and only borrows
        this module's `format_search_results` / `resolve_scheme_code` /
        `get_builtin_scheme_list` / `format_scheme_unavailable` /
        `query_names_unindexed_scheme` for routing/formatting the network
        response. The direct-Qdrant `search_schemes()` path appears
        dormant/legacy for production tool calls.
    main.py's lifespan pre-warms the embedder (`warm_scheme_search()`,
    only if settings.qdrant_url is set) so the first real search_schemes
    call isn't a cold start.
  - NETWORK / BAP LAYER (Beckn-ONDC-style protocol): the majority of
    "scheme status" and grievance tools (get_scheme_info,
    call_maha_vistaar_network, PM-KISAN/PMFBY/SHC/SMAM status &
    grievance flows, search_schemes, weather_forecast, get_mandi_prices,
    gfr_get_crop_registries/recommendations, search_sathi_seed_
    availability) POST to a `BAP_ENDPOINT` env var using `/search`,
    `/init`, `/status` actions with `context.domain` values like
    "schemes:vistaar" and provider/category codes per scheme (e.g.
    "pmfby-agri", "smam", "gfr-agri", "sathi-seed", "price-discovery",
    category code "WFC" for weather). This is the same Beckn-based
    cross-network pattern used by mh-oan-api's BAP integration.
  - GEO: Photon geocoder (self-hosted, PHOTON_HOST env, bounded to
    INDIA_BBOX [68.0, 6.0, 98.0, 36.0]) for forward_geocode/
    reverse_geocode; NPSS image analysis uses app/core/npss_geocodes.py
    to resolve browser lat/long to NPSS location IDs, falling back to
    Krishi Vigyan Kendra, Delhi when coordinates are absent.
  - VOICE / LANGUAGE: Bhashini (dhruva-api.bhashini.gov.in/services/
    inference/pipeline, auth via MEITY_API_KEY_VALUE) is the primary ASR
    (transcribe_bhashini + detect_audio_language_bhashini for automatic
    language detection before transcription), TTS (text_to_speech_
    bhashini, indictrans-v3 style service IDs, hardcoded gender="female",
    sampling_rate=8000) and translation (BhashiniTranslator,
    "bhashini/ai4bharat/indictrans-v3") backend. OpenAI Whisper
    ("whisper-1") is a secondary ASR option (service_type="whisper",
    self-detects language). helpers/translation.py also contains an
    unused/alternate GoogleTranslator (google.cloud.translate_v2). No
    Sarvam or ElevenLabs code exists despite settings.sarvam_api_key and
    settings.eleven_labs_api_key existing as config fields — both are
    dead config.
  - NPSS (National Pest Surveillance System): agents/tools/npss.py calls
    NPSS_BASE_URL (default "https://npss.dac.gov.in/api3.0")
    `/api/Vistaar/token` then `/api/Vistaar/analyze-image` for crop image
    pest/disease analysis; images are uploaded to /api/image/upload first
    (app/core/image_storage.py) and only a URL is ever passed to the LLM.
  - GOVERNMENT TELEMETRY: helpers/telemetry.py implements a Sunbird/
    ekstep-style telemetry schema (`TelemetryRequest.id = "ekstep.
    telemetry"`) posted to settings.telemetry_api_url (default
    "https://dev-vistaar.da.gov.in/observability-service/action/data/v3/
    telemetry") with either a static bearer token or a hand-rolled
    HS256-signed JWT (telemetry_auth_key/secret), retried up to 3x via
    tenacity. Question/answer/error events, ASR/TTS/ALD (audio language
    detection) events, and UI-interact events all funnel through this.
  - AUTH PROVIDERS beyond plain JWT: Google Play Integrity attestation
    (app/routers/token.py, Google service-account credentials, calls
    playintegrity.googleapis.com) and per-client static API keys
    (X-API-Key header, env var {API_KEY_AUTH_TOKEN_PREFIX}{CLIENT_CODE})
    — both are alternate ways to MINT a first-party JWT, not alternate
    verification schemes; every authenticated route still verifies that
    minted JWT the same way (app/auth/jwt_auth.py).
  - OBSERVABILITY: Langfuse (langfuse==4.14.1, OTel-based client ≥3.x),
    initialized once in helpers/langfuse_helper.py from settings.langfuse_
    public_key/secret_key/host. Trace shape (helpers/langfuse_trace_
    schema.py): chain.chat -> agent.moderation / agent.vistaar -> tool:*.
    User thumbs-up/down feedback (POST /api/telemetry/feedback) is
    attached as a Langfuse "user-feedback" categorical score on the
    original chat trace (helpers/langfuse_scores.py, idempotent per-qid
    upsert), correlated via a Redis join map (app/services/chat_turn_
    map.py, key "chat_turn:{qid}") written while the trace is still live.
============================================================================
                           MODERATION
============================================================================
  Prompt file: assets/prompts/moderation_system.md — a full policy doc
  ("BharatVistaar Query Moderation Policy") with 8 categories
  (valid_agricultural, invalid_non_agricultural, invalid_external_
  reference, invalid_compound_mixed, invalid_language, unsafe_illegal,
  political_controversial, role_obfuscation), an explicit priority order
  when multiple apply (unsafe_illegal > role_obfuscation > political_
  controversial > invalid_compound_mixed > invalid_external_reference >
  invalid_non_agricultural > invalid_language > valid_agricultural), and
  a hard-coded list of 10 supported response languages (English, Hindi,
  Bengali, Marathi, Tamil, Telugu, Kannada, Gujarati, Malayalam, Assamese)
  used to detect "invalid_language" requests.
  Model: moderation_agent (agents/moderation.py) uses MODERATION_MODEL =
  registry.get_model(registry.get_default_alias("moderation")) =
  azure_gpt41 — fixed, no per-turn override, no routing/weighting (the
  "moderation" use case in config/models.yaml has exactly one alias).
  model_settings: temperature=0.0, top_p=1.0, timeout=env
  LLM_MODERATION_TIMEOUT_SECONDS (default 20.0s). retries=2.
  Structured output: output_type=PromptedOutput(QueryModerationResult)
  where QueryModerationResult is a pydantic model with
  category: Literal[the 8 values above] and action: str ("Action to
  take on the query, always in English"). Its __str__ renders as
  "**Moderation Compliance:** {action} ({Category Title Case})" — this
  exact string is what gets embedded into the user message sent to
  agrinet_agent, not a separate side-channel.
  Invocation in the request flow: app/services/chat.py's _run_moderation
  runs BEFORE the agrinet agent, on the already-built user_message
  (query + selected-language line + any location line, per
  FarmerContext.get_user_message()) — i.e. moderation sees the same
  text agrinet would, minus the moderation line itself (which doesn't
  exist yet). Traced as a Langfuse "agent.moderation" span
  (helpers/langfuse_trace_schema.AGENT_MODERATION). After moderation
  runs, chat.py rebuilds user_message a second time with
  deps.update_moderation_str(str(moderation_data)) included, and that
  final version — not the pre-moderation one — is what agrinet_agent
  actually receives. Separately, propagate_attributes(tags=[moderation_
  data.category]) tags the whole downstream Langfuse trace with the
  moderation category for dashboard filtering.
============================================================================
                      TOOL CALL INPUT OUTPUT
============================================================================
All 31 tools are plain Python functions (NOT `@agrinet_agent.tool`-
decorated) wrapped as `pydantic_ai.Tool(fn, takes_ctx=<bool>, strict=
False)` in the module-level TOOLS list in agents/tools/__init__.py, in
the exact order below; each function itself carries a Langfuse
`@observe(name="tool:<name>", as_type="tool")` decorator instead.
agents/agrinet.py does `Agent(..., tools=TOOLS, ...)`. Every tool's
docstring becomes part of the tool-calling JSON schema pydantic-ai sends
the model.

1. get_scheme_info(ctx, scheme_name: Literal["kcc","pmkisan","pmfby",
   "shc","pmksy","sathi","pmasha","aif","smam","pdmc","pkvy","nfsm",
   "rad","ffs","nbm","nbhm"]) -> str
   Example: get_scheme_info(ctx, scheme_name="pmkisan")
   Calls Beckn /search on BAP_ENDPOINT, category "schemes-agri". Output
   starts with the literal "**Source:** Government Scheme Information"
   then "## {tag name}" / value blocks; "No scheme data found." if empty.
   For "pmkisan" specifically, appends a PM-KISAN 23rd-installment
   release-date note from helpers/pmkisan_installment_release.py.

2. call_maha_vistaar_network(ctx, scheme_code: str) -> str
   Example: call_maha_vistaar_network(ctx, scheme_code="ndksp-drip-irrigation")
   Beckn /search, domain "schemes:vistaar", category "schemes-agri" —
   the BH-side counterpart of mh-oan-api's bharat_vistaar cross-network
   tool. Output: "**Source:** Government Scheme Information" + "## name"
   blocks, or "No scheme data found for this scheme."

3. initiate_pm_kisan_status_check(ctx, reg_no="", phone_number="") -> str
   Example: initiate_pm_kisan_status_check(ctx, reg_no="MH01234567890")
   Beckn /init. Returns joined response text, or fallback "OTP request
   processed. Please check your mobile for the OTP."

4. check_pm_kisan_status_with_otp(ctx, otp, reg_no="", phone_number="") -> str
   Example: check_pm_kisan_status_with_otp(ctx, otp="1234", reg_no="MH01234567890")
   Beckn /status. Output lines like "Order ID / OTP: {id}", "State:
   **{state}**", "Provider: **{provider}**".

5. initiate_pmfby_status_check(ctx, phone_number) -> str
   Example: initiate_pmfby_status_check(ctx, phone_number="9876543210")
   Beckn /init (provider.id="pmfby-agri"). Fallback text: "OTP has been
   sent to your registered mobile. Please enter the OTP you received to
   see your policy/claim status."

6. check_pmfby_status_with_otp(ctx, otp, phone_number, inquiry_type:
   Literal["policy_status","claim_status"], year, season:
   Literal["Kharif","Rabi","Summer"]) -> str
   Example: check_pmfby_status_with_otp(ctx, otp="123456",
   phone_number="9876543210", inquiry_type="policy_status", year="2025",
   season="Kharif")
   Beckn /status. Empty-result literal: "No {policy|claim} record found
   for {year} {season}."

7. check_shc_status(ctx, phone_number, cycle) -> str
   Example: check_shc_status(ctx, phone_number="9876543210", cycle="2024-25")
   Beckn /init (provider.id="shc-discovery"); decodes base64 HTML
   report attachments, converts to markdown, caches at
   "{API_BASE_URL}/api/file/{hash}". Output is the converted markdown
   suffixed "\n\nOpen full report: {link}", or "No data available."

8. pmkisan_grievance_send_otp(ctx, reg_no, phone_number="", purpose:
   Literal["submit_grievance","check_status"]="submit_grievance") -> str
   Example: pmkisan_grievance_send_otp(ctx, reg_no="MH01234567890")
   Beckn /init. Returns OTP confirmation text or an error string.

9. check_smam_scheme_status(ctx, search_type: Literal["application_no",
   "mobile"], search_value) -> str
   Example: check_smam_scheme_status(ctx, search_type="mobile",
   search_value="9876543210")
   Beckn /search (provider.id="smam"). Output: "## Application /
   reference: {app_label}", "### Implement: {impl_name}", status-history
   bullets; failure literal "{status}. {message}" or "No application
   data found for the details provided."

10. pmkisan_submit_grievance(ctx, reg_no, grievance_description,
    grievance_type: Literal[dynamic from assets/grievance_types.json,
    e.g. "ACCOUNT_NUMBER_NOT_CORRECT", "INSTALLMENT_NOT_RECEIVED",
    "TRANSACTION_FAILED", "PROBLEM_IN_AADHAAR_CORRECTION", "GENDER_NOT_
    CORRECT", "PAYMENT_RELATED", "PROBLEM_IN_OTP_BASED_EKYC", "PROBLEM_
    IN_BIO_METRIC_BASED_EKYC", "PROBLEM_IN_FACIAL_BASED_EKYC",
    "ONLINE_APPLICATION_PENDING_FOR_APPROVAL"], otp=None,
    phone_number="", raw=False) -> str
    Example: pmkisan_submit_grievance(ctx, reg_no="MH01234567890",
    grievance_description="Payment not received", grievance_type=
    "INSTALLMENT_NOT_RECEIVED", otp="1234")
    Re-verifies OTP via Beckn /status, then Beckn /init to submit.
    Output: grievance submission result text or an OTP-verification
    error message.

11. pmkisan_grievance_status(ctx, reg_no="", raw=False, otp=None,
    phone_number="") -> str
    Example: pmkisan_grievance_status(ctx, reg_no="MH01234567890", otp="1234")
    OTP verify then Beckn /search. Output: grievance status summary text.

12. initiate_pmfby_grievance_otp(ctx, phone_number) -> str
    Example: initiate_pmfby_grievance_otp(ctx, phone_number="9876543210")
    Beckn /init. Success literal: "OTP has been sent to the registered
    mobile number. Please share the 6-digit OTP to proceed with
    grievance lodging."

13. check_pmfby_grievance_otp(ctx, otp, phone_number) -> str
    Example: check_pmfby_grievance_otp(ctx, otp="123456", phone_number="9876543210")
    Beckn /status. Success literal: "OTP verified. Please share your
    PMFBY application number…"; failure literal: "OTP verification
    failed. Please re-check the OTP and try again."

14. pmfby_grievance_status(ctx, phone_number, grievance_support_ticket_no) -> str
    Example: pmfby_grievance_status(ctx, phone_number="9876543210",
    grievance_support_ticket_no="TCK123456")
    Beckn /status. Output: "{name}: {value}" lines, or "No grievance
    status found for this ticket."

15. pmfby_submit_grievance(ctx, otp, phone_number, receipt_source_id,
    request_year, request_season, application_no, grievance_description) -> str
    Example: pmfby_submit_grievance(ctx, otp="123456",
    phone_number="9876543210", receipt_source_id="134306",
    request_year="2025", request_season="Kharif",
    application_no="APP123456", grievance_description="Claim not settled")
    Beckn /init (provider.id="pmfby-grievance"). NOTE: whatever
    receipt_source_id the model passes is force-overridden internally to
    the hardcoded constant "134306". Output: "Status: {status}",
    "Ticket Number: {ticket_no}", "Ticket ID: {ticket_id}", "Message:
    {message}".

16. search_terms(term, max_results=5, threshold=0.7, language:
    Language|None=None) -> str
    Example: search_terms(term="beej", language=Language.TRANSLITERATION)
    No network call — rapidfuzz.fuzz.ratio over an in-memory glossary
    loaded from assets/glossary_terms.json. Output prefix: "Matching
    Terms for `{term}`\n\n" then "{en} -> {hi} ({translit}) [{score}%]"
    lines; no-match literal "No matching terms found for `{term}`".

17. search_documents(query, top_k=10) -> str
    Example: search_documents(query="drip irrigation subsidy eligibility")
    Marqo hybrid search, index "sunbird-va-index" (MARQO_INDEX_NAME).
    No-hit literal "No results found for `{query}`"; hits prefixed
    "> Search Results for `{query}`\n\n", each hit rendered as
    "**{name}**\n```\n{text}\n```\n" (or a markdown-link title for
    videos), joined by "\n\n----\n\n".

18. search_schemes(ctx, query, top_k=10) -> str
    Example: search_schemes(ctx, query="premium subsidy under PMFBY", top_k=5)
    Beckn /search on BAP_ENDPOINT, category "scheme-agri-qdrant" (see
    VECTOR SEARCH above for the local-vs-network nuance). Its own
    docstring contains a "PLACEHOLDER_SCHEME_CODES" token that is
    replaced ONCE, at process import time, with the live Qdrant scheme-
    code list (format_qdrant_scheme_codes_for_doc()) — logged as
    "STARTUP: search_schemes tool docstring frozen with scheme codes:
    %s". This is deliberately frozen (unlike the system prompt, which
    re-renders the equivalent scheme list every turn) — a scheme synced
    into Redis after process start won't appear in this tool's schema
    until the next restart. Output via format_search_results(): header
    "> Scheme Search Results for `{query}`\n\n**Source: {source}**\n\n"
    then result blocks; unindexed-scheme literal "**Scheme not available
    right now.**\n\n".

19. search_video(query, top_k=10) -> str (docstring says default 3;
    actual code default is 10 — a stale docstring)
    Example: search_video(query="how to prune mango trees")
    Direct Qdrant query against QDRANT_VIDEO_COLLECTION_NAME (default
    "video_data_collection") via helpers/video_qdrant_search.py. Output:
    "> Videos for `{query}`\n\n" + "**[{name}]({source})** (score=
    {score:.4f})\n```\n{text}\n```" blocks; "No videos found for
    `{query}`" if empty.

20. search_pests_diseases(query, top_k=10) -> str
    Example: search_pests_diseases(query="yellowing leaves wheat")
    Marqo hybrid search, index MARQO_PESTS_DISEASES_INDEX_NAME. No-hit
    literal "No pests or diseases information found for `{query}`";
    hits prefixed "> Pests & Diseases Search Results for `{query}`\n\n".

21. weather_forecast(ctx, latitude, longitude) -> str
    Example: weather_forecast(ctx, latitude=18.5204, longitude=73.8567)
    Beckn /search, category descriptor {"name": "Weather-Forecast-
    Mausamgram", "code": "WFC"} (IMD-sourced). Output prefix:
    "**Weather Forecast Data** [Today's Date: {date}]" then "Responses:"
    + provider/item text, or "No weather forecast data found for the
    requested location."

22. get_mandi_prices(ctx, latitude, longitude, location_name,
    commodity_name, price_date=None, price_date_to=None) -> str
    Example: get_mandi_prices(ctx, latitude=26.9124, longitude=75.7873,
    location_name="Jaipur", commodity_name="Onion", price_date="01-07-2026")
    Beckn /search, category "price-discovery", paginates up to 10 pages
    backward. Output header literal "**Mandi Price Discovery**" plus a
    bracketed date qualifier, then per-item "Commodity/Market/Price/
    Arrival Date" blocks joined by "\n---\n"; no-data literal "No mandi
    price data found for the requested location and commodity."

23. search_commodity(query, max_results=5, threshold=0.7) -> str
    Example: search_commodity(query="pyaz", max_results=3)
    No network call — rapidfuzz over assets/commodity_codes.json (AGMKT
    commodity codes). Output: a markdown table "| Commodity | Matched
    Term (Score) | Code |"; no-match literal "No commodity matches
    found for `{query}`".

24. forward_geocode(place_name) -> str
    Example: forward_geocode(place_name="Pune, Maharashtra")
    Photon geocoder GET /api, bounded to India's bbox. Output:
    "{place_name} (Latitude: {lat}, Longitude: {lon})", or "No location
    found for '{place_name}'. Please check the spelling or try a
    different location name."

25. reverse_geocode(latitude, longitude) -> Optional[Location]
    Example: reverse_geocode(latitude=18.5204, longitude=73.8567)
    Photon geocoder GET /reverse. Unlike almost every other tool here,
    this returns an actual pydantic Location object (latitude,
    longitude, place_name), not a plain string — pydantic-ai serializes
    the model directly. Falls back to place_name="Unknown Location" on
    any error rather than raising.

26. gfr_get_crop_registries(ctx, latitude, longitude,
    only_gfr_available=True, crop_name_contains=None, limit=25) -> str
    Example: gfr_get_crop_registries(ctx, latitude=26.9, longitude=75.8,
    crop_name_contains="wheat")
    Beckn /search, provider.id="gfr-agri", items=[{"id":"gfr-agri-crop-
    registy"}]. Output header "Crops (id - name - stateId - districtId -
    season - irrigation - GFR):" then dash-rows; "No crops found." /
    "No crops matched your filter." on empty.

27. gfr_get_recommendations(ctx, state_id, crops: List[str], phone_no,
    cycle, district_id=None, natural_farming=False, latitude=None,
    longitude=None) -> str
    Example: gfr_get_recommendations(ctx, state_id="STATE0009",
    crops=["CROP001"], phone_no="9876543210", cycle="2025-26")
    Beckn /search, items=[{"id":"gfr-agri-crop-recommendation"}]. Output
    header "Fertilizer recommendation:" then per-crop dosage/organic-
    input bullets; "No recommendation data found." on empty.

28. get_sathi_crop_groups() -> str (no ctx, no params)
    Example: get_sathi_crop_groups()
    GET {SATHI_MASTER_BASE}/get-crop-group, cached 7 days. Output header
    "SATHI crop groups (use group_code with list_sathi_crops_in_group):"
    then "- group_code={gc} | group_name={gn}" rows.

29. list_sathi_crops_in_group(group_code) -> str
    Example: list_sathi_crops_in_group(group_code="A02")
    GET {SATHI_MASTER_BASE}/get-crops-list?...&group_code=.... Output
    header "SATHI crops in group {gc} (pick crop_code for
    search_sathi_seed_availability):" then "- crop_code=... |
    crop_name=..." rows.

30. search_sathi_seed_availability(ctx, crop_code, latitude, longitude) -> str
    Example: search_sathi_seed_availability(ctx, crop_code="A0201",
    latitude=26.9, longitude=75.8)
    Beckn /search, provider.id="sathi-seed". Output per-dealer blocks
    (name/district/contact/stock/variety); every successful response
    ends with the fixed literal footer "**Source: SATHI**"; no-stock
    variant: "Data is not available for certified seed stock in
    {place}.\n\n**Source: SATHI**".

31. analyze_crop_image(ctx, image_url, location=None) -> str
    Example: analyze_crop_image(ctx, image_url="https://.../api/image/
    3fa85f64-5717-4562-b3fc-2c963f66afa6")
    `location` is a deprecated no-op argument — ctx.deps.latitude/
    longitude (backend-trusted browser coordinates) are used instead,
    with a Krishi Vigyan Kendra, Delhi fallback when absent. Downloads
    the image bytes from the URL, then calls NPSS_BASE_URL (default
    "https://npss.dac.gov.in/api3.0") `/api/Vistaar/token` then
    `/api/Vistaar/analyze-image`. Output header literal "**NPSS Analysis
    Result**", ordered fields (errors, pest, crop, pathogenClass,
    description) as "**{key}:** {value}", ending with the fixed literal
    footer "**Source:** NPSS". Pre-flight literals include "No image URL
    was provided. Please upload a clear photo of the affected crop or
    plant part first." and per-format rejection messages (e.g. WebP not
    supported).

Common private helper libraries behind these tools (not tools
themselves): agents/tools/pmfby_scheme_status.py's
normalize_phone_for_api() (Indian phone normalization, reused by gfr.py);
helpers/encryption.py (AES-GCM, used by the PM-KISAN grievance flow);
helpers/inject_pdf_header.py (adds a client-side "Download PDF" button to
cached HTML, used by the SHC report flow alongside app/routers/file.py).
============================================================================
                      CODE FLOW
============================================================================
main.py
├── load_dotenv(); logging.basicConfig(level=settings.log_level)
├── app.config → Settings() singleton (pydantic-settings, .env-backed)
├── app.core.cache → cache = aiocache.Cache(Cache.REDIS, ...) module-level
├── agents.models.validate_agrinet_routing_config (called in lifespan(),
│   after token.validate_multi_provider_auth_config())
│   └── agents.model_registry.get_registry() → ModelRegistry()
│       ├── config/models.yaml (parsed once; "${VAR}" resolved from os.environ)
│       └── per-alias lazy build → pydantic_ai.models.openai.OpenAIChatModel
│           via openai.AsyncAzureOpenAI (azure-openai) or
│           pydantic_ai.providers.openai.OpenAIProvider (vllm/bharat_ai_grid/openai)
├── app.routers.chat (router; prefix "/chat")
│   ├── app.auth.jwt_auth.get_current_user (Depends; RS256, public key
│   │   loaded once at import from settings.jwt_public_key_path)
│   ├── app.models.requests.ChatRequest
│   ├── app.routers.chat_query_utils (normalize_chat_query, get_session_history,
│   │   prepare_image_analyze_payload)
│   │   └── app.utils._get_message_history → app.core.cache
│   └── app.services.chat.stream_chat_messages (StreamingResponse, text/event-stream)
│       ├── agents.agrinet.agrinet_agent → pydantic_ai.Agent(...) created
│       │   ├── agents.models.AGRINET_MODEL (static default; overridden per
│       │   │   call via model=get_agrinet_route_model(route))
│       │   ├── agents.tools.TOOLS (31 Tool(...) wrappers; see catalog above)
│       │   ├── agents.deps.FarmerContext (deps_type)
│       │   └── helpers.utils.get_prompt('agrinet_{lang}') + Jinja2
│       │       └── helpers.scheme_qdrant_search.format_vector_schemes_prompt_block
│       │           └── helpers.master_catalog.get_master_catalog_snapshot (Redis)
│       ├── agents.moderation.moderation_agent → pydantic_ai.Agent(...) created
│       │   ├── agents.models.MODERATION_MODEL (fixed, azure_gpt41)
│       │   └── helpers.utils.get_prompt('moderation_system')
│       ├── app.services.agrinet_routing
│       │   ├── resolve_agrinet_route / get_alternate_agrinet_route /
│       │   │   set_session_agrinet_route / refresh_session_agrinet_route_ttl
│       │   ├── app.utils.get_cache/set_cache → app.core.cache (Redis)
│       │   └── httpx.AsyncClient (ad hoc, per-call) → vLLM /metrics scraping
│       ├── app.services.chat_turn_map (qid -> trace_id Redis join map)
│       ├── app.services.npss_response.post_process_npss_response
│       ├── app.core.npss_followup.find_pending_npss_image_url
│       ├── app.tasks.telemetry.send_telemetry
│       │   └── helpers.telemetry (event builders) → httpx POST to
│       │       settings.telemetry_api_url (tenacity retry x3)
│       ├── app.utils (trim_history, filter_thinking_from_history,
│       │   update_message_history, format_message_pairs)
│       └── helpers.langfuse_tracing / helpers.langfuse_trace_schema
│           └── helpers.langfuse_helper → langfuse.Langfuse() singleton
├── app.routers.transcribe → helpers.transcription (Bhashini + OpenAI Whisper)
├── app.routers.tts → helpers.tts (Bhashini only; eleven_labs rejected at runtime)
├── app.routers.health → helpers.master_catalog, helpers.scheme_qdrant_search
├── app.routers.file → app.core.cache (serves cached SHC-report HTML)
├── app.routers.token → Google Play Integrity client, per-client API keys,
│   private_key.pem-based JWT issuance (app.auth counterpart: public key only)
├── app.routers.telemetry → app.services.chat_turn_map, helpers.langfuse_scores
├── app.routers.image → app.core.image_storage (upload/serve; used internally
│   by agents.tools.npss.analyze_crop_image)
└── app.routers.suggestions — NOT mounted (import + include_router both
    commented out in main.py); agents.suggestions.suggestions_agent has a
    broken import (LLM_AGRINET_MODEL does not exist in agents.models) and
    is unreachable in practice.

Individual tool modules (agents/tools/*.py) each independently import:
httpx.AsyncClient (per-call, not a shared module-level client — unlike
mh-oan-api's shared client pattern), plus one of: marqo.Client
(search.py), qdrant_client.QdrantClient (search.py's search_video path,
via helpers/video_qdrant_search.py), openai.OpenAI (helpers/
transcription.py's Whisper path), or Beckn BAP_ENDPOINT calls (the
majority of scheme/grievance/weather/mandi/GFR/SATHI tools).
```

**Key files referenced** (all read from `origin/bh-dev`): `/mnt/raid/gautam/bharat-oan-api/main.py`, `app/config.py`, `app/routers/{chat,chat_query_utils,transcribe,tts,health,file,token,telemetry,image,suggestions}.py`, `app/auth/jwt_auth.py`, `app/models/{requests,responses}.py`, `app/services/{chat,agrinet_routing,chat_turn_map,npss_response}.py`, `app/utils.py`, `app/core/{cache,image_storage,npss_followup,master_catalog}.py`, `agents/{agrinet,moderation,models,model_registry,deps,suggestions}.py`, `agents/tools/__init__.py` and all 17 tool files, `config/models.yaml`, `assets/prompts/{moderation_system,agrinet_*}.md`, `helpers/{scheme_qdrant_search,video_qdrant_search,translation,tts,transcription,telemetry,langfuse_helper,langfuse_tracing,langfuse_trace_schema,langfuse_scores,utils}.py`, `requirements.txt`, `.env.example`, `docker-compose.yml`, `supervisord.conf`.
