# Implementation Plan: AI-Powered Flashcard Generator

**Date**: 2025-12-03
**Status**: Ready for Implementation
**Based on**: [research-ai-flashcard-generator.md](./research-ai-flashcard-generator.md)

## Overview

This plan details the implementation of an AI-powered flashcard generator as a core Anki feature. Users will upload documents (PDF, text, URLs) and receive AI-generated flashcards for review before import.

## Final Specification Summary

| Decision            | Choice                                                            |
| ------------------- | ----------------------------------------------------------------- |
| LLM Provider        | OpenAI (API key required)                                         |
| Processing          | Hybrid: Python (document parsing + API) / Rust (parsing + import) |
| Document Formats    | PDF, text files, pasted text, URLs                                |
| Entry Point         | "AI Flashcards" button on main page                               |
| Note Types          | User default + AI suggestions (Basic, Basic reversed, Cloze)      |
| API Key Storage     | Encrypted in Preferences                                          |
| Session Persistence | Temp file, resume prompt, 7-day auto-delete                       |
| Deck Selection      | User chooses during review                                        |
| Batch Processing    | All cards at once                                                 |
| Cost Visibility     | Show estimated tokens/cost before processing                      |
| Auto-tagging        | `ai-generated` + `source::filename`                               |
| Card Limit          | User-configurable maximum                                         |
| Regeneration        | Option to regenerate rejected cards                               |
| Edit Interface      | Simple text fields                                                |

---

## Phase 1: Foundation & Preferences Infrastructure

### 1.1 Add AI Flashcards Preferences Section

**Files to modify:**

- `qt/aqt/forms/preferences.ui` - Add new tab/section for AI settings
- `qt/aqt/preferences.py` - Handle AI preferences logic
- `proto/anki/config.proto` - Add AI config fields

**Tasks:**

- [x] Add "AI Flashcards" section to Preferences dialog
- [x] Create input field for OpenAI API key (password-masked)
- [x] Add "Test Connection" button to validate API key
- [x] Add dropdown for default note type preference (Basic, Basic reversed, Cloze)
- [x] Add default card limit field (number input, default: 20)
- [x] Store API key encrypted using existing Anki encryption utilities

**Config fields to add:**

```protobuf
message AIFlashcardsConfig {
  string openai_api_key_encrypted = 1;
  string default_notetype = 2;  // "basic", "basic_reversed", "cloze"
  uint32 default_card_limit = 3;
}
```

### 1.2 API Key Encryption

**Files modified:**

- `qt/aqt/secret.py` - Created obfuscation utilities (new file)
- `qt/aqt/profiles.py` - Added AI settings storage methods

**Tasks:**

- [x] Implement `obfuscate_api_key(key: str) -> str`
- [x] Implement `deobfuscate_api_key(encrypted: str) -> str`
- [x] Use XOR + base64 obfuscation with machine-specific key derivation (matches existing Anki patterns)

---

## Phase 2: Document Processing Pipeline (Python)

### 2.1 Create AI Flashcards Python Module

**New files:**

- `pylib/anki/ai_flashcards/__init__.py`
- `pylib/anki/ai_flashcards/document_parser.py`
- `pylib/anki/ai_flashcards/openai_client.py`
- `pylib/anki/ai_flashcards/models.py`

### 2.2 Document Parser

**File:** `pylib/anki/ai_flashcards/document_parser.py`

**Tasks:**

- [ ] Implement `parse_pdf(file_path: str) -> str` using PyMuPDF
- [ ] Implement `parse_text_file(file_path: str) -> str`
- [ ] Implement `parse_url(url: str) -> str` using requests + BeautifulSoup
- [ ] Implement `parse_pasted_text(text: str) -> str` (minimal processing)
- [ ] Add text chunking for large documents (respect token limits)
- [ ] Implement `estimate_tokens(text: str) -> int` for cost estimation

**Dependencies to add:**

- `PyMuPDF` (fitz) for PDF parsing
- `beautifulsoup4` for HTML parsing
- `tiktoken` for accurate token counting

