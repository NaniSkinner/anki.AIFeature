---
date: 2025-12-03T17:46:44Z
researcher: Claude
git_commit: 2d4de33cf3160342c4c704c294e643c3e11071b1
branch: main
repository: Anki
topic: "AI-Powered Flashcard Generator from Source Documents"
tags: [research, codebase, flashcards, ai-integration, import, notes, cards, editor]
status: complete
last_updated: 2025-12-03
last_updated_by: Claude
---

# Research: AI-Powered Flashcard Generator from Source Documents

**Date**: 2025-12-03T17:46:44Z
**Researcher**: Claude
**Git Commit**: 2d4de33cf3160342c4c704c294e643c3e11071b1
**Branch**: main
**Repository**: Anki

## Research Question

Build an AI-Powered Flashcard Generator that allows Anki users to automatically create high-quality flashcards from source documents (PDFs, text files, or pasted text) using large language models. The feature will accept uploaded study materials and use AI to intelligently extract key concepts, facts, and relationships, then generate question-answer pairs formatted as Anki notes. Users will be presented with a review interface showing all AI-generated cards where they can edit, approve, or reject suggestions before importing them into their Anki collection.

## Summary

The Anki codebase has all the fundamental infrastructure needed to implement an AI-powered flashcard generator. The architecture consists of:

1. **Note/Card Creation System**: Robust Rust backend with `Collection::add_note()` and batch operations, supporting multiple card types through the notetype system
2. **Import Infrastructure**: Comprehensive CSV/JSON import with preview, field mapping, and duplicate detection capabilities
3. **Editor Components**: Sophisticated Svelte-based editor with field management, toolbar, and real-time validation
4. **API Layer**: Protobuf-based RPC system enabling TypeScript↔Rust and Python↔Rust communication
5. **Text Processing**: Extensive parsing capabilities for HTML, cloze deletions, templates, and media references

The recommended implementation approach would leverage the existing CSV/JSON import flow, adding an AI processing step that generates `ForeignData` structures, then uses the preview and review interfaces already in place.

## Detailed Findings

### 1. Note and Card Creation Architecture

The core note creation system (`rslib/src/notes/mod.rs:90-92`) provides:

- **Entry Points**:
  - `Collection::add_note()` for single notes
  - `Collection::add_notes()` for batch operations (essential for bulk AI generation)
- **Data Flow**:
  1. Note preparation with field normalization
  2. Checksum calculation for duplicate detection
  3. Database insertion with transaction support
  4. Automatic card generation based on note type templates
- **Key Components**:
  - `Note` struct with fields, tags, and metadata (`rslib/src/notes/mod.rs:41-51`)
  - `Card` generation from templates (`rslib/src/notetype/cardgen.rs:213-226`)
  - Transaction management ensuring atomicity

**Relevance**: The batch operation support is perfect for importing multiple AI-generated flashcards efficiently.

### 2. Import System Architecture

The import system (`rslib/src/import_export/text/`) provides a complete pipeline:

#### CSV Import Flow

- **Preview Stage** (`rslib/src/import_export/text/csv/metadata.rs:41`):
  - Extracts first 5 rows for preview
  - Auto-detects delimiters and HTML content
  - Field mapping configuration
- **Import Stage** (`rslib/src/import_export/text/import.rs:35-52`):
  - Duplicate detection via checksum/GUID
  - Three resolution strategies: Update, Preserve, Duplicate
  - Validation and error categorization
  - Progress tracking for long operations

#### Key Data Structures

- `ForeignData` (`rslib/src/import_export/text/mod.rs:15-26`): Container for notes to import
- `ForeignNote` (`rslib/src/import_export/text/mod.rs:28-37`): Individual note with fields, tags, deck
- `ImportResponse` with detailed categorization of results

**Relevance**: This provides the perfect foundation - AI-generated content can be converted to `ForeignData` format and leverage all existing import machinery.

### 3. Note Type System

The note type system (`rslib/src/notetype/`) supports diverse card formats:

- **Built-in Types** (`rslib/src/notetype/stock.rs`):
  - Basic (Front/Back)
  - Basic with reverse
  - Cloze deletions
  - Type-in-the-answer
- **Template Engine** (`rslib/src/template.rs`):
  - Field substitution with `{{Field}}` syntax
  - Conditional rendering with `{{#Field}}...{{/Field}}`
  - Filters for text transformation

**Relevance**: AI can target different note types based on content structure (definitions → Basic, processes → Cloze, etc.)

### 4. Frontend Editor Architecture

The editor (`ts/editor/`) provides rich editing capabilities:

- **NoteEditor Component** (`ts/editor/NoteEditor.svelte`):
  - Field management with collapse/expand
  - Rich text and plain text modes
  - Real-time validation and updates
- **EditorToolbar** (`ts/editor/editor-toolbar/`):
  - Formatting controls
  - Cloze insertion tools
  - Extensible via slots for add-ons

**Review Interface Components**:

- `ImportPage.svelte` (`ts/routes/import-page/`): Generic import interface
- `ImportLogPage.svelte`: Results display with categorization
- `FieldMapper.svelte` (`ts/routes/import-csv/`): Field mapping UI

