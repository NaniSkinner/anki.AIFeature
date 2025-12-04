// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Validation of AI-generated flashcards.

use std::sync::LazyLock;

use regex::Regex;

use super::parse::AIGeneratedCard;
use super::parse::CardType;

/// Maximum length for card fields (in characters).
const MAX_FIELD_LENGTH: usize = 100_000;

/// Minimum content length for a valid card.
const MIN_CONTENT_LENGTH: usize = 1;

/// Regex for validating cloze deletion syntax.
static CLOZE_PATTERN: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\{\{c\d+::.*?\}\}").unwrap());

/// Result of card validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationResult {
    /// Whether the card is valid.
    pub is_valid: bool,
    /// List of validation issues (warnings or errors).
    pub issues: Vec<ValidationIssue>,
    /// The sanitized card (if valid).
    pub sanitized_card: Option<AIGeneratedCard>,
}

/// A validation issue found in a card.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationIssue {
    pub severity: IssueSeverity,
    pub message: String,
}

/// Severity of a validation issue.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IssueSeverity {
    /// Informational - card is still valid.
    Info,
    /// Warning - card is valid but may have issues.
    Warning,
    /// Error - card is invalid.
    Error,
}

impl ValidationResult {
    fn valid(card: AIGeneratedCard) -> Self {
        Self {
            is_valid: true,
            issues: vec![],
            sanitized_card: Some(card),
        }
    }

    fn valid_with_warnings(card: AIGeneratedCard, issues: Vec<ValidationIssue>) -> Self {
        Self {
            is_valid: true,
            issues,
            sanitized_card: Some(card),
        }
    }

    fn invalid(issues: Vec<ValidationIssue>) -> Self {
        Self {
            is_valid: false,
            issues,
            sanitized_card: None,
        }
    }
}

/// Validate an AI-generated card.
///
/// This function checks:
/// - Field lengths are within limits
/// - Required fields are non-empty
/// - Cloze cards have valid cloze syntax
/// - HTML is sanitized
///
/// # Arguments
/// * `card` - The card to validate
///
/// # Returns
/// A ValidationResult containing the validation status and any issues
pub fn validate_card(card: &AIGeneratedCard) -> ValidationResult {
    let mut issues = Vec::new();

    // Check for empty front
    let front_trimmed = card.front.trim();
    if front_trimmed.len() < MIN_CONTENT_LENGTH {
        issues.push(ValidationIssue {
            severity: IssueSeverity::Error,
            message: "Front field is empty".to_string(),
        });
        return ValidationResult::invalid(issues);
    }

    // Check for empty back on non-cloze cards
    if card.card_type != CardType::Cloze {
        let back_trimmed = card.back.trim();
        if back_trimmed.len() < MIN_CONTENT_LENGTH {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Error,
                message: "Back field is empty for non-cloze card".to_string(),
            });
            return ValidationResult::invalid(issues);
        }
    }

    // Check field length limits
    if card.front.len() > MAX_FIELD_LENGTH {
        issues.push(ValidationIssue {
            severity: IssueSeverity::Error,
            message: format!(
                "Front field exceeds maximum length ({} > {})",
                card.front.len(),
                MAX_FIELD_LENGTH
            ),
        });
        return ValidationResult::invalid(issues);
    }

    if card.back.len() > MAX_FIELD_LENGTH {
        issues.push(ValidationIssue {
            severity: IssueSeverity::Error,
            message: format!(
                "Back field exceeds maximum length ({} > {})",
                card.back.len(),
                MAX_FIELD_LENGTH
            ),
        });
        return ValidationResult::invalid(issues);
    }

    // Validate cloze syntax for cloze cards
    if card.card_type == CardType::Cloze && !CLOZE_PATTERN.is_match(&card.front) {
        issues.push(ValidationIssue {
            severity: IssueSeverity::Error,
            message: "Cloze card is missing valid cloze deletion ({{c1::...}})".to_string(),
        });
        return ValidationResult::invalid(issues);
    }

    // Sanitize HTML content
    let sanitized_front = sanitize_card_html(&card.front);
    let sanitized_back = sanitize_card_html(&card.back);

    // Check if sanitization changed the content significantly
    if sanitized_front != card.front || sanitized_back != card.back {
        issues.push(ValidationIssue {
            severity: IssueSeverity::Info,
            message: "HTML was sanitized for security".to_string(),
        });
    }

    // Sanitize tags
    let sanitized_tags: Vec<String> = card
        .suggested_tags
        .iter()
        .map(|t| sanitize_tag(t))
        .filter(|t| !t.is_empty())
        .collect();

    let sanitized_card = AIGeneratedCard {
        card_type: card.card_type,
        front: sanitized_front,
        back: sanitized_back,
        suggested_tags: sanitized_tags,
    };

    if issues.is_empty() {
        ValidationResult::valid(sanitized_card)
    } else {
        ValidationResult::valid_with_warnings(sanitized_card, issues)
    }
}

