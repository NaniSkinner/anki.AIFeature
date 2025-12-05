---
date: 2025-12-05T03:19:32Z
researcher: Claude (Sonnet 4.5)
git_commit: b47e853929d0775daa6a4d9a633c0046886a6f5e
branch: Features
repository: Anki
topic: "UI Architecture Research for Mochi-Inspired Redesign with Svelte + SMUI"
tags: [research, codebase, ui, svelte, smui, redesign, styling, architecture]
status: complete
last_updated: 2025-12-04
last_updated_by: Claude (Sonnet 4.5)
---

# Research: UI Architecture for Mochi-Inspired Redesign with Svelte + SMUI

**Date**: 2025-12-05T03:19:32Z
**Researcher**: Claude (Sonnet 4.5)
**Git Commit**: b47e853929d0775daa6a4d9a633c0046886a6f5e
**Branch**: Features
**Repository**: Anki

## Research Question

How is the current Anki UI architecture structured, and what needs to change to implement a Mochi.cards-inspired redesign using Svelte + SMUI (Svelte Material UI) while maintaining all existing functionality?

## Summary

Anki uses a multi-layered architecture where a **Svelte/TypeScript web frontend** (in `ts/`) is embedded within a **PyQt desktop application** (in `qt/aqt/`). The web components communicate with the Python/Qt layer through a **QWebChannel bridge** and are served via a **local Flask HTTP server** (MediaServer). The current styling system uses **Bootstrap 5** with a comprehensive **CSS custom properties system** for theming, supporting both light and dark modes. The build system combines **Vite** (for SvelteKit development), **esbuild** (for component bundling), and **Ninja** (as the master orchestrator).

For a Mochi-inspired redesign with SMUI, the key changes needed are:

1. Install and integrate SMUI components alongside existing Svelte components
2. Replace current styling gradually, starting with the study/review interface
3. Maintain the existing QWebChannel bridge and PyQt embedding (no changes needed)
4. Keep the build system intact (Vite + esbuild already support any Svelte components)
5. Adapt the theming system to use SMUI's Material Design tokens while preserving dark mode support

## Detailed Findings

### 1. Current Svelte Component Architecture

**Location**: `ts/` directory with SvelteKit-based routing

**Component Organization** (197+ total components):

#### Routes (`ts/routes/`) - SvelteKit Pages

- **File-based routing** using `+page.svelte` convention
- **Main routes**:
  - `card-info/[cardId]/` - Card information display
  - `graphs/` - Statistics and analytics (21 graph components)
  - `deck-options/[deckId]/` - Deck configuration (48 components)
  - `change-notetype/[...notetypeIds]/` - Note type switching
  - `image-occlusion/[...imagePathOrNoteId]/` - Image occlusion editor
  - `import-page/`, `import-csv/`, `import-anki-package/` - Import wizards
  - `congrats/` - Completion screen
  - `ai-flashcards/` - AI flashcard generator (recent addition)

#### Editor Components (`ts/editor/`) - 57 Components

- **Core**: `NoteEditor.svelte`, `EditingArea.svelte`, `Fields.svelte`
- **Toolbar**: 24 formatting and control buttons
- **Overlays**: Image properties, MathJax editing
- **Input modes**: Rich text and plain text editing

#### Shared Component Library (`ts/lib/components/`) - 48+ Components

- **Layout**: Container, Row, Col, Spacer
- **Buttons**: ButtonGroup, IconButton, LabelButton
- **Forms**: CheckBox, Switch, Select, SpinBox, EnumSelector
- **UI Utilities**: Badge, Icon, Popover, Tooltip, Modal helpers
- **Wrappers**: WithTooltip, WithFloating, WithOverlay, WithState

#### Tag Editor (`ts/lib/tag-editor/`) - 10 Components

- Tag input, display, autocomplete, and management

**Key Pattern**: Clear separation between route pages, feature components, and reusable library components.

**References**:

- Component listing: Full inventory in research sub-agent output
- Routes directory: `ts/routes/`
- Library: `ts/lib/components/`
- Editor: `ts/editor/`

---

### 2. Study/Review Interface Implementation

**Primary Location**: `qt/aqt/reviewer.py` (Python backend) + `qt/aqt/data/web/js/reviewer-bottom.ts` (TypeScript)

#### State Machine (reviewer.py:374-407)

