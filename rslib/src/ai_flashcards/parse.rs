// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Parsing of OpenAI API responses for flashcard generation.

use serde::Deserialize;
use serde::Serialize;
use snafu::FromString;

use crate::error::AnkiError;
use crate::error::InvalidInputError;
use crate::error::Result;

/// Type of flashcard.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum CardType {
    #[default]
    Basic,
    BasicReversed,
    Cloze,
}

impl CardType {
    /// Convert from string representation.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "basic" => CardType::Basic,
            "basic_reversed" => CardType::BasicReversed,
            "cloze" => CardType::Cloze,
            _ => CardType::Basic, // Default to basic for unknown types
        }
    }
}

/// A single AI-generated flashcard parsed from API response.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct AIGeneratedCard {
    /// Type of card (basic, basic_reversed, cloze)
    #[serde(rename = "type")]
    pub card_type: CardType,
    /// Front side content (or full cloze text for cloze cards)
    pub front: String,
    /// Back side content (empty for cloze cards)
    #[serde(default)]
    pub back: String,
    /// Suggested tags from AI
    #[serde(default)]
    pub suggested_tags: Vec<String>,
}

/// Response structure from OpenAI API.
#[derive(Debug, Clone, Deserialize)]
struct OpenAIResponse {
    cards: Vec<RawCard>,
}

/// Raw card from API before normalization.
#[derive(Debug, Clone, Deserialize)]
struct RawCard {
    #[serde(rename = "type")]
    card_type: String,
    front: String,
    #[serde(default)]
    back: String,
    #[serde(default)]
    suggested_tags: Vec<String>,
}

impl From<RawCard> for AIGeneratedCard {
    fn from(raw: RawCard) -> Self {
        AIGeneratedCard {
            card_type: CardType::from_str(&raw.card_type),
            front: raw.front,
            back: raw.back,
            suggested_tags: raw.suggested_tags,
        }
    }
}

/// Parse OpenAI response JSON into a list of cards.
///
/// This function attempts to handle malformed JSON gracefully by
/// extracting as many valid cards as possible.
///
/// # Arguments
/// * `json` - The JSON string from OpenAI API
///
/// # Returns
/// A list of parsed cards, or an error if parsing completely fails
pub fn parse_openai_response(json: &str) -> Result<Vec<AIGeneratedCard>> {
    // Try to parse as standard response
    match serde_json::from_str::<OpenAIResponse>(json) {
        Ok(response) => {
            let cards: Vec<AIGeneratedCard> = response.cards.into_iter().map(Into::into).collect();
            if cards.is_empty() {
                return Err(AnkiError::InvalidInput {
                    source: InvalidInputError::without_source(
                        "No cards found in response".to_string(),
                    ),
                });
            }
            Ok(cards)
        }
        Err(e) => {
            // Try to extract JSON object if wrapped in other text
            if let Some(start) = json.find('{') {
                if let Some(end) = json.rfind('}') {
                    let extracted = &json[start..=end];
                    if let Ok(response) = serde_json::from_str::<OpenAIResponse>(extracted) {
                        let cards: Vec<AIGeneratedCard> =
                            response.cards.into_iter().map(Into::into).collect();
                        if !cards.is_empty() {
                            return Ok(cards);
                        }
                    }
                }
            }
            Err(AnkiError::JsonError {
                info: format!("Failed to parse OpenAI response: {}", e),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_basic_response() {
        let json = r#"{
            "cards": [
                {
                    "type": "basic",
                    "front": "What is Rust?",
                    "back": "A systems programming language",
                    "suggested_tags": ["programming", "rust"]
                }
            ]
        }"#;

        let cards = parse_openai_response(json).unwrap();
        assert_eq!(cards.len(), 1);
        assert_eq!(cards[0].card_type, CardType::Basic);
        assert_eq!(cards[0].front, "What is Rust?");
        assert_eq!(cards[0].back, "A systems programming language");
        assert_eq!(cards[0].suggested_tags, vec!["programming", "rust"]);
    }

    #[test]
    fn test_parse_cloze_response() {
        let json = r#"{
            "cards": [
                {
                    "type": "cloze",
                    "front": "The {{c1::mitochondria}} is the powerhouse of the cell",
                    "back": "",
                    "suggested_tags": ["biology"]
                }
            ]
        }"#;

        let cards = parse_openai_response(json).unwrap();
        assert_eq!(cards.len(), 1);
        assert_eq!(cards[0].card_type, CardType::Cloze);
        assert!(cards[0].front.contains("{{c1::"));
    }

    #[test]
    fn test_parse_multiple_cards() {
        let json = r#"{
            "cards": [
                {"type": "basic", "front": "Q1", "back": "A1"},
                {"type": "basic_reversed", "front": "Q2", "back": "A2"},
                {"type": "cloze", "front": "{{c1::test}}", "back": ""}
            ]
        }"#;

        let cards = parse_openai_response(json).unwrap();
        assert_eq!(cards.len(), 3);
        assert_eq!(cards[0].card_type, CardType::Basic);
        assert_eq!(cards[1].card_type, CardType::BasicReversed);
        assert_eq!(cards[2].card_type, CardType::Cloze);
    }

    #[test]
    fn test_parse_unknown_type_defaults_to_basic() {
        let json = r#"{
            "cards": [
                {"type": "unknown_type", "front": "Q", "back": "A"}
            ]
        }"#;

        let cards = parse_openai_response(json).unwrap();
        assert_eq!(cards[0].card_type, CardType::Basic);
    }

    #[test]
    fn test_parse_empty_cards_error() {
        let json = r#"{"cards": []}"#;
        assert!(parse_openai_response(json).is_err());
    }

    #[test]
    fn test_parse_invalid_json_error() {
        let json = "not valid json";
        assert!(parse_openai_response(json).is_err());
    }

    #[test]
    fn test_parse_wrapped_json() {
        let json =
            r#"Here is the response: {"cards": [{"type": "basic", "front": "Q", "back": "A"}]}"#;
        let cards = parse_openai_response(json).unwrap();
        assert_eq!(cards.len(), 1);
    }
}
