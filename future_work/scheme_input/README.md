# Scheme Input Pipeline (PDF -> Searchable Schemes)

This README defines a simple setup to ingest a scheme PDF, convert it into structured scheme records, and expose them for reliable tool calls and search.

## Goal

Given a PDF containing one or more schemes, create a normalized scheme object with:

- `scheme_name`
- `scheme_code`
- `short_description`
- `eligibility`
- `benefits`
- `documents_required`
- `application_process`
- `important_dates`
- `official_links`
- `contact_details`
- `source_pdf`
- `source_page_refs`

Then index the text fields for better semantic and keyword search.

## High-level Flow

1. Ingest PDF file.
2. Extract text per page (keep page numbers).
3. Segment by scheme boundaries (one PDF may contain multiple schemes).
4. Parse each segment into the common scheme structure.
5. Validate and normalize fields (required vs optional).
6. Save structured records.
7. Build search index over key descriptive fields.
8. Expose retrieval APIs for tool calling.

## Canonical Scheme Object

Use one consistent object shape so every tool call can rely on the same contract:

```json
{
  "scheme_id": "SCH-000123",
  "scheme_name": "Pradhan Mantri Fasal Bima Yojana",
  "scheme_code": "PMFBY",
  "short_description": "Crop insurance support for notified crops and areas.",
  "eligibility": [
    "Farmer must be registered in notified area",
    "Crop must be covered under current season notification"
  ],
  "benefits": [
    "Insurance coverage for crop loss",
    "Claim support under eligible events"
  ],
  "documents_required": [
    "Aadhaar",
    "Bank account details",
    "Land records"
  ],
  "application_process": [
    "Check scheme notification",
    "Submit application through portal/CSC",
    "Track status with reference ID"
  ],
  "important_dates": [
    {
      "label": "Kharif enrollment deadline",
      "value": "2026-07-31"
    }
  ],
  "official_links": [
    "https://example.gov/scheme/pmfby"
  ],
  "contact_details": [
    "Helpline: 1800-000-000"
  ],
  "source_pdf": "pmfby_guidelines_2026.pdf",
  "source_page_refs": [3, 4, 5],
  "last_updated": "2026-04-27"
}
```

## Minimum Validation Rules

- `scheme_name` and `short_description` are required.
- `scheme_code` can be null if not present in source.
- Keep lists as arrays even for single values.
- Preserve source traceability with `source_pdf` + `source_page_refs`.
- If a field is missing, use empty array (`[]`) or null, not free text placeholders.

## Search Strategy

Create two search paths for best retrieval quality:

1. **Keyword search** on:
   - `scheme_name`
   - `scheme_code`
   - `short_description`
   - `eligibility`
   - `benefits`
2. **Semantic/vector search** on:
   - `short_description`
   - `eligibility`
   - `benefits`
   - `application_process`

Return merged and reranked results. Always return `scheme_id`, `scheme_name`, `scheme_code`, `short_description`, and source references.

## Tool-call Friendly API Shape

Keep endpoints simple and stable so agent tools can call them safely.

### 1) Ingest PDF

`POST /schemes/ingest`

Request:

```json
{
  "pdf_path": "data/schemes/pmfby.pdf",
  "source_tag": "gov_pdf_batch_apr_2026"
}
```

Response:

```json
{
  "ingestion_id": "ING-20260427-001",
  "schemes_created": 3,
  "scheme_ids": ["SCH-000121", "SCH-000122", "SCH-000123"]
}
```

### 2) Search Schemes

`POST /schemes/search`

Request:

```json
{
  "query": "insurance scheme for crop loss in kharif",
  "top_k": 5,
  "filters": {
    "state": "Maharashtra"
  }
}
```

Response:

```json
{
  "results": [
    {
      "scheme_id": "SCH-000123",
      "scheme_name": "Pradhan Mantri Fasal Bima Yojana",
      "scheme_code": "PMFBY",
      "short_description": "Crop insurance support for notified crops and areas.",
      "score": 0.91,
      "source_pdf": "pmfby_guidelines_2026.pdf",
      "source_page_refs": [3, 4, 5]
    }
  ]
}
```

### 3) Get Scheme Details

`GET /schemes/{scheme_id}`

Returns full canonical object.

## Recommended Storage

- `schemes` table/collection: one row per scheme (canonical object).
- `scheme_chunks` table/collection: chunked text blocks for semantic index.
- `ingestion_runs` table/collection: ingestion audit trail (input file, timestamp, status, errors).

This separation keeps retrieval fast while preserving full structured fields for deterministic tool use.

## Practical Notes

- Start simple: one parser + one schema + one search endpoint.
- Add confidence flags later (field extraction confidence, OCR confidence).
- Re-ingest when PDFs update; do not overwrite without version tracking.
- Keep source page references mandatory for debugging and trust.