The reviewer operates as a finite state machine:

```
Question -> Answer -> Transition -> Question (next card)
```

**State transitions**:

- `_showQuestion()` - Displays card front, shows "Show Answer" button
- `_showAnswer()` - Displays card back, shows ease buttons (Again/Hard/Good/Easy)
- `_answerCard(ease)` - Processes answer, transitions to next card

**Key aspects**:

- State stored in `self.state` variable (lines 374, 395)
- Audio playback integrated with state changes (lines 378-380, 400-402)
- Hooks for UI customization at each state (lines 382, 406)

#### Card Display Flow

1. **Question Phase** (`reviewer.py:374-390`):
   - Fetches HTML via `c.question()` (line 376)
   - Plays question audio if autoplay enabled (lines 378-380)
   - Evaluates JavaScript: `_showQuestion(json_html)` (line 384)
   - Updates flag and mark icons (lines 385-386)
   - Shows "Show Answer" button in bottom bar (line 387)

2. **Answer Phase** (`reviewer.py:392-407`):
   - Fetches HTML via `c.answer()` (line 396)
   - Plays answer audio if autoplay enabled (lines 397-401)
   - Evaluates JavaScript: `_showAnswer(json_html)` (line 404)
   - Shows ease buttons (Again/Hard/Good/Easy) (line 405)

3. **Answering** (`reviewer.py:533-572`):
   - Validates state is "answer" (line 540)
   - Builds answer using V3 scheduler (lines 548-552)
   - Runs in background thread (line 562-564)
   - Handles leech detection (line 558-560)
   - Transitions to next card (line 574)

#### Keyboard Shortcuts (reviewer.py:596-643)

Extensive keyboard-driven interface:

- **Space/Return**: Show answer or select default ease
- **1-4**: Select ease buttons (dynamically mapped)
- **E**: Edit current card
- **R/F5**: Replay audio
- **M**: Context menu
- ***/=/-**: Mark/bury operations
- **!/\@**: Suspend operations
- **I**: Card info
- **U**: Undo

#### Answer Buttons (reviewer.py:886-943)

Dynamic button generation based on scheduler:

- **2 buttons**: Again, Good (for new cards in some configs)
- **3 buttons**: Again, Good, Easy
- **4 buttons**: Again, Hard, Good, Easy (standard)

Each button shows:

- Label (translated via Fluent)
- Keyboard shortcut in title attribute
- Due time estimate from V3 scheduler
- `data-ease` attribute for click handling

#### Bottom Bar UI (reviewer-bottom.ts)

TypeScript component managing:

- Timer display with red highlight at limit
- Button HTML injection
- Selected button tracking via `activeElement`
- Answer submission via `pycmd("ease1")` through `pycmd("ease4")`

**Key Pattern**: The review interface is a hybrid - Python controls the state machine and card scheduling, while TypeScript handles UI rendering and user input.

**References**:

- Main reviewer: `qt/aqt/reviewer.py:374-943`
- Bottom bar: `qt/aqt/data/web/js/reviewer-bottom.ts`
- Scheduler states: `proto/anki/scheduler.proto:264-286`
- V3 state info: `qt/aqt/reviewer.py:84-123`

---

### 3. Styling System and Theming

**Framework**: Bootstrap 5 (customized) + CSS Custom Properties system

#### CSS Architecture

**Core SCSS Files** (`ts/lib/sass/`):

- `_root-vars.scss` - Generates CSS custom properties from SCSS maps
- `_color-palette.scss` - Complete color palette (gray scale + Tailwind colors)
- `_vars.scss` - Design token definitions (460+ lines)
- `base.scss` - Bootstrap integration and resets
- `core.scss` - Core body/typography styles
- `elevation.scss` - Material Design-inspired shadow system

#### Theme System

**Detection Mechanism**:

1. **Python** (`qt/aqt/theme.py:52-56`): Determines system theme, sets night_mode preference
2. **HTML class**: Applies `night-mode` class to document root
3. **CSS variables** (`ts/lib/sass/_root-vars.scss:1-65`): Switches all color tokens
4. **Svelte store** (`ts/lib/sveltelib/theme.ts:7-35`): Monitors class changes via MutationObserver

**Theme Class Application** (`qt/aqt/theme.py:162-184`):

```python
classes = ["isWin"/"isMac"/"isLin", "nightMode", "fancy", "reduce-motion"]
```

