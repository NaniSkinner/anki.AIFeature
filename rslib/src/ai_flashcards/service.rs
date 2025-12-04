// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Service implementation for AI flashcard generation.
//!
//! Note: The actual AI operations (test_api_connection, estimate_cost,
//! generate_flashcards, regenerate_card) are implemented in Python
//! (pylib/anki/ai_flashcards/) because:
//! 1. OpenAI SDK has better Python support
//! 2. Document parsing libraries (PyMuPDF, BeautifulSoup) are Python-based
//!
//! This Rust service handles:
//! - Card import (using existing Anki import infrastructure)
//! - Session persistence (file-based JSON storage)
//!
//! The Python layer is called directly from the Qt frontend for AI operations.

use std::fs;
use std::path::PathBuf;

use anki_proto::ai_flashcards::CardStatus;
use anki_proto::ai_flashcards::CardType;
use anki_proto::ai_flashcards::GeneratedCard;
use anki_proto::ai_flashcards::ImportApprovedCardsRequest;
use anki_proto::ai_flashcards::ImportApprovedCardsResponse;
use anki_proto::ai_flashcards::LoadSessionResponse;
use anki_proto::ai_flashcards::SaveSessionRequest;
use serde::Deserialize;
use serde::Serialize;
use snafu::FromString;

use crate::error;
use crate::import_export::text::ForeignNote;
use crate::import_export::text::NameOrId;
use crate::prelude::*;

/// Session file format version for compatibility checking
const SESSION_VERSION: u32 = 1;

/// Maximum session age in seconds (7 days)
const SESSION_MAX_AGE_SECS: i64 = 7 * 24 * 60 * 60;

/// Session file name
const SESSION_FILENAME: &str = "ai_flashcards_session.json";

/// Serializable session format for JSON persistence
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SessionFile {
    version: u32,
    created_timestamp: i64,
    source_name: String,
    source_text: String,
    cards: Vec<SessionCard>,
}

/// Card format for JSON persistence
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SessionCard {
    id: String,
    card_type: String,
    front: String,
    back: String,
    suggested_tags: Vec<String>,
    status: String,
}

impl From<&GeneratedCard> for SessionCard {
    fn from(card: &GeneratedCard) -> Self {
        SessionCard {
            id: card.id.clone(),
            card_type: match card.card_type() {
                CardType::Basic => "basic".to_string(),
                CardType::BasicReversed => "basic_reversed".to_string(),
                CardType::Cloze => "cloze".to_string(),
            },
            front: card.front.clone(),
            back: card.back.clone(),
            suggested_tags: card.suggested_tags.clone(),
            status: match card.status() {
                CardStatus::Pending => "pending".to_string(),
                CardStatus::Approved => "approved".to_string(),
                CardStatus::Rejected => "rejected".to_string(),
            },
        }
    }
}

impl From<SessionCard> for GeneratedCard {
    fn from(card: SessionCard) -> Self {
        GeneratedCard {
            id: card.id,
            card_type: match card.card_type.as_str() {
                "basic" => CardType::Basic.into(),
                "basic_reversed" => CardType::BasicReversed.into(),
                "cloze" => CardType::Cloze.into(),
                _ => CardType::Basic.into(),
            },
            front: card.front,
            back: card.back,
            suggested_tags: card.suggested_tags,
            status: match card.status.as_str() {
                "pending" => CardStatus::Pending.into(),
                "approved" => CardStatus::Approved.into(),
                "rejected" => CardStatus::Rejected.into(),
                _ => CardStatus::Pending.into(),
            },
        }
    }
}

impl Collection {
    /// Get the session file path for this collection
    fn ai_session_path(&self) -> PathBuf {
        self.col_path
            .parent()
            .map(|p| p.to_path_buf())
            .unwrap_or_default()
            .join(SESSION_FILENAME)
    }

    /// Import approved AI-generated cards into the collection
    pub fn import_ai_cards(
        &mut self,
        cards: Vec<GeneratedCard>,
        target_deck_id: DeckId,
        additional_tags: Vec<String>,
    ) -> error::Result<ImportApprovedCardsResponse> {
        self.transact(Op::Import, |col| {
            col.import_ai_cards_inner(cards, target_deck_id, additional_tags)
        })
        .map(|output| output.output)
    }

