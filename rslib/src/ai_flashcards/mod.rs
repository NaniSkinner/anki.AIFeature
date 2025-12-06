// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! AI-powered flashcard generation.
//!
//! This module handles session persistence and card import.
//! The actual AI operations (generation, cost estimation) are
//! implemented in Python (pylib/anki/ai_flashcards/).

mod service;