#### Design Tokens (`ts/lib/sass/_vars.scss:14-460`)

Comprehensive token system with light/dark variants:

**Color tokens**:

- `--fg`, `--fg-subtle`, `--fg-disabled`, `--fg-link`
- `--canvas`, `--canvas-elevated`, `--canvas-inset`, `--canvas-overlay`, `--canvas-code`
- `--border`, `--border-subtle`, `--border-strong`, `--border-focus`
- `--button-bg`, `--button-gradient-start`, `--button-gradient-end`
- `--accent-*`, `--flag-*`, `--state-*` (semantic colors)

**Property tokens**:

- `--border-radius`, `--border-radius-medium`, `--border-radius-large`
- `--transition`, `--transition-medium`, `--transition-slow`
- `--blur` (glass effect)

**Example token definition**:

```scss
fg: (
    default: (
        "Default text/icon color",
        (
            light: palette(darkgray, 9),
            dark: palette(lightgray, 0),
        ),
    ),
)
```

#### Component Styling Pattern

**Scoped styles with CSS variables** (`ts/lib/components/Switch.svelte:26-60`):

```svelte
<style lang="scss">
    .form-check-input {
        background-color: var(--canvas-elevated);
        border-color: var(--border);
    }

    .nightMode:not(:checked) {
        background-color: var(--canvas-elevated);
        border-color: var(--border);
    }
</style>
```

**Global theme targeting**:

```scss
:global(.night-mode) .help-badge {
    color: var(--fg);
}
```

#### Qt Stylesheet System

**Dynamic generation** (`qt/aqt/stylesheets.py:31-124`):

- Python generates Qt stylesheets using theme variables
- `ThemeManager.var()` selects light/dark values
- Separate methods for: general, menu, button, checkbox, combobox, etc.

**Key Pattern**: Dual theming system - CSS custom properties for web components, Qt stylesheets for native widgets.

**References**:

- Root variables: `ts/lib/sass/_root-vars.scss`
- Token definitions: `ts/lib/sass/_vars.scss:14-460`
- Color palette: `ts/lib/sass/_color-palette.scss`
- Theme detection: `ts/lib/sveltelib/theme.ts:7-35`
- Qt styling: `qt/aqt/stylesheets.py:31-124`
- Theme manager: `qt/aqt/theme.py:52-184`

---

### 4. PyQt GUI Embedding and Web Component Integration

**Architecture**: QWebEngine framework embeds Svelte components, QWebChannel provides bidirectional IPC

#### Bridge Initialization

**QWebChannel Setup** (`qt/aqt/webview.py:169-196`):

1. Creates nested `Bridge` QObject class (lines 183-190)
2. Implements `cmd()` method with `@pyqtSlot(str, result=str)` decorator
3. Registers Bridge as "py" object in QWebChannel (line 195)
4. Injects bridge script at DocumentReady (lines 79-115)

**Bridge script injection**:

```javascript
new QWebChannel(qt.webChannelTransport, function(channel) {
    window.py = channel.objects.py;
    pycmd = function(cmd, cb) {
        return py.cmd(cmd, cb);
    };
    bridgeCommand = function(cmd, cb) {
        return pycmd(cmd, cb);
    };
});
```

#### Communication Flow

**JavaScript → Python**:

1. JS calls `pycmd("command_string", callback)` (webview.py:93-103)
2. Routes through QWebChannel to `Bridge.cmd()` slot (line 189)
3. Calls registered handler `self.onBridgeCmd` (line 808)
4. Returns JSON response to JS callback

**Python → JavaScript**:

1. Python calls `webview.eval(js_code)` (lines 732-736)
2. Queued until DOM ready (`_domDone` flag)
3. Executes via `page.runJavaScript()` (line 752)

#### Asset Delivery via MediaServer

**Flask HTTP server** (`qt/aqt/mediasrv.py:93-163`):

- Runs on localhost (127.0.0.1) with ephemeral port
- Serves bundled assets, add-on files, and user media
- Bearer token authentication for API requests
- CORS enabled for localhost only

**Request routing** (mediasrv.py:327-351):

- `/_anki/` - Built-in CSS/JS from `data/web/` folder
- `/_addons/` - Add-on exports
- `/` - User media collection
- POST endpoints - Backend communication