/// Sanitize HTML content for card fields.
fn sanitize_card_html(html: &str) -> String {
    // Use ammonia for HTML sanitization with default safe settings
    ammonia::clean(html)
}

/// Sanitize a tag string.
fn sanitize_tag(tag: &str) -> String {
    // Remove leading/trailing whitespace
    let trimmed = tag.trim();
    // Replace spaces with underscores
    let no_spaces = trimmed.replace(' ', "_");
    // Remove any characters that might cause issues
    no_spaces
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '_' || *c == '-' || *c == ':')
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_basic_card() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "What is Rust?".to_string(),
            back: "A programming language".to_string(),
            suggested_tags: vec!["programming".to_string()],
        };

        let result = validate_card(&card);
        assert!(result.is_valid);
        assert!(result.issues.is_empty());
    }

    #[test]
    fn test_empty_front_invalid() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "".to_string(),
            back: "Answer".to_string(),
            suggested_tags: vec![],
        };

        let result = validate_card(&card);
        assert!(!result.is_valid);
        assert!(result
            .issues
            .iter()
            .any(|i| i.message.contains("Front field is empty")));
    }

    #[test]
    fn test_empty_back_invalid_for_basic() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "Question".to_string(),
            back: "".to_string(),
            suggested_tags: vec![],
        };

        let result = validate_card(&card);
        assert!(!result.is_valid);
    }

    #[test]
    fn test_empty_back_valid_for_cloze() {
        let card = AIGeneratedCard {
            card_type: CardType::Cloze,
            front: "The {{c1::sun}} rises in the east".to_string(),
            back: "".to_string(),
            suggested_tags: vec![],
        };

        let result = validate_card(&card);
        assert!(result.is_valid);
    }

    #[test]
    fn test_cloze_without_deletion_invalid() {
        let card = AIGeneratedCard {
            card_type: CardType::Cloze,
            front: "No cloze deletion here".to_string(),
            back: "".to_string(),
            suggested_tags: vec![],
        };

        let result = validate_card(&card);
        assert!(!result.is_valid);
        assert!(result
            .issues
            .iter()
            .any(|i| i.message.contains("missing valid cloze deletion")));
    }

    #[test]
    fn test_html_sanitization() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "<script>alert('xss')</script>What is Rust?".to_string(),
            back: "A <b>safe</b> language".to_string(),
            suggested_tags: vec![],
        };

        let result = validate_card(&card);
        assert!(result.is_valid);
        let sanitized = result.sanitized_card.unwrap();
        assert!(!sanitized.front.contains("<script>"));
        assert!(sanitized.back.contains("<b>"));
    }

    #[test]
    fn test_tag_sanitization() {
        let card = AIGeneratedCard {
            card_type: CardType::Basic,
            front: "Q".to_string(),
            back: "A".to_string(),
            suggested_tags: vec![
                "  spaces  ".to_string(),
                "special!@#chars".to_string(),
                "valid_tag".to_string(),
            ],
        };

        let result = validate_card(&card);
        assert!(result.is_valid);
        let sanitized = result.sanitized_card.unwrap();
        assert_eq!(sanitized.suggested_tags[0], "spaces");
        assert_eq!(sanitized.suggested_tags[1], "specialchars");
        assert_eq!(sanitized.suggested_tags[2], "valid_tag");
    }
}