    /// Inner implementation of card import, runs within a transaction
    fn import_ai_cards_inner(
        &mut self,
        cards: Vec<GeneratedCard>,
        target_deck_id: DeckId,
        additional_tags: Vec<String>,
    ) -> error::Result<ImportApprovedCardsResponse> {
        let mut imported_count = 0u32;
        let mut duplicate_count = 0u32;
        let mut errors: Vec<String> = Vec::new();

        for card in cards {
            // Only import approved cards
            if card.status() != CardStatus::Approved {
                continue;
            }

            // Convert to ForeignNote
            let foreign_note =
                self.ai_card_to_foreign_note(&card, target_deck_id, &additional_tags);

            // Try to import
            match self.import_single_ai_note(foreign_note) {
                Ok(is_duplicate) => {
                    if is_duplicate {
                        duplicate_count += 1;
                    } else {
                        imported_count += 1;
                    }
                }
                Err(e) => {
                    errors.push(format!("Failed to import card '{}': {}", card.id, e));
                }
            }
        }

        Ok(ImportApprovedCardsResponse {
            changes: Some(anki_proto::collection::OpChanges {
                card: true,
                note: true,
                tag: true,
                ..Default::default()
            }),
            imported_count,
            duplicate_count,
            errors,
        })
    }

    /// Convert an AI-generated card to a ForeignNote for import
    fn ai_card_to_foreign_note(
        &self,
        card: &GeneratedCard,
        deck_id: DeckId,
        additional_tags: &[String],
    ) -> ForeignNote {
        // Combine AI suggested tags with additional tags and auto-tags
        let mut all_tags: Vec<String> = vec!["ai-generated".to_string()];
        all_tags.extend(card.suggested_tags.iter().cloned());
        all_tags.extend(additional_tags.iter().cloned());

        // Determine notetype name based on card type
        let notetype_name = match card.card_type() {
            CardType::Basic => "Basic",
            CardType::BasicReversed => "Basic (and reversed card)",
            CardType::Cloze => "Cloze",
        };

        // Create fields based on card type
        let fields = match card.card_type() {
            CardType::Cloze => vec![
                Some(card.front.clone()), // Text field (with cloze deletions)
                Some(card.back.clone()),  // Extra field (usually empty for cloze)
            ],
            _ => vec![
                Some(card.front.clone()), // Front field
                Some(card.back.clone()),  // Back field
            ],
        };

        ForeignNote {
            guid: String::new(), // Will be auto-generated
            fields,
            tags: Some(all_tags),
            notetype: NameOrId::Name(notetype_name.to_string()),
            deck: NameOrId::Id(deck_id.0),
            cards: Vec::new(),
        }
    }

    /// Import a single note, returning whether it was a duplicate
    fn import_single_ai_note(&mut self, foreign_note: ForeignNote) -> error::Result<bool> {
        use crate::notes::Note;

        // Get the notetype by name
        let notetype_name = match &foreign_note.notetype {
            NameOrId::Name(name) => name.clone(),
            NameOrId::Id(id) => id.to_string(),
        };

        let notetype = self
            .get_notetype_by_name(&notetype_name)?
            .or_not_found(notetype_name)?;

        // Get deck ID
        let deck_id = match &foreign_note.deck {
            NameOrId::Id(id) => DeckId(*id),
            NameOrId::Name(name) => self.get_deck_id(name)?.or_not_found(name)?,
        };

        // Create a new note with the notetype
        let mut note = Note::new(&notetype);

        // Set the fields
        for (idx, field_opt) in foreign_note.fields.iter().enumerate() {
            if let Some(field_content) = field_opt {
                if idx < note.fields().len() {
                    note.set_field(idx, field_content.clone())?;
                }
            }
        }

        // Set tags
        if let Some(tags) = foreign_note.tags {
            note.tags = tags;
        }

        // Add the note (this also generates cards)
        self.add_note_inner(&mut note, deck_id)?;

        // Note: Duplicate detection could be added here by checking checksums
        // before adding. For now, we always add the note.
        Ok(false) // Not a duplicate
    }

    /// Save AI session to disk
    pub fn save_ai_session(&self, request: SaveSessionRequest) -> error::Result<()> {
        let session = SessionFile {
            version: SESSION_VERSION,
            created_timestamp: TimestampSecs::now().0,
            source_name: request.source_name,
            source_text: request.source_text,
            cards: request.cards.iter().map(SessionCard::from).collect(),
        };

        let json = serde_json::to_string_pretty(&session)?;
        fs::write(self.ai_session_path(), json)?;

        Ok(())
    }

