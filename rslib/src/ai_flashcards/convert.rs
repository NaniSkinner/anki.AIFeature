// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Convert AI-generated cards to ForeignNote format for import.

use super::parse::AIGeneratedCard;
use super::parse::CardType;
use crate::import_export::text::ForeignNote;
use crate::import_export::text::NameOrId;

/// Configuration for converting AI cards to import format.
#[derive(Debug, Clone)]
pub struct ConvertConfig {
    /// Target deck for import (by ID or name).
    pub target_deck: NameOrId,
    /// Additional tags to apply to all cards.
    pub auto_tags: Vec<String>,
    /// Source name for tagging (e.g., filename).
    pub source_name: Option<String>,
}

impl Default for ConvertConfig {
    fn default() -> Self {
        Self {
            target_deck: NameOrId::Name("Default".to_string()),
            auto_tags: vec!["ai-generated".to_string()],
            source_name: None,
        }
    }
}

/// Convert an AI-generated card to ForeignNote format for import.
///
/// This maps the card type to the appropriate notetype and
/// formats the fields correctly.
///
/// # Arguments
/// * `card` - The AI-generated card to convert
/// * `config` - Configuration for the conversion
///
/// # Returns
/// A ForeignNote ready for import
pub fn to_foreign_note(card: &AIGeneratedCard, config: &ConvertConfig) -> ForeignNote {
    // Build the complete tag list
    let mut tags: Vec<String> = config.auto_tags.clone();

    // Add source tag if provided
    if let Some(ref source) = config.source_name {
        let source_tag = format!("source::{}", sanitize_source_for_tag(source));
        tags.push(source_tag);
    }

    // Add suggested tags from AI
    tags.extend(card.suggested_tags.clone());

    // Determine notetype based on card type
    let notetype = match card.card_type {
        CardType::Basic => NameOrId::Name("Basic".to_string()),
        CardType::BasicReversed => NameOrId::Name("Basic (and reversed card)".to_string()),
        CardType::Cloze => NameOrId::Name("Cloze".to_string()),
    };

    // Build fields based on card type
    let fields = match card.card_type {
        CardType::Basic | CardType::BasicReversed => {
            vec![Some(card.front.clone()), Some(card.back.clone())]
        }
        CardType::Cloze => {
            // Cloze cards have Text and Extra fields
            vec![Some(card.front.clone()), Some(card.back.clone())]
        }
    };

    ForeignNote {
        guid: generate_guid(),
        fields,
        tags: Some(tags),
        notetype,
        deck: config.target_deck.clone(),
        cards: vec![],
    }
}

/// Generate a GUID for a new note.
fn generate_guid() -> String {
    use std::time::SystemTime;
    use std::time::UNIX_EPOCH;

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();

    // Simple base62-like encoding for the GUID
    let chars: Vec<char> = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        .chars()
        .collect();
    let mut result = String::new();
    let mut n = timestamp as u64;

    for _ in 0..10 {
        result.push(chars[(n % 62) as usize]);
        n /= 62;
    }

    result
}

/// Sanitize a source name for use as a tag.
fn sanitize_source_for_tag(source: &str) -> String {
    source
        .chars()
        .map(|c| {
            if c.is_alphanumeric() || c == '_' || c == '-' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

/// Batch convert multiple AI cards to ForeignNotes.
#[allow(dead_code)]
pub fn batch_convert(cards: &[AIGeneratedCard], config: &ConvertConfig) -> Vec<ForeignNote> {
    cards
        .iter()
        .map(|card| to_foreign_note(card, config))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_basic_card() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "What is Rust?".to_string(),
            back: "A programming language".to_string(),
            suggested_tags: vec!["programming".to_string()],
        };

        let config = ConvertConfig::default();
        let note = to_foreign_note(&card, &config);

        assert_eq!(note.notetype, NameOrId::Name("Basic".to_string()));
        assert_eq!(note.fields.len(), 2);
        assert_eq!(note.fields[0], Some("What is Rust?".to_string()));
        assert_eq!(note.fields[1], Some("A programming language".to_string()));
        assert!(note
            .tags
            .as_ref()
            .unwrap()
            .contains(&"ai-generated".to_string()));
        assert!(note
            .tags
            .as_ref()
            .unwrap()
            .contains(&"programming".to_string()));
    }

    #[test]
    fn test_convert_cloze_card() {
        let card = AIGeneratedCard {
            card_type: CardType::Cloze,
            front: "The {{c1::mitochondria}} is the powerhouse".to_string(),
            back: "".to_string(),
            suggested_tags: vec![],
        };

        let config = ConvertConfig::default();
        let note = to_foreign_note(&card, &config);

        assert_eq!(note.notetype, NameOrId::Name("Cloze".to_string()));
        assert!(note.fields[0].as_ref().unwrap().contains("{{c1::"));
    }

    #[test]
    fn test_convert_with_source_tag() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "Q".to_string(),
            back: "A".to_string(),
            suggested_tags: vec![],
        };

        let config = ConvertConfig {
            source_name: Some("chapter 1.pdf".to_string()),
            ..Default::default()
        };
        let note = to_foreign_note(&card, &config);

        assert!(note
            .tags
            .as_ref()
            .unwrap()
            .iter()
            .any(|t| t.starts_with("source::")));
    }

    #[test]
    fn test_batch_convert() {
        let cards = vec![
            AIGeneratedCard {
                card_type: CardType::Basic,
                front: "Q1".to_string(),
                back: "A1".to_string(),
                suggested_tags: vec![],
            },
            AIGeneratedCard {
                card_type: CardType::Basic,
                front: "Q2".to_string(),
                back: "A2".to_string(),
                suggested_tags: vec![],
            },
        ];

        let config = ConvertConfig::default();
        let notes = batch_convert(&cards, &config);

        assert_eq!(notes.len(), 2);
    }
}
