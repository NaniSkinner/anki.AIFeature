# AI Flashcard Generation

# Window and toolbar
ai-flashcards-window-title = AI Flashcard Generator
ai-flashcards-toolbar-button = Generate

# Source selection
ai-flashcards-select-source = Select Source Material
ai-flashcards-tab-text = Text
ai-flashcards-tab-file = File
ai-flashcards-tab-url = URL
ai-flashcards-paste-text-here = Paste or type your text here...
ai-flashcards-source-name-placeholder = Source name (optional)
ai-flashcards-drag-drop-or-click = Drag and drop a file here, or click to select
ai-flashcards-supported-formats = Supported formats: TXT, MD, PDF, HTML
ai-flashcards-enter-url = Enter a URL to fetch content from
ai-flashcards-fetch-url = Fetch
ai-flashcards-generate-cards = Generate Flashcards
ai-flashcards-untitled-source = Untitled

# Generation
ai-flashcards-generating = Generating flashcards...
ai-flashcards-loading = Loading...

# Card review
ai-flashcards-pending = Pending
ai-flashcards-approved = Approved
ai-flashcards-rejected = Rejected
ai-flashcards-approve = Approve
ai-flashcards-reject = Reject
ai-flashcards-reset = Reset
ai-flashcards-approve-all = Approve All
ai-flashcards-reject-all = Reject All
ai-flashcards-front = Front
ai-flashcards-back = Back

# Card types
ai-flashcards-card-type-basic = Basic
ai-flashcards-card-type-reversed = Basic (and reversed)
ai-flashcards-card-type-cloze = Cloze

# Import
ai-flashcards-target-deck = Target Deck
ai-flashcards-import-approved = Import Approved
ai-flashcards-importing = Importing cards...
ai-flashcards-import-complete = Import Complete!
ai-flashcards-imported-count = { $count ->
    [one] { $count } card imported
    *[other] { $count } cards imported
}
ai-flashcards-duplicates-skipped = { $count ->
    [one] { $count } duplicate skipped
    *[other] { $count } duplicates skipped
}

# Session
ai-flashcards-new-session = New Session
ai-flashcards-start-new = Start New Generation

# Errors
ai-flashcards-no-approved-cards = No cards have been approved yet.
ai-flashcards-no-text-provided = Please provide text to generate flashcards from.
ai-flashcards-unsupported-file-type = This file type is not yet supported. Please use TXT or MD files.
ai-flashcards-url-fetch-not-implemented = URL fetching is not yet implemented.
ai-flashcards-api-key-not-configured = OpenAI API key is not configured. Please set it in Preferences.
ai-flashcards-generation-failed = Flashcard generation failed: { $error }

# Preferences
ai-flashcards-preferences-title = AI Flashcards
ai-flashcards-api-key = OpenAI API Key
ai-flashcards-api-key-placeholder = sk-...
ai-flashcards-test-connection = Test Connection
ai-flashcards-connection-success = Connection successful!
ai-flashcards-connection-failed = Connection failed: { $error }