    /// Load AI session from disk
    pub fn load_ai_session(&self) -> error::Result<LoadSessionResponse> {
        let path = self.ai_session_path();

        if !path.exists() {
            return Ok(LoadSessionResponse {
                has_session: false,
                cards: Vec::new(),
                source_name: String::new(),
                created_timestamp: 0,
                source_text: String::new(),
            });
        }

        let json = fs::read_to_string(&path)?;
        let session: SessionFile = serde_json::from_str(&json)?;

        // Check version compatibility
        if session.version != SESSION_VERSION {
            // Clear incompatible session
            let _ = fs::remove_file(&path);
            return Ok(LoadSessionResponse {
                has_session: false,
                cards: Vec::new(),
                source_name: String::new(),
                created_timestamp: 0,
                source_text: String::new(),
            });
        }

        // Check if session has expired
        let age = TimestampSecs::now().0 - session.created_timestamp;
        if age > SESSION_MAX_AGE_SECS {
            // Clear expired session
            let _ = fs::remove_file(&path);
            return Ok(LoadSessionResponse {
                has_session: false,
                cards: Vec::new(),
                source_name: String::new(),
                created_timestamp: 0,
                source_text: String::new(),
            });
        }

        Ok(LoadSessionResponse {
            has_session: true,
            cards: session.cards.into_iter().map(Into::into).collect(),
            source_name: session.source_name,
            created_timestamp: session.created_timestamp,
            source_text: session.source_text,
        })
    }

    /// Clear AI session from disk
    pub fn clear_ai_session(&self) -> error::Result<()> {
        let path = self.ai_session_path();
        if path.exists() {
            fs::remove_file(path)?;
        }
        Ok(())
    }
}

impl crate::services::AIFlashcardsService for Collection {
    fn test_api_connection(
        &mut self,
        _input: anki_proto::ai_flashcards::TestApiConnectionRequest,
    ) -> error::Result<anki_proto::ai_flashcards::TestApiConnectionResponse> {
        // This is handled by Python directly
        // Return an error indicating the caller should use Python
        Err(AnkiError::InvalidInput {
            source: error::InvalidInputError::without_source(
                "API connection test should be performed via Python layer".to_string(),
            ),
        })
    }

    fn estimate_cost(
        &mut self,
        _input: anki_proto::ai_flashcards::EstimateCostRequest,
    ) -> error::Result<anki_proto::ai_flashcards::EstimateCostResponse> {
        // This is handled by Python directly
        Err(AnkiError::InvalidInput {
            source: error::InvalidInputError::without_source(
                "Cost estimation should be performed via Python layer".to_string(),
            ),
        })
    }

    fn generate_flashcards(
        &mut self,
        _input: anki_proto::ai_flashcards::GenerateFlashcardsRequest,
    ) -> error::Result<anki_proto::ai_flashcards::GenerateFlashcardsResponse> {
        // This is handled by Python directly
        Err(AnkiError::InvalidInput {
            source: error::InvalidInputError::without_source(
                "Flashcard generation should be performed via Python layer".to_string(),
            ),
        })
    }

    fn regenerate_card(
        &mut self,
        _input: anki_proto::ai_flashcards::RegenerateCardRequest,
    ) -> error::Result<anki_proto::ai_flashcards::RegenerateCardResponse> {
        // This is handled by Python directly
        Err(AnkiError::InvalidInput {
            source: error::InvalidInputError::without_source(
                "Card regeneration should be performed via Python layer".to_string(),
            ),
        })
    }

    fn import_approved_cards(
        &mut self,
        input: ImportApprovedCardsRequest,
    ) -> error::Result<ImportApprovedCardsResponse> {
        self.import_ai_cards(
            input.cards,
            DeckId(input.target_deck_id),
            input.additional_tags,
        )
    }

    fn save_session(&mut self, input: SaveSessionRequest) -> error::Result<()> {
        self.save_ai_session(input)
    }

    fn load_session(&mut self) -> error::Result<LoadSessionResponse> {
        self.load_ai_session()
    }

    fn clear_session(&mut self) -> error::Result<()> {
        self.clear_ai_session()
    }
}
