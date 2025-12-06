# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""AI Flashcard generation dialog."""

from __future__ import annotations

import json
from concurrent.futures import Future
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

        print(f"[AI Flashcards] Bridge command received: {cmd[:100]}...")

        try:
            request = json.loads(cmd[len("ai_flashcards:") :])
            action = request.get("action")
            print(f"[AI Flashcards] Action: {action}")

            if action == "ready":
                self.set_ready()
                return json.dumps({"ok": True})
            elif action == "generate_flashcards":
                return self._handle_generate(request)
            elif action == "estimate_cost":
                return self._handle_estimate_cost(request)
            elif action == "fetch_url":
                return self._handle_fetch_url(request)
            elif action == "test_connection":
                return self._handle_test_connection()
            elif action == "refresh_decks":
                # Trigger main window to refresh deck browser
                self.mw.reset()
                return json.dumps({"ok": True})
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            print(f"[AI Flashcards] Error in _on_bridge_cmd: {e}")
            return json.dumps({"error": str(e)})

    def _handle_generate(self, request: dict[str, Any]) -> str:
        """Handle flashcard generation request - starts async operation."""
        print("[AI Flashcards] _handle_generate called")
        text = request.get("text", "")
        source_name = request.get("sourceName", "")
        print(f"[AI Flashcards] Text length: {len(text)}, source_name: {source_name}")

        if not text.strip():
            print("[AI Flashcards] Error: No text provided")
            return json.dumps(
                {"error": "Please provide text to generate flashcards from."}
            )

        # Get API key upfront (this is fast)
        api_key = self._get_api_key()
        print(f"[AI Flashcards] API key present: {bool(api_key)}")
        if not api_key:
            print("[AI Flashcards] Error: No API key configured")
            return json.dumps(
                {
                    "error": "OpenAI API key is not configured. Please set it in Preferences."
                }
            )

        # Start background task - returns immediately so Qt event loop isn't blocked
        print("[AI Flashcards] Starting background task")
        self.mw.taskman.run_in_background(
            task=lambda: self._generate_flashcards_task(text, source_name, api_key),
            on_done=self._on_generate_done,
            uses_collection=False,  # Network request, not collection access
        )

        # Return "generating" status - frontend will wait for callback
        print("[AI Flashcards] Returning 'generating' status")
        return json.dumps({"status": "generating"})

    def _generate_flashcards_task(
        self, text: str, source_name: str, api_key: str
    ) -> dict[str, Any]:
        """Background task that calls OpenAI API. Runs in thread pool."""
        print("[AI Flashcards] _generate_flashcards_task started (background thread)")
        try:
            from anki.ai_flashcards.models import GenerationConfig
            from anki.ai_flashcards.openai_client import OpenAIFlashcardClient

            print("[AI Flashcards] Creating OpenAI client")
            client = OpenAIFlashcardClient(api_key)
            config = GenerationConfig(
                card_limit=20,
                source_name=source_name,
            )

            print("[AI Flashcards] Calling generate_flashcards")
            result = client.generate_flashcards(text, config)
            print(f"[AI Flashcards] Generated {len(result.cards)} cards")

            return {
                "success": True,
                "cards": result.cards,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
                "model": result.model,
            }
        except Exception as e:
            print(f"[AI Flashcards] Error in background task: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _on_generate_done(self, future: Future) -> None:
        """Called on main thread when generation completes."""
        print("[AI Flashcards] _on_generate_done called")
        # Check if dialog was closed while generating
        if self._closed or self.web is None:
            print("[AI Flashcards] Dialog closed, aborting callback")
            return

        try:
            result = future.result()
            print(f"[AI Flashcards] Future result success: {result.get('success')}")
            if result["success"]:
                cards_json = [
                    {
                        "id": card.id,
                        "cardType": _card_type_to_int(card.card_type),
                        "front": card.front,
                        "back": card.back,
                        "suggestedTags": card.suggested_tags,
                        "status": 0,  # pending
                    }
                    for card in result["cards"]
                ]
                response = json.dumps(
                    {
                        "cards": cards_json,
                        "tokens_used": result.get("tokens_used", 0),
                        "cost_usd": result.get("cost_usd", 0),
                        "model": result.get("model", ""),
                    }
                )
                print(f"[AI Flashcards] Sending {len(cards_json)} cards to frontend")
            else:
                response = json.dumps({"error": result["error"]})
                print(f"[AI Flashcards] Sending error to frontend: {result['error']}")
        except Exception as e:
            print(f"[AI Flashcards] Exception in _on_generate_done: {e}")
            response = json.dumps({"error": str(e)})

        # Send result to frontend via JavaScript callback
        print("[AI Flashcards] Calling window._aiFlashcardsOnGenerate")
        self.web.eval(f"window._aiFlashcardsOnGenerate({response})")

    def _handle_fetch_url(self, request: dict[str, Any]) -> str:
        """Handle URL fetch request."""
        url = request.get("url", "")

        if not url.strip():
            return json.dumps({"error": "Please provide a URL to fetch."})

        try:
            from anki.ai_flashcards.document_parser import get_source_name, parse_url

            text = parse_url(url)
            source_name = get_source_name(url, "url")

            return json.dumps({"text": text, "sourceName": source_name})

        except Exception as e:
            return json.dumps({"error": f"Failed to fetch URL: {e}"})

    def _handle_estimate_cost(self, request: dict[str, Any]) -> str:
        """Handle cost estimation request."""
        text = request.get("text", "")

        if not text.strip():
            return json.dumps({"error": "No text provided for estimation."})

        try:
            from anki.ai_flashcards.openai_client import OpenAIFlashcardClient

            # We don't need a valid API key for estimation, just use a placeholder
            client = OpenAIFlashcardClient("estimation-only")
            estimate = client.estimate_cost(text)
            return json.dumps(estimate.to_dict())
        except Exception as e:
            return json.dumps({"error": f"Failed to estimate cost: {e}"})

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
            # Use the profile manager's method to get the API key
            api_key = self.mw.pm.ai_openai_api_key()
            print(f"[AI Flashcards] _get_api_key: key present = {bool(api_key)}")
            return api_key
        except Exception as e:
            print(f"[AI Flashcards] _get_api_key exception: {e}")
            import traceback

            traceback.print_exc()
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