**SvelteKit page loading** (`webview.py:883-898`):

1. Checks HMR mode → uses dev server at `http://127.0.0.1:5173/`
2. Otherwise uses MediaServer URL
3. Adds `#night` hash for night mode
4. Loads URL and waits for `domDone` signal

#### Web View Profiles

**Dual profile system** (`webview.py:136-167`):

- `_profile_with_api_access` - For sensitive pages (EDITOR, DECK_OPTIONS, AI_FLASHCARDS, etc.)
- `_profile_without_api_access` - For regular pages

**API-enabled profile**:

- Adds `Authorization: Bearer {_APIKEY}` header via `AuthInterceptor`
- Validates requests match localhost
- Enables backend POST requests

#### Constraints

**Security**:

- Origin restriction to 127.0.0.1 and [::1]
- Content Security Policy restricts script sources
- Bearer token validation for API calls

**Functional**:

- Actions queued until "domDone" signal (lines 754-769)
- HTML size limits worked around via URL-based loading
- HMR mode requires separate dev server

**Key Pattern**: The PyQt layer acts as a container and bridge, while Svelte components handle all UI logic. No changes needed to this system for SMUI integration.

**References**:

- Bridge setup: `qt/aqt/webview.py:79-196`
- QWebChannel: `qt/aqt/webview.py:169-196`
- MediaServer: `qt/aqt/mediasrv.py:93-351`
- SvelteKit loading: `qt/aqt/webview.py:883-898`
- Profile management: `qt/aqt/webview.py:136-167`

---

### 5. Build System and Bundling

**Architecture**: Vite (SvelteKit dev/build) + esbuild (component bundling) + Ninja (orchestration)

#### Build Outputs

**Two output types**:

1. **SvelteKit SPA** → `out/sveltekit/` (full application with routing)
2. **Standalone bundles** → `ts/*/` directories (individual pages for PyQt embedding)

#### Vite Configuration (`ts/vite.config.ts`)

**Build settings**:

- Targets: `["es2020", "edge88", "firefox78", "chrome77", "safari14"]` (line 26)
- Chrome 77 support for Qt 5.14 compatibility
- Dev server on 127.0.0.1:5173 with HMR
- Proxy at `/_anki` → `http://127.0.0.1:40000` for MediaServer

**SvelteKit adapter** (`ts/svelte.config.js:17-19`):

- Uses `adapter-static` for static site generation
- Outputs to `../out/sveltekit`
- Fallback to `index.html` for SPA routing

#### esbuild Bundling

**Svelte component bundles** (`ts/bundle_svelte.mjs`):

- Bundle dependencies together (line 46)
- Global export as "anki" object (line 48)
- Minify in release builds (line 50)
- Svelte plugin with preprocessing
- Target ES2020 for Chrome 77

**Pure TypeScript bundles** (`ts/bundle_ts.mjs`):

- No Svelte processing
- Target `["es6", "chrome77"]`
- Used for reviewer and utilities

#### Ninja Orchestration (`build/configure/src/web.rs`)

**Build sequence** (web.rs:25-38):

1. Setup Node.js and Yarn
2. Compile Sass stylesheets
3. Build TypeScript library
4. Build SvelteKit application
5. Build individual pages (editable, congrats, editor, reviewer)
6. Run checks (type checking, linting, formatting)

**SvelteKit build** (web.rs:40-52):

- Dependencies: `ts/tsconfig.json`, all `ts/` files, `:ts:lib` target
- Command: `$yarn build` (invokes `vite build`)
- Output: `out/sveltekit/` folder

#### Code Quality Checks

**Type checking** (node.rs:239-282):

- `svelte-check` for Svelte components
- `tsc --noEmit` for TypeScript

**Linting** (node.rs:284-307):

- ESLint with zero warnings
- Modes: check and fix

**Formatting** (node.rs:195-237):

- DPrint for TS/JS/Markdown/JSON/TOML
- Prettier for `.svelte` files

**Testing** (node.rs:309-324):

- Vitest for unit tests

#### Protobuf Code Generation

**TypeScript protobuf** (web.rs:131-155):

- Input: All `.proto` files from `proto/`
- Output: `out/ts/lib/generated/`
- Runs protoc with `@bufbuild/protoc-gen-es`
- Post-processing with `ts/tools/markpure.ts`