### 2.3 OpenAI Client

**File:** `pylib/anki/ai_flashcards/openai_client.py`

**Tasks:**

- [ ] Implement `OpenAIFlashcardClient` class
- [ ] Add `test_connection(api_key: str) -> bool` for preferences validation
- [ ] Add `estimate_cost(token_count: int, model: str) -> float`
- [ ] Implement `generate_flashcards(text: str, config: GenerationConfig) -> list[GeneratedCard]`
- [ ] Design prompt template for flashcard generation
- [ ] Parse structured JSON response from OpenAI
- [ ] Handle rate limiting and errors gracefully

**Prompt Engineering:**

```python
SYSTEM_PROMPT = """You are an expert educator creating Anki flashcards.
Generate flashcards from the provided text following these rules:
1. Create clear, atomic cards (one concept per card)
2. For definitions and simple facts, use Basic format
3. For vocabulary/translations, use Basic (reversed) format
4. For processes, sequences, or fill-in-blank, use Cloze format
5. Ensure answers are concise but complete
6. Include context when the question would be ambiguous without it

Respond in JSON format:
{
  "cards": [
    {
      "type": "basic|basic_reversed|cloze",
      "front": "question or cloze text with {{c1::deletions}}",
      "back": "answer (empty string for cloze)",
      "suggested_tags": ["optional", "topic", "tags"]
    }
  ]
}
"""
```

### 2.4 Data Models

**File:** `pylib/anki/ai_flashcards/models.py`

**Tasks:**

- [ ] Define `GenerationConfig` dataclass (limit, notetype preference, source info)
- [ ] Define `GeneratedCard` dataclass (type, front, back, tags, status)
- [ ] Define `GenerationSession` dataclass (cards, source, timestamp, session_id)
- [ ] Define `CardStatus` enum (pending, approved, rejected, regenerating)

---

## Phase 3: Rust Parsing and Validation Layer

### 3.1 Create AI Flashcards Rust Module

**New files:**

- `rslib/src/ai_flashcards/mod.rs`
- `rslib/src/ai_flashcards/parse.rs`
- `rslib/src/ai_flashcards/validate.rs`
- `rslib/src/ai_flashcards/convert.rs`

### 3.2 Response Parser

**File:** `rslib/src/ai_flashcards/parse.rs`

**Tasks:**

- [ ] Define `AIGeneratedCard` struct matching Python model
- [ ] Implement `parse_openai_response(json: &str) -> Result<Vec<AIGeneratedCard>>`
- [ ] Handle malformed JSON gracefully (partial recovery)
- [ ] Validate cloze syntax for cloze-type cards

### 3.3 Content Validator

**File:** `rslib/src/ai_flashcards/validate.rs`

**Tasks:**

- [ ] Implement `validate_card(card: &AIGeneratedCard) -> ValidationResult`
- [ ] Check for empty fields
- [ ] Validate cloze deletion syntax using existing `rslib/src/cloze.rs`
- [ ] Sanitize HTML content using existing ammonia integration
- [ ] Check field length limits

### 3.4 ForeignNote Converter

**File:** `rslib/src/ai_flashcards/convert.rs`

**Tasks:**

- [ ] Implement `to_foreign_note(card: &AIGeneratedCard, config: &ImportConfig) -> ForeignNote`
- [ ] Map card types to appropriate notetype IDs
- [ ] Apply auto-tags (`ai-generated`, `source::filename`)
- [ ] Set target deck from user selection

---

## Phase 4: Protobuf Service Definitions

### 4.1 Define AI Flashcards Service

**New file:** `proto/anki/ai_flashcards.proto`

