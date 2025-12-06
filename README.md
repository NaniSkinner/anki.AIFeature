# Anki Fork: AI Flashcard Generator

This is a fork of [Anki](https://github.com/ankitects/anki), the powerful open-source spaced repetition flashcard program. This fork adds an **AI-powered flashcard generation feature** that uses OpenAI's GPT-4o to automatically create high-quality flashcards from any text, URL, or document.

---

## What We Built

### AI Flashcard Generator

A complete feature that transforms source material into optimized Anki flashcards using cognitive science principles.

**Key Features:**
- **Multiple Input Sources**: Paste text directly, fetch content from URLs, or upload TXT/MD files
- **Smart Card Generation**: Uses GPT-4o with carefully engineered prompts based on learning science (minimum information principle, active recall, etc.)
- **Three Card Types**: Basic, Basic (and reversed), and Cloze deletion cards
- **Cost Transparency**: Estimate costs before generation, view actual costs after
- **Review Workflow**: Approve, reject, or reset individual cards before importing
- **Session Persistence**: Auto-saves progress; resume anytime within 7 days
- **Deck Integration**: Import to existing decks or create new ones directly from the UI

**User Flow:**
1. Open AI Flashcard Generator (Tools menu or `G` shortcut)
2. Input source material (text/URL/file)
3. Optionally estimate cost
4. Generate flashcards
5. Review and approve/reject cards
6. Select target deck and import

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Svelte/TypeScript)                                   │
│  ts/routes/ai-flashcards/                                       │
│  ├── AIFlashcardsPage.svelte    Main component + state machine  │
│  ├── SourceSelector.svelte      Text/File/URL input tabs        │
│  ├── CardReview.svelte          Approve/reject UI               │
│  └── Header.svelte              Navigation header               │
└────────────────────┬────────────────────────────────────────────┘
                     │ bridgeCommand() for AI operations
                     │ postProto() for session/import RPCs
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Qt Dialog (Python)                                             │
│  qt/aqt/ai_flashcards.py                                        │
│  └── AIFlashcardsDialog                                         │
│      - Bridge command routing                                   │
│      - Background task management (non-blocking UI)             │
│      - API key retrieval from profile                           │
└────────────────────┬───────────────────────────────────────────┘
                     │ Direct Python calls
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Python AI Layer                                                │
│  pylib/anki/ai_flashcards/                                      │
│  ├── openai_client.py     GPT-4o integration, prompt engineering│
│  ├── document_parser.py   PDF/URL/text extraction               │
│  └── models.py            Data classes                          │
└────────────────────────────────────────────────────────────────┘
                     │ Protobuf RPCs
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Rust Backend                                                   │
│  rslib/src/ai_flashcards/                                       │
│  └── service.rs                                                 │
│      - Session persistence (JSON file storage)                  │
│      - Card import (leverages existing ForeignNote system)      │
└────────────────────────────────────────────────────────────────┘
```

### File Structure

```
proto/anki/ai_flashcards.proto      # Service + message definitions
rslib/src/ai_flashcards/            # Rust: session + import
pylib/anki/ai_flashcards/           # Python: OpenAI + parsing
qt/aqt/ai_flashcards.py             # Qt dialog + bridge
ts/routes/ai-flashcards/            # Svelte frontend
ftl/core/ai-flashcards.ftl          # Translations
```

---

## Setup + Run Steps

### Prerequisites

- Python 3.9+
- Rust (latest stable)
- Node.js 18+
- OpenAI API key

### Building

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Anki.git
   cd Anki
   ```

2. **Run the build:**
   ```bash
   ./check
   ```
   This will download dependencies, build all components, and run checks.

3. **Run Anki:**
   ```bash
   ./run
   ```

### Configuration

1. Open Anki
2. Go to **Tools → Preferences**
3. Navigate to the **AI** section
4. Enter your OpenAI API key
5. Save preferences

### Using the AI Flashcard Generator

1. **Open**: Tools → AI Flashcard Generator (or press `G`)
2. **Input**: Choose Text/File/URL tab and provide source material
3. **Estimate** (optional): Click "Estimate Cost" to preview token usage
4. **Generate**: Click "Generate Flashcards"
5. **Review**: Approve/reject individual cards or use bulk actions
6. **Import**: Select target deck and click "Import Approved"

---

## Technical Decisions

### Why Python for AI Operations?

The AI operations (generation, cost estimation, URL parsing) are implemented in Python rather than Rust because:

1. **OpenAI SDK**: The official OpenAI Python SDK is mature and well-supported
2. **Parsing Libraries**: PyMuPDF (PDF) and BeautifulSoup (HTML) are Python-native
3. **Rapid Iteration**: Prompt engineering benefits from Python's flexibility

The Rust layer handles what it does best: data persistence and integration with Anki's existing import infrastructure.

### Prompt Engineering

The system prompt (`pylib/anki/ai_flashcards/openai_client.py`) incorporates cognitive science principles:

- **Minimum Information Principle**: Each card tests one atomic piece of information
- **Active Recall**: Questions require retrieval, not recognition
- **Conciseness**: Shortest possible questions and answers
- **Card Type Selection**: Guidelines for Basic vs Cloze based on content type

### Session Persistence

Sessions are stored as JSON in the collection directory (`ai_flashcards_session.json`) with:
- Version number for compatibility
- 7-day expiration
- Full card state including approval status

This allows users to close Anki and resume their review session later.

### Cost Tracking

- **Pre-generation**: Token estimation using tiktoken (or character-based fallback)
- **Post-generation**: Actual token counts from OpenAI API response
- **Pricing**: Configurable per-model rates (GPT-4o: $2.50/1M input, $10/1M output)

### URL Content Extraction

The URL parser (`document_parser.py`) uses 6 strategies to find main content:
1. Semantic HTML5 (`<main>`, `<article>`)
2. Common content IDs (`#content`, `#main-content`)
3. Common content classes (`.article-content`, `.post-content`)
4. ARIA role (`role="main"`)
5. Largest text container (div with most paragraph content)
6. Fallback to `<body>`

Unwanted elements (nav, footer, ads, scripts) are removed before extraction.

### Background Task Architecture

OpenAI API calls can take 10-30 seconds. To keep the UI responsive:

1. Frontend sends bridge command → returns immediately with "generating" status
2. Python launches background task via `taskman.run_in_background()`
3. Task runs OpenAI call in thread pool
4. On completion, callback runs on main thread
5. Result sent to frontend via `window._aiFlashcardsOnGenerate()` callback

Timeout: 2 minutes.

---

## Original Repository

> This is a fork of [ankitects/anki](https://github.com/ankitects/anki).

Anki is a program which makes remembering things easy. It uses spaced repetition to help you study more efficiently than traditional methods.

For more information about Anki, visit [apps.ankiweb.net](https://apps.ankiweb.net/).

### Original Anki Resources

- [Development Guide](./docs/development.md)
- [Contribution Guidelines](./docs/contributing.md)
- [Contributors](./CONTRIBUTORS)

---

## License

This project is licensed under the [GNU AGPL v3](./LICENSE) - see the original Anki repository for full license details.