**Key Pattern**: The build system is flexible - adding SMUI won't require changes since esbuild and Vite both support any Svelte components. Just install SMUI and import it.

**References**:

- Vite config: `ts/vite.config.ts`
- SvelteKit config: `ts/svelte.config.js`
- Svelte bundler: `ts/bundle_svelte.mjs`
- Build orchestration: `build/configure/src/web.rs:25-52`
- Node setup: `build/ninja_gen/src/node.rs`

---

## Architecture Documentation

### Current Component Hierarchy

```
Desktop Application (PyQt)
├── AnkiQt Main Window
│   ├── MainWebView (reviewer, deck browser)
│   ├── TopWebView (toolbar)
│   └── BottomWebView (reviewer controls)
│
├── Dialogs (each with dedicated AnkiWebView)
│   ├── Editor Dialog
│   ├── Stats Dialog
│   ├── AI Flashcards Dialog
│   └── Card Info Dialog
│
└── MediaServer (Flask HTTP)
    ├── SvelteKit App (/_anki/sveltekit/)
    ├── Bundled Assets (/_anki/)
    ├── Add-on Files (/_addons/)
    └── User Media (/)
```

### Data Flow

```
User Interaction (Browser/Qt)
    ↓
JavaScript (Svelte Component)
    ↓ pycmd("command")
QWebChannel Bridge
    ↓
Python Handler (reviewer.py, etc.)
    ↓
Rust Backend (via protobuf)
    ↓
Database/Scheduler
    ↓
Python Response
    ↓ webview.eval("js_code")
JavaScript Updates UI
```

### Styling Layers

```
1. CSS Custom Properties (:root)
   ├── Light mode values (default)
   └── Dark mode values (.night-mode class)

2. Bootstrap 5 Base
   ├── Reboot (normalize)
   └── Utilities (spacing, flexbox, etc.)

3. Custom SCSS
   ├── Component-scoped styles
   ├── Global utilities
   └── Elevation system

4. Qt Stylesheets (for native widgets)
   └── Generated from same theme tokens
```

### Build Artifacts

```
out/
├── sveltekit/               # Full SPA
│   ├── index.html
│   ├── _app/               # JS bundles
│   └── assets/             # CSS, images
│
ts/
├── editable/
│   ├── editable.js         # Standalone bundle
│   └── editable.css
├── congrats/
│   ├── congrats.js
│   ├── congrats.css
│   └── congrats.html
├── editor/
│   ├── editor.js
│   └── editor.css
└── reviewer/
    ├── reviewer.js
    ├── reviewer.css
    ├── reviewer_extras_bundle.js
    └── reviewer_extras.css
```

---

## Implementation Strategy for SMUI Integration

### Phase 1: Setup and Installation

**Install SMUI packages**:

```bash
cd ts
yarn add -D @smui/button @smui/card @smui/fab @smui/icon-button @smui/paper @smui/ripple @smui/theme @smui/typography
```

**SMUI theme configuration** (`ts/smui-theme.scss`):

- Define primary, secondary, and surface colors matching Mochi aesthetic
- Map existing CSS custom properties to SMUI theme variables
- Configure dark mode variant

### Phase 2: Theme Bridge

**Create theme adapter** (`ts/lib/smui/theme-adapter.ts`):

- Monitor `$pageTheme` store
- Apply SMUI theme classes based on light/dark mode
- Bridge existing `--canvas`, `--fg`, etc. to Material Design tokens

**Update root variables**:

- Add Material Design color mappings
- Preserve existing token names for backward compatibility
- Ensure smooth transition

### Phase 3: Component Migration (Study Interface Priority)

**Start with reviewer bottom bar**:

1. Create `ts/reviewer/ReviewerBottomSMUI.svelte`
2. Replace button HTML with SMUI Button components
3. Apply Material Design styling (elevation, ripple effects)
4. Test keyboard shortcuts and touch interactions

**Card display**:

1. Wrap card content in SMUI Card component
2. Add elevation and rounded corners
3. Implement smooth transitions between question/answer states

**Answer buttons**:

1. Replace HTML buttons with SMUI Button (variant="unelevated" or "raised")
2. Add ripple effects for touch feedback
3. Maintain keyboard shortcuts and ease handling

### Phase 4: Incremental Rollout

**Component replacement order**:

