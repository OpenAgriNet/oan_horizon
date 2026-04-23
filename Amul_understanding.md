```

  ============================================================================
                AMUL OAN — BACKEND AGENTIC ARCHITECTURE
                 (voice-oan-api + amul-oan-api)
  ============================================================================


                             ┌─────────────────┐
                             │   CALLER/USER    │
                             └────────┬────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
       ┌────────▼────────┐   ┌───────▼───────┐   ┌────────▼────────┐
       │  RAYA TELEPHONY │   │ WEB/APP CLIENT │   │  WHATSAPP/SMS   │
       │  (IVR Provider) │   │   (React/Next) │   │   (future)      │
       └────────┬────────┘   └───────┬───────┘   └─────────────────┘
                │ STT audio → text   │ HTTP
                │ process_id=N       │
                ▼                    ▼
  ┌──────────────────────┐  ┌──────────────────────┐
  │   voice-oan-api      │  │   amul-oan-api       │
  │   (FastAPI :8003)    │  │   (FastAPI :8000)     │
  │                      │  │                       │
  │  GET /api/voice/     │  │  GET /api/chat/       │
  │  StreamingResponse   │  │  SSE StreamingResponse│
  │  (text/plain)        │  │  (text/event-stream)  │
  └──────────┬───────────┘  └──────────┬────────────┘
             │                         │
             ▼                         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                     AUTH LAYER (both services)               │
  │                                                              │
  │  JWT (RS256) ──► get_current_user()                          │
  │  FCM (chat only) ──► Firebase service account verification   │
  │  CORS: configurable origins (default "*")                    │
  │  Rate limit: 1000 req/min                                    │
  └──────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │               SESSION MANAGEMENT (Redis)                     │
  │                                                              │
  │  ┌─────────────────────────────────────────────────────┐     │
  │  │ Redis (localhost:6379, pool=100)                     │     │
  │  │                                                     │     │
  │  │  {session_id}_SVA           → ModelMessage[] (24h)  │     │
  │  │  {session_id}_active_request → ownership token(120s)│     │
  │  │  {session_id}_request_epoch → counter (staleness)   │     │
  │  │  ai_call_booked:{session_id} → cooldown flag (30m)  │     │
  │  │  farmer_cache:{mobile}      → farmer JSON (17 days) │     │
  │  └─────────────────────────────────────────────────────┘     │
  │                                                              │
  │  Session ownership (voice): claim → refresh(15s) → release   │
  │  Prevents concurrent requests on same session                │
  │  History: Pydantic AI ModelMessage[] (JSON serialized)       │
  └──────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │              PRE-PROCESSING PIPELINE                         │
  │                                                              │
  │  ┌─── VOICE PATH ────────────────────────────────────────┐   │
  │  │                                                       │   │
  │  │  1. STT Signal Detection (stt_signals.py)             │   │
  │  │     └─ "*No audio*", unclear speech → retry/hangup    │   │
  │  │     └─ STT_SIGNAL_RETRY_CEILING=3 (configurable)     │   │
  │  │                                                       │   │
  │  │  2. Greeting Short-Circuit (_is_bare_greeting)        │   │
  │  │     └─ "hello","હલો","નમસ્તે" → canned response      │   │
  │  │     └─ Skipped when translation pipeline active       │   │
  │  │                                                       │   │
  │  │  3. Fragment Short-Circuit (_is_fragment_query)        │   │
  │  │     └─ ≤3 chars → "please repeat"                    │   │
  │  │                                                       │   │
  │  │  4. Query Pre-Translation (when pipeline enabled)     │   │
  │  │     └─ Gujarati → English via GPT-5.1                │   │
  │  │     └─ Confidence scoring: high/medium/low            │   │
  │  │     └─ Low confidence → "please repeat" (no LLM)     │   │
  │  │     └─ Fallback: TranslateGemma structured            │   │
  │  └───────────────────────────────────────────────────────┘   │
  │                                                              │
  │  ┌─── CHAT PATH ─────────────────────────────────────────┐   │
  │  │                                                       │   │
  │  │  1. Moderation Agent (Claude/GPT, temp=0.1)           │   │
  │  │     └─ Categories: agricultural, admin_intent,        │   │
  │  │        non_agricultural, translation_request          │   │
  │  │     └─ Actions: allow, block, translate               │   │
  │  │                                                       │   │
  │  │  2. Query Pre-Translation (when pipeline enabled)     │   │
  │  │     └─ Gujarati → English via Claude Haiku 3.5       │   │
  │  └───────────────────────────────────────────────────────┘   │
  └──────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │              PYDANTIC AI AGENTIC LOOP                        │
  │                                                              │
  │  ┌─── VOICE AGENTS ─────────────────────────────────────┐    │
  │  │                                                      │    │
  │  │  voice_agent          (unauthenticated callers)      │    │
  │  │  voice_agent_signed_in (authenticated callers)       │    │
  │  │                                                      │    │
  │  │  Model: GPT-5.1 (configurable via LLM_PROVIDER)     │    │
  │  │  System prompt: voice_system_translation_pipeline_en │    │
  │  │  Settings: max_tokens=3600, temp=0.0                 │    │
  │  │  Tool strategy: parallel_tool_calls=False            │    │
  │  │  End strategy: 'early'                               │    │
  │  │  Retries: 3                                          │    │
  │  │  Deps: FarmerContext(query, mobile, signed_in,       │    │
  │  │        farmer_info, session_id, process_id)          │    │
  │  │                                                      │    │
  │  │  Runtime context injected per turn:                  │    │
  │  │    - Today's date                                    │    │
  │  │    - Signed-in status                                │    │
  │  │    - Normalized mobile                               │    │
  │  │    - Farmer context (name, society, animals)         │    │
  │  │    - "Core loop language: English"                   │    │
  │  └──────────────────────────────────────────────────────┘    │
  │                                                              │
  │  ┌─── CHAT AGENTS ──────────────────────────────────────┐    │
  │  │                                                      │    │
  │  │  agrinet_agent        (main conversational agent)    │    │
  │  │  moderation_agent     (input classification)         │    │
  │  │  suggestions_agent    (background, post-response)    │    │
  │  │                                                      │    │
  │  │  Model: GPT-5.1 (configurable)                       │    │
  │  │  System prompt: agrinet_system_translation_pipeline   │    │
  │  │  Settings: max_tokens=4000, parallel_tools=True      │    │
  │  │  End strategy: varies per agent                      │    │
  │  │  Retries: 5, request_limit: 10                       │    │                                
  │  └──────────────────────────────────────────────────────┘    │
  │                                                              │                                
  │  ┌─── TOOL DECLARATIONS ────────────────────────────────┐    │
  │  │                                                      │    │                                
  │  │  BASE_TOOLS (both agents):                           │    │                                
  │  │    search_documents(query, top_k)                    │    │                                
  │  │      └─ Marqo vector search, takes_ctx=True          │    │                                
  │  │    search_terms(term)                                │    │
  │  │      └─ JSON glossary lookup for ambiguous terms     │    │                                
  │  │    create_ai_call(...)                               │    │                                
  │  │      └─ Book artificial insemination via PashuGPT    │    │                                
  │  │      └─ Cooldown: 30 min per session (Redis)         │    │                                
  │  │                                                      │    │                                
  │  │  SIGNED_IN_FARMER_TOOLS (voice_agent_signed_in):     │    │
  │  │    get_farmer_profile()                              │    │                                
  │  │      └─ Farmer name, society, membership             │    │                                
  │  │    get_herd_summary()                                │    │                                
  │  │      └─ Animal count, breeds, milk production        │    │                                
  │  │    list_animal_tags()                                │    │                                
  │  │      └─ Available ear tag numbers                    │    │
  │  │                                                      │    │                                
  │  │  All tools wrapped with _with_nudge_signal():        │    │                                
  │  │    └─ Fires asyncio.Event on tool invocation         │    │
  │  │    └─ Triggers RAYA nudge ("please wait" to caller)  │    │                                
  │  └──────────────────────────────────────────────────────┘    │
  │                                                              │                                
  │  Agent Loop: user_prompt + message_history + deps            │
  │    → LLM generates (streaming)                               │                                
  │    → if tool_call: execute tool → feed result back → re-gen  │
  │    → if text: stream to post-processing pipeline             │                                
  │                                                              │                                
  └──────────────────────┬───────────────────────────────────────┘
                         │ English text (streaming)                                               
                         ▼                                        
  ┌──────────────────────────────────────────────────────────────┐                                
  │            POST-PROCESSING / TRANSLATION PIPELINE            │                                
  │                                                              │
  │  ┌─── SENTENCE BATCHING (voice) ────────────────────────┐    │                                
  │  │                                                      │    │
  │  │  GPT streams tokens → sentence_buffer                │    │                                
  │  │    → extract_complete_sentences() (regex segmenter)  │    │
  │  │    → accumulate into translation_batch[]             │    │                                
  │  │    → should_translate_batch() decides when to flush:  │    │
  │  │        min_words=15: flush on .!? if ≥5 words        │    │                                
  │  │        15-80 words: flush on sentence/para boundary  │    │                                
  │  │        max_words=80: force flush                     │    │                                
  │  └──────────────────────────────────────────────────────┘    │                                
  │                                                              │                                
  │  ┌─── RESPONSE TRANSLATION ─────────────────────────────┐    │                                
  │  │                                                      │    │                                
  │  │  translate_text_stream_fast() [streaming, current]    │    │                               
  │  │  translate_text()             [non-streaming]         │    │
  │  │                                                      │    │                                
  │  │  Model: TranslateGemma 27B (vLLM endpoint)           │    │
  │  │  Features:                                           │    │                                
  │  │    - Mini glossary injection (agricultural terms)     │    │                               
  │  │    - Gujarati term policy (forbidden→preferred)       │    │                               
  │  │    - Danda normalization (_fix_dandas)                │    │                               
  │  │    - Post-normalization (_post_normalize_gu)          │    │
  │  └──────────────────────────────────────────────────────┘    │                                
  │                                                              │                                
  │  ┌─── VOICE OUTPUT CLEANING ────────────────────────────┐    │                                
  │  │                                                      │    │                                
  │  │  clean_output_by_language(text, lang_code)            │    │                               
  │  │    └─ normalize_voice_output(): strip markdown,       │    │                               
  │  │       list markers, headers, brackets                │    │                                
  │  │    └─ Gujarati filter: allow only U+0A80..U+0AFF     │    │
  │  │       + whitespace + basic punctuation               │    │                                
  │  │    └─ BUG: Latin digits 0-9 stripped (not in range)  │    │                                
  │  │    └─ FIX NEEDED: call normalize_numbers_for_tts()   │    │                                
  │  │       before char filter                             │    │                                
  │  └──────────────────────────────────────────────────────┘    │                                
  │                                                              │                                
  └──────────────────────┬───────────────────────────────────────┘                                
                         │ Gujarati text                                                          
                         ▼                                                                        
  ┌──────────────────────────────────────────────────────────────┐                                
  │                    DELIVERY LAYER                            │                                
  │                                                              │
  │  VOICE: StreamingResponse → RAYA → TTS → caller hears it    │                                 
  │  CHAT:  SSE events → web client renders markdown             │
  │                                                              │                                
  │  Voice-specific:                                             │
  │    - Nudge messages sent during tool calls/delays            │                                
  │    - RAYA nudge API: POST /api/nudge-user                    │                                
  │    - signal_conversation_state tool: in_progress, closing    │                                
  └──────────────────────────────────────────────────────────────┘                                
                                                                                                  
                                                                                                  
  ============================================================================                    
                      EXTERNAL INTEGRATIONS                                                       
  ============================================================================                    
                                                                                                  
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  LLM PROVIDERS                     FARMER/ANIMAL APIs        │
  │  ┌─────────────────────┐          ┌─────────────────────┐   │                                 
  │  │ OpenAI (GPT-5.1)    │          │ amulpashudhan.com   │   │
  │  │  - Agent core loop   │          │  GetFarmerDetails   │   │                                
  │  │  - Pretranslation    │          │  CreateAICall       │   │                                
  │  │                      │          │  (PASHUGPT_TOKEN)   │   │
  │  │ Anthropic (Claude)   │          ├─────────────────────┤   │                                
  │  │  - Chat pretranslate │          │ herdman.live        │   │                                
  │  │  - Moderation        │          │  get-amul-farmer    │   │                                
  │  │                      │          │  get-amul-animal    │   │                                
  │  │ vLLM (self-hosted)   │          │  (PASHUGPT_TOKEN_3) │   │
  │  │  - TranslateGemma    │          └─────────────────────┘   │                                
  │  │    27B translation   │                                    │                                
  │  └─────────────────────┘          VECTOR SEARCH              │                                
  │                                   ┌─────────────────────┐   │                                 
  │  TELEPHONY                        │ Marqo (self-hosted) │   │                                 
  │  ┌─────────────────────┐          │  Index: configurable │   │                                
  │  │ RAYA (getraya.app)  │          │  search_documents() │   │ 
  │  │  - STT (speech→text) │          │  Agricultural KB    │   │                                
  │  │  - TTS (text→speech) │          └─────────────────────┘   │
  │  │  - Nudge API         │                                    │                                
  │  │  - Call recordings   │          STORAGE                   │                                
  │  └─────────────────────┘          ┌─────────────────────┐   │                                 
  │                                   │ AWS S3              │   │                                 
  │  OBSERVABILITY                    │  Call recordings     │   │                                
  │  ┌─────────────────────┐          └─────────────────────┘   │                                 
  │  │ Langfuse             │                                    │
  │  │  Auto-instrumented:  │          STT/TTS (chat)            │                                
  │  │  - Agent runs        │          ┌─────────────────────┐   │
  │  │  - Tool calls        │          │ Bhashini (default)  │   │                                
  │  │  - Translations      │          │ Whisper (fallback)  │   │
  │  │  - Token usage/cost  │          └─────────────────────┘   │                                
  │  │  - Nudge events      │                                    │                                
  │  │                      │                                    │                                
  │  │  Environments:       │                                    │                                
  │  │  - voice-production  │                                    │                                
  │  │  - chat-production   │                                    │                                
  │  │  - development       │                                    │                                
  │  └─────────────────────┘                                     │
  │                                                              │                                
  └──────────────────────────────────────────────────────────────┘
                                                                                                  
                                          
  ============================================================================                    
            VOICE CALL LIFECYCLE (single turn, translation pipeline)                              
  ============================================================================
                                                                                                  
   RAYA STT ──► Progressive fragments arrive (process_id increments)
                │                                                                                 
                ├─ Fragment 1: "સરલાબેન મારી"  (partial)
                │   └─ pretranslate → "Sarlaben, my..." → fragment detected → skip                
                │                                                 
                ├─ Fragment 2: "...ગાયને બહુ બધી" (still partial)                                   
                │   └─ pretranslate → "my cow has..." → nudge sent ("please wait")                
                │   └─ agent starts → anext() error (concurrency) → wasted                        
                │                                                                                 
                └─ Fragment 3: "...બગાઈઓ લાગેલી છે તો દૂર કેવી રીતના કરવી" (FULL)                     
                    │                                                                             
                    ▼                                                                             
            pretranslate_to_english_with_gpt5_mini()                                              
            "Sarlaben, my cow has ticks, how to remove?" (~1s)                                    
                    │                                                                             
                    ▼                                                                             
            voice_agent_signed_in.run_stream(                                                     
                user_prompt = '**User:** "How can I remove ticks?"',                              
                message_history = [...prior turns in English...],                                 
                deps = FarmerContext(mobile="7600713373", signed_in=True, ...)                    
            )                                                                                     
                    │                                                                             
            GPT-5.1 streaming ──► tokens arrive                                                   
                    │                                                                             
                    ├─ "You can control ticks..."  → sentence_buffer                              
                    ├─ "Here's what you should do:" → batch (not flushed, no .!?)                 
                    ├─ "...tie her properly."       → batch flushed (≥5 words + ".")              
                    │       │                 
                    │       ▼                                                                     
                    │   translate_text_stream_fast("You can control...tie her properly.")         
                    │       │                                                                     
                    │       ▼                                                                     
                    │   TranslateGemma 27B (vLLM, stream=True)                                    
                    │       │                                                                     
                    │       ▼                                     
                    │   clean_output_by_language(translated, "gu")                                
                    │       │                                                                     
                    │       ▼                 
                    │   StreamingResponse → RAYA → TTS → caller hears first sentence              
                    │                                             
                    ├─ Next batch accumulates...                                                  
                    └─ (continues until GPT finishes)
```