```protobuf
syntax = "proto3";
package anki.ai_flashcards;

import "anki/generic.proto";

service AIFlashcardsService {
  // Test OpenAI API connection
  rpc TestApiConnection(TestApiConnectionRequest) returns (TestApiConnectionResponse);

  // Estimate cost before generation
  rpc EstimateCost(EstimateCostRequest) returns (EstimateCostResponse);

  // Generate flashcards from document
  rpc GenerateFlashcards(GenerateFlashcardsRequest) returns (GenerateFlashcardsResponse);

  // Regenerate a single rejected card
  rpc RegenerateCard(RegenerateCardRequest) returns (RegenerateCardResponse);

  // Import approved cards to collection
  rpc ImportApprovedCards(ImportApprovedCardsRequest) returns (ImportApprovedCardsResponse);

  // Session management
  rpc SaveSession(SaveSessionRequest) returns (generic.Empty);
  rpc LoadSession(generic.Empty) returns (LoadSessionResponse);
  rpc ClearSession(generic.Empty) returns (generic.Empty);
}

message TestApiConnectionRequest {
  string api_key = 1;
}

message TestApiConnectionResponse {
  bool success = 1;
  string error_message = 2;
}

message EstimateCostRequest {
  oneof source {
    string file_path = 1;
    string url = 2;
    string pasted_text = 3;
  }
}

message EstimateCostResponse {
  uint32 estimated_tokens = 1;
  float estimated_cost_usd = 2;
  string model = 3;
}

message GenerateFlashcardsRequest {
  oneof source {
    string file_path = 1;
    string url = 2;
    string pasted_text = 3;
  }
  uint32 card_limit = 4;
  string preferred_notetype = 5;  // "basic", "basic_reversed", "cloze", or "auto"
}

message GeneratedCard {
  string id = 1;  // UUID for tracking
  string card_type = 2;  // "basic", "basic_reversed", "cloze"
  string front = 3;
  string back = 4;
  repeated string suggested_tags = 5;
  string status = 6;  // "pending", "approved", "rejected"
}

message GenerateFlashcardsResponse {
  repeated GeneratedCard cards = 1;
  string source_name = 2;
  uint32 tokens_used = 3;
  float cost_usd = 4;
}

message RegenerateCardRequest {
  string card_id = 1;
  string context_hint = 2;  // Optional user hint for regeneration
}

message RegenerateCardResponse {
  GeneratedCard new_card = 1;
}

message ImportApprovedCardsRequest {
  repeated GeneratedCard cards = 1;
  int64 target_deck_id = 2;
}

message ImportApprovedCardsResponse {
  uint32 imported_count = 1;
  uint32 duplicate_count = 2;
  repeated string errors = 3;
}

message LoadSessionResponse {
  bool has_session = 1;
  repeated GeneratedCard cards = 2;
  string source_name = 3;
  int64 created_timestamp = 4;
}
```

### 4.2 Implement Backend Service

**Files to modify:**

- `rslib/src/backend/mod.rs` - Register new service
- `rslib/src/lib.rs` - Export ai_flashcards module

**New file:** `rslib/src/ai_flashcards/service.rs`

**Tasks:**

- [ ] Implement service trait for AIFlashcardsService
- [ ] Wire up to Python layer for document parsing and API calls
- [ ] Implement session persistence to profile temp directory

---

## Phase 5: Frontend UI

### 5.1 Main Page Button

**Files to modify:**

- `ts/routes/deck-options/` or equivalent main page component
- Need to locate exact file for main page buttons

**Tasks:**

- [ ] Identify the component containing "Get Started", "Create Deck", "Import File" buttons
- [ ] Add "AI Flashcards" button with appropriate icon
- [ ] Wire button to open AI Flashcards dialog/route

### 5.2 AI Flashcards Dialog - Source Selection

**New files:**

- `ts/routes/ai-flashcards/AIFlashcardsPage.svelte`
- `ts/routes/ai-flashcards/SourceSelector.svelte`
- `ts/routes/ai-flashcards/CostEstimate.svelte`

**Tasks:**

- [ ] Create tabbed interface for source selection (File, URL, Paste Text)
- [ ] File tab: drag-drop zone + file picker (accept .pdf, .txt)
- [ ] URL tab: text input with validation
- [ ] Paste tab: large textarea
- [ ] Add card limit input (number, default from preferences)
- [ ] Add note type preference dropdown
- [ ] Display cost estimate after source is selected
- [ ] "Generate Cards" button (disabled until source selected and API key configured)
- [ ] Show "Configure API key in Preferences" message if key missing