**Relevance**: These components can be reused/extended for the AI card review interface.

### 5. Backend Communication

The communication layer (`rslib/rust_interface.rs`) provides:

- **Protobuf Services**: Type-safe service definitions
- **Python Bridge** (`pylib/rsbridge/`): PyO3-based Python↔Rust communication
- **TypeScript API** (`ts/lib/generated/`): Auto-generated TypeScript clients
- **HTTP Endpoints** (`qt/aqt/mediasrv.py`): Flask server for frontend requests

**Key Patterns**:

- Service methods on Collection for operations requiring open collection
- Numeric service/method dispatch for efficiency
- Automatic error serialization/deserialization

**Relevance**: New AI services can follow the same protobuf→implementation pattern.

### 6. Text Processing Capabilities

Extensive text processing (`rslib/src/text.rs`, `rslib/src/cloze.rs`):

- **HTML Processing**:
  - Stripping with media preservation
  - Entity encoding/decoding
  - Sanitization via ammonia library
- **Cloze Parsing**:
  - Recursive parsing supporting nested clozes
  - Multi-ordinal support (`{{c1,2,3::text}}`)
- **Media Handling**:
  - Reference extraction from multiple tag formats
  - Filename normalization
  - SHA1-based deduplication

**Relevance**: Essential for processing AI output and ensuring valid flashcard content.

## Architecture Recommendations

### Proposed Implementation Flow

1. **Document Processing Service** (New):
   ```protobuf
   service AIFlashcardService {
     rpc ExtractText(ExtractTextRequest) returns (ExtractTextResponse);
     rpc GenerateFlashcards(GenerateRequest) returns (stream GenerateProgress);
     rpc ReviewGenerated(ReviewRequest) returns (ImportResponse);
   }
   ```

2. **AI Processing Pipeline**:
   - Extract text from PDF/documents (could use existing Python libraries)
   - Send to LLM API with prompt engineering for flashcard generation
   - Parse LLM response into `ForeignNote` structures
   - Store temporarily for review

3. **Review Interface** (Extend existing):
   - Reuse `ImportPage.svelte` as base
   - Add card preview component showing both sides
   - Enable inline editing of fields
   - Batch approve/reject controls

4. **Integration Points**:
   - Hook into existing import flow at `ForeignData::import()`
   - Leverage duplicate detection mechanisms
   - Use existing field mapping for custom note types

### Implementation Locations

1. **Backend Services**:
   - `rslib/src/ai_flashcards/` (new module)
   - Service implementation in `rslib/src/ai_flashcards/service.rs`
   - Protobuf definitions in `proto/anki/ai_flashcards.proto`

2. **Frontend Components**:
   - `ts/routes/ai-flashcards/` (new route)
   - Reuse components from `ts/routes/import-csv/`
   - Add preview cards from `ts/editor/`

3. **Python Integration**:
   - AI API calls in `pylib/anki/ai_flashcards.py`
   - Document parsing libraries integration

4. **Configuration**:
   - Store API keys in preferences
   - Prompt templates in `ftl/core/ai-flashcards.ftl`

## Code References

### Key Entry Points

- `rslib/src/notes/mod.rs:90` - Note addition entry point
- `rslib/src/import_export/text/import.rs:35` - Import orchestration
- `rslib/src/import_export/text/csv/metadata.rs:41` - Preview extraction
- `ts/routes/import-page/ImportPage.svelte:30` - Import UI component
- `ts/editor/NoteEditor.svelte:109` - Field editing logic

### Reusable Components

- `rslib/src/import_export/text/mod.rs:15-26` - ForeignData structure
- `rslib/src/notes/mod.rs:597-622` - Note validation
- `ts/routes/import-csv/FieldMapper.svelte:22` - Field mapping UI
- `ts/routes/import-page/ImportLogPage.svelte:18` - Results display

### Extension Points

- `rslib/src/backend/mod.rs` - Add new backend service
- `proto/anki/` - Add new protobuf definitions
- `ts/routes/` - Add new frontend routes
- `qt/aqt/mediasrv.py:659` - Expose new backend methods

## Technical Considerations

### Performance

- Use streaming for large document processing
- Batch API calls to LLM for efficiency
- Leverage existing transaction batching for imports

### Error Handling

- Network errors from AI API calls
- Parsing errors from LLM responses
- Validation errors for generated content
- Use existing `AnkiError` type hierarchy

### User Experience

- Progress indicators during AI processing
- Preview before import (leverage existing preview)
- Ability to refine prompts and regenerate
- Save/load generation sessions

### Security

- Sanitize AI-generated HTML content
- Validate field counts match note types
- Rate limiting for API calls
- Secure storage of API keys

## Conclusion

Anki's architecture is well-suited for adding AI-powered flashcard generation. The existing import infrastructure, editor components, and text processing capabilities provide a solid foundation. The main implementation work involves:

1. Creating the AI service layer for LLM integration
2. Building the document extraction pipeline
3. Extending the import preview interface for card review
4. Connecting these components through the existing protobuf-based API

The modular architecture allows this feature to be implemented without major changes to core systems, primarily extending existing patterns and reusing proven components.