1. Study interface (highest priority)
2. Deck browser and management
3. Card editor
4. Settings and preferences
5. Statistics and graphs
6. Import/export dialogs

**For each component**:

- Create new SMUI version alongside existing
- Add feature flag to toggle between old/new
- Test thoroughly before removing old version
- Maintain all existing functionality

### Phase 5: Build Integration

**No build changes needed**:

- esbuild handles SMUI components automatically
- Vite dev server supports SMUI with HMR
- SCSS compilation works with SMUI theme files

**Optional optimization**:

- Tree-shake unused SMUI components
- Bundle common SMUI components separately for caching

---

## Code References

### Component Structure

- Routes: `ts/routes/` (197+ components across all routes)
- Shared library: `ts/lib/components/` (48 components)
- Editor: `ts/editor/` (57 components)
- Tag editor: `ts/lib/tag-editor/` (10 components)

### Study Interface

- Main reviewer: `qt/aqt/reviewer.py:374-943`
- Bottom bar: `qt/aqt/data/web/js/reviewer-bottom.ts`
- State machine: `qt/aqt/reviewer.py:374-407`
- Keyboard shortcuts: `qt/aqt/reviewer.py:596-643`
- Answer buttons: `qt/aqt/reviewer.py:886-943`

### Styling System

- Root variables: `ts/lib/sass/_root-vars.scss`
- Design tokens: `ts/lib/sass/_vars.scss:14-460`
- Color palette: `ts/lib/sass/_color-palette.scss`
- Theme detection: `ts/lib/sveltelib/theme.ts:7-35`
- Bootstrap integration: `ts/lib/sass/base.scss`
- Qt stylesheets: `qt/aqt/stylesheets.py:31-124`

### PyQt Embedding

- Bridge setup: `qt/aqt/webview.py:79-196`
- MediaServer: `qt/aqt/mediasrv.py:93-351`
- Profile management: `qt/aqt/webview.py:136-167`
- Page loading: `qt/aqt/webview.py:883-898`

### Build System

- Vite config: `ts/vite.config.ts`
- SvelteKit config: `ts/svelte.config.js`
- Svelte bundler: `ts/bundle_svelte.mjs`
- Build orchestration: `build/configure/src/web.rs:25-52`
- Package config: `package.json:8-16`

---

## Key Insights

### What Works Well

1. **Clean separation of concerns**: Web UI, PyQt container, and Rust backend are clearly separated
2. **Flexible component system**: Svelte components can be added/modified without touching PyQt
3. **Robust theming**: CSS custom properties make theme switching seamless
4. **Strong build system**: Ninja + esbuild + Vite provide fast, reliable builds

### What Needs Attention for SMUI

1. **Bootstrap removal**: Gradual migration away from Bootstrap utilities to Material Design
2. **Theme token mapping**: Align existing tokens with Material Design color system
3. **Component props**: SMUI uses different prop patterns than current custom components
4. **Ripple effects**: Add touch feedback throughout (SMUI provides this automatically)
5. **Elevation system**: Already exists (`ts/lib/sass/elevation.scss`) - map to SMUI elevation

### No Changes Needed

1. **PyQt embedding layer**: QWebChannel bridge works with any web framework
2. **Build system**: esbuild and Vite support SMUI out of the box
3. **MediaServer**: Asset delivery unchanged
4. **Backend communication**: Protobuf IPC is UI-agnostic

---

## Related Research

None (initial research document)

---

## Open Questions

1. **Performance impact**: How will SMUI component overhead affect load times in Qt WebEngine?
2. **Bundle size**: What's the size increase from adding SMUI? (Can be measured after installation)
3. **Custom theming depth**: How much customization is needed to match Mochi's exact aesthetic?
4. **Accessibility**: Does SMUI improve or maintain current accessibility features?
5. **Add-on compatibility**: Will existing add-ons that modify UI continue to work?

---

## Conclusion

The current architecture is well-suited for incremental SMUI adoption. The Svelte + CSS custom properties foundation provides a smooth migration path, and the build system requires no changes. The primary work will be:

1. Installing SMUI and creating a theme bridge
2. Migrating components one at a time, starting with the study interface
3. Ensuring visual consistency across light/dark modes
4. Maintaining all existing functionality and keyboard shortcuts

The PyQt embedding layer and backend communication remain untouched, minimizing risk and allowing focused UI improvements.