### 5.3 Generation Progress

**New file:** `ts/routes/ai-flashcards/GenerationProgress.svelte`

**Tasks:**

- [ ] Display spinner/progress indicator during generation
- [ ] Show "Extracting text..." → "Generating flashcards..." → "Validating..." stages
- [ ] Handle errors gracefully with retry option
- [ ] Cancel button to abort

### 5.4 Card Review Interface

**New files:**

- `ts/routes/ai-flashcards/CardReview.svelte`
- `ts/routes/ai-flashcards/CardPreview.svelte`
- `ts/routes/ai-flashcards/CardEditor.svelte`

**Tasks:**

- [ ] Display list of generated cards with status indicators
- [ ] Card preview showing front/back (or cloze with deletions highlighted)
- [ ] Per-card action buttons: Approve ✓, Reject ✗, Edit ✏️, Regenerate 🔄
- [ ] Batch actions: Approve All, Reject All
- [ ] Inline editor with simple text fields (front, back, tags)
- [ ] Deck selector dropdown
- [ ] Summary stats: X approved, Y rejected, Z pending
- [ ] "Import Approved Cards" button
- [ ] "Save for Later" button (persist session)

### 5.5 Import Confirmation

**New file:** `ts/routes/ai-flashcards/ImportResult.svelte`

**Tasks:**

- [ ] Show import results (X imported, Y duplicates, Z errors)
- [ ] Link to browse imported cards
- [ ] "Generate More" button to return to source selection
- [ ] "Done" button to close

---

## Phase 6: Session Persistence

### 6.1 Session Storage

**Location:** `{profile_folder}/ai_flashcards_session.json`

**Tasks:**

- [ ] Save session on "Save for Later" or window close with pending cards
- [ ] Load session on AI Flashcards page open
- [ ] Show "Resume previous session?" prompt if session exists
- [ ] Clear session after successful import
- [ ] Implement 7-day auto-expiry check

**Session file structure:**

```json
{
    "version": 1,
    "created_at": "2025-12-03T12:00:00Z",
    "source_name": "chapter5.pdf",
    "cards": [
        {
            "id": "uuid",
            "type": "basic",
            "front": "...",
            "back": "...",
            "tags": ["ai-generated"],
            "status": "approved"
        }
    ]
}
```

---

## Phase 7: Translations

### 7.1 Add FTL Strings

**New file:** `ftl/core/ai-flashcards.ftl`

**Tasks:**

- [ ] Add all user-facing strings
- [ ] Follow existing FTL style conventions

**Strings needed:**

```ftl
ai-flashcards-button = AI Flashcards
ai-flashcards-title = Generate Flashcards with AI
ai-flashcards-source-file = Upload File
ai-flashcards-source-url = From URL
ai-flashcards-source-paste = Paste Text
ai-flashcards-card-limit = Maximum cards to generate
ai-flashcards-notetype = Preferred card type
ai-flashcards-estimate = Estimated cost: { $tokens } tokens (~${ $cost })
ai-flashcards-generate = Generate Cards
ai-flashcards-generating = Generating flashcards...
ai-flashcards-approve = Approve
ai-flashcards-reject = Reject
ai-flashcards-edit = Edit
ai-flashcards-regenerate = Regenerate
ai-flashcards-approve-all = Approve All
ai-flashcards-import = Import { $count } Cards
ai-flashcards-select-deck = Import to deck
ai-flashcards-no-api-key = OpenAI API key not configured. Set it in Preferences → AI Flashcards.
ai-flashcards-api-error = API error: { $message }
ai-flashcards-import-success = Successfully imported { $count } cards
ai-flashcards-resume-session = Resume previous session from { $date }?
ai-flashcards-session-expired = Previous session expired and was cleared.
```

---

## Phase 8: Testing

