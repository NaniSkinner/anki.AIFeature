// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! AI-powered flashcard generation parsing and validation.

mod convert;
mod parse;
mod service;
mod validate;

pub use convert::to_foreign_note;
pub use parse::parse_openai_response;
pub use parse::AIGeneratedCard;
pub use parse::CardType;
pub use validate::validate_card;
pub use validate::ValidationResult;
