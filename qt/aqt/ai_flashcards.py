# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""AI Flashcard generation dialog."""

from __future__ import annotations

import json
from typing import Any

import aqt
import aqt.main
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind


class AIFlashcardsDialog(QDialog):
    """Dialog for AI-powered flashcard generation."""

    GEOMETRY_KEY = "aiFlashcards"
    DEFAULT_SIZE = (900, 700)
    MIN_SIZE = (600, 400)
    silentlyClose = True

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.web: AnkiWebView | None = None
        self._closed = False
        self._ready = False
        self._setup_ui()
        self.show()

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(*self.MIN_SIZE)
        disable_help_button(self)
        restoreGeom(self, self.GEOMETRY_KEY, default_size=self.DEFAULT_SIZE)

        self.web = AnkiWebView(kind=AnkiWebViewKind.AI_FLASHCARDS)
        self.web.set_bridge_command(self._on_bridge_cmd, self)
        self.web.load_sveltekit_page("ai-flashcards")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

        # TODO: Use tr.ai_flashcards_window_title() once FTL is generated
        self.setWindowTitle("AI Flashcard Generator")

    def _on_bridge_cmd(self, cmd: str) -> Any:
        """Handle bridge commands from the frontend."""
        if not cmd.startswith("ai_flashcards:"):
            return None

        try:
            request = json.loads(cmd[len("ai_flashcards:") :])
            action = request.get("action")

            if action == "ready":
                self.set_ready()
                return json.dumps({"ok": True})
            elif action == "generate_flashcards":
                return self._handle_generate(request)
            elif action == "test_connection":
                return self._handle_test_connection()
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _handle_generate(self, request: dict[str, Any]) -> str:
        """Handle flashcard generation request."""
        text = request.get("text", "")
        source_name = request.get("sourceName", "")

        if not text.strip():
            return json.dumps(
                {"error": "Please provide text to generate flashcards from."}
            )

        try:
            # Get API key from profile
            api_key = self._get_api_key()
            if not api_key:
                return json.dumps(
                    {
                        "error": "OpenAI API key is not configured. Please set it in Preferences."
                    }
                )

            # Import the OpenAI client
            from anki.ai_flashcards.models import GenerationConfig
            from anki.ai_flashcards.openai_client import OpenAIFlashcardClient

            client = OpenAIFlashcardClient(api_key)
            config = GenerationConfig(
                card_limit=20,
                source_name=source_name,
            )

            cards = client.generate_flashcards(text, config)

            # Convert to the format expected by frontend
            result_cards = []
            for card in cards:
                result_cards.append(
                    {
                        "id": card.id,
                        "cardType": _card_type_to_int(card.card_type),
                        "front": card.front,
                        "back": card.back,
                        "suggestedTags": card.suggested_tags,
                        "status": 0,  # pending
                    }
                )

            return json.dumps({"cards": result_cards})

        except Exception as e:
            return json.dumps({"error": f"Flashcard generation failed: {e}"})

    def _handle_test_connection(self) -> str:
        """Test the OpenAI API connection."""
        try:
            api_key = self._get_api_key()
            if not api_key:
                return json.dumps(
                    {
                        "success": False,
                        "error": "OpenAI API key is not configured. Please set it in Preferences.",
                    }
                )

            from anki.ai_flashcards.openai_client import test_api_key

            success, error = test_api_key(api_key)
            return json.dumps({"success": success, "error": error})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _get_api_key(self) -> str | None:
        """Get the OpenAI API key from the profile."""
        try:
            from aqt.secret import deobfuscate_api_key

            # Get obfuscated key from profile meta
            meta = self.mw.pm.meta
            obfuscated = meta.get("openai_api_key", "")
            if not obfuscated:
                return None
            return deobfuscate_api_key(obfuscated)
        except Exception:
            return None

    def _cleanup(self) -> None:
        """Clean up the web view."""
        if self.web is not None:
            self.web.cleanup()
            self.web = None

    def set_ready(self) -> None:
        """Called by frontend when the page is fully loaded."""
        self._ready = True

    def _close_dialog(self) -> None:
        """Common close logic - only runs once."""
        if self._closed:
            return
        self._closed = True
        self._cleanup()
        saveGeom(self, self.GEOMETRY_KEY)
        # Clear reference from main window
        if hasattr(self.mw, "_ai_flashcards_dialog"):
            self.mw._ai_flashcards_dialog = None

    def closeEvent(self, evt: QCloseEvent | None) -> None:
        """Handle window close event (X button, etc.)."""
        # If not ready yet, allow Qt to handle close without cleanup
        # This prevents crashes during early close before webview is ready
        if self._closed or not self._ready:
            return super().closeEvent(evt)
        self._close_dialog()

    def reject(self) -> None:
        """Handle dialog rejection (close button, escape key)."""
        self._close_dialog()
        QDialog.reject(self)


def _card_type_to_int(card_type) -> int:
    """Convert CardType enum to int for frontend."""
    from anki.ai_flashcards.models import CardType

    if card_type == CardType.BASIC:
        return 0
    elif card_type == CardType.BASIC_REVERSED:
        return 1
    elif card_type == CardType.CLOZE:
        return 2
    return 0


def open_ai_flashcards(mw: aqt.main.AnkiQt) -> AIFlashcardsDialog:
    """Open the AI Flashcards dialog."""
    # Check if we already have an open dialog
    existing = getattr(mw, "_ai_flashcards_dialog", None)
    if existing is not None:
        try:
            existing.activateWindow()
            existing.raise_()
            return existing
        except RuntimeError:
            # C++ object deleted, create new one
            pass

    dialog = AIFlashcardsDialog(mw)
    mw._ai_flashcards_dialog = dialog
    return dialog