### 8.1 Unit Tests

**Rust tests:**

- [ ] `rslib/src/ai_flashcards/parse.rs` - JSON parsing tests
- [ ] `rslib/src/ai_flashcards/validate.rs` - Validation logic tests
- [ ] `rslib/src/ai_flashcards/convert.rs` - ForeignNote conversion tests

**Python tests:**

- [ ] `pylib/tests/test_ai_flashcards/` - Document parsing tests
- [ ] Mock OpenAI responses for client tests
- [ ] Token estimation accuracy tests

### 8.2 Integration Tests

- [ ] End-to-end flow with mock OpenAI API
- [ ] Session persistence round-trip
- [ ] Import integration with duplicate detection

### 8.3 Manual Testing Checklist

- [ ] PDF parsing with various PDF types (text, scanned, mixed)
- [ ] URL parsing with various website structures
- [ ] Large document handling (chunking)
- [ ] API error handling (invalid key, rate limit, timeout)
- [ ] Session resume after Anki restart
- [ ] Import to different decks
- [ ] All three note types generate correctly

---

## Phase 9: Dependencies & Build

### 9.1 Python Dependencies

**Add to requirements:**

```
PyMuPDF>=1.23.0
beautifulsoup4>=4.12.0
tiktoken>=0.5.0
openai>=1.0.0
```

### 9.2 Build Integration

**Tasks:**

- [ ] Update `build/` scripts to include new proto file
- [ ] Ensure TypeScript types are generated for new service
- [ ] Add new Svelte route to build

---

## Implementation Order

### Sprint 1: Foundation

1. Phase 1.1 - Preferences UI for API key
2. Phase 1.2 - API key encryption
3. Phase 2.4 - Data models
4. Phase 4.1 - Protobuf definitions (partial - just config)

### Sprint 2: Document Processing

1. Phase 2.2 - Document parser (PDF, text, URL)
2. Phase 2.3 - OpenAI client
3. Phase 4.1 - Complete protobuf definitions
4. Phase 4.2 - Backend service (generation flow)

### Sprint 3: Rust Layer

1. Phase 3.2 - Response parser
2. Phase 3.3 - Content validator
3. Phase 3.4 - ForeignNote converter
4. Wire up Python ↔ Rust communication

### Sprint 4: Frontend - Generation

1. Phase 5.1 - Main page button
2. Phase 5.2 - Source selection dialog
3. Phase 5.3 - Generation progress
4. Phase 7.1 - Translations

### Sprint 5: Frontend - Review & Import

1. Phase 5.4 - Card review interface
2. Phase 5.5 - Import confirmation
3. Phase 6.1 - Session persistence

### Sprint 6: Polish & Testing

1. Phase 8.1 - Unit tests
2. Phase 8.2 - Integration tests
3. Phase 8.3 - Manual testing
4. Bug fixes and polish

---

## Risk Mitigation

| Risk                    | Mitigation                                                              |
| ----------------------- | ----------------------------------------------------------------------- |
| OpenAI API changes      | Use official SDK, pin version, abstract client interface                |
| PDF parsing failures    | Graceful degradation, clear error messages, suggest text paste fallback |
| Token limit exceeded    | Implement chunking, process in segments, combine results                |
| Cost unexpectedly high  | Show estimate upfront, require confirmation, add spending limit option  |
| Session data corruption | Version session format, validate on load, clear if invalid              |

---

## Future Enhancements (Out of Scope)

- Ollama/local LLM support
- Image OCR
- Word document support
- Multiple LLM providers
- Prompt customization by users
- Card templates/styles
- Batch processing multiple documents
- Integration with AnkiWeb

---

## Success Criteria

1. Users can generate flashcards from PDF, text file, URL, or pasted text
2. Cost is estimated and shown before generation
3. Generated cards can be reviewed, edited, approved, or rejected
4. Approved cards import correctly with proper note types
5. Sessions persist across Anki restarts
6. API key is stored securely
7. Feature is discoverable from main page
8. Errors are handled gracefully with clear messages
