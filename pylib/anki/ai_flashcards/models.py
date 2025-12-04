# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Data models for AI flashcard generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CardType(Enum):
    """Type of flashcard to generate."""

    BASIC = "basic"
    BASIC_REVERSED = "basic_reversed"
    CLOZE = "cloze"


class CardStatus(Enum):
    """Status of a generated card in the review workflow."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REGENERATING = "regenerating"


@dataclass
class GeneratedCard:
    """A single AI-generated flashcard."""

    card_type: CardType
    front: str
    back: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    suggested_tags: list[str] = field(default_factory=list)
    status: CardStatus = CardStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.card_type.value,
            "front": self.front,
            "back": self.back,
            "tags": self.suggested_tags,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratedCard:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            card_type=CardType(data["type"]),
            front=data["front"],
            back=data.get("back", ""),
            suggested_tags=data.get("tags", []),
            status=CardStatus(data.get("status", "pending")),
        )


@dataclass
class GenerationConfig:
    """Configuration for flashcard generation."""

    card_limit: int = 20
    preferred_card_type: CardType | None = None  # None = auto/let AI decide
    source_name: str = ""
    auto_tags: list[str] = field(default_factory=lambda: ["ai-generated"])

    def get_source_tag(self) -> str:
        """Generate a source tag from the source name."""
        if not self.source_name:
            return ""
        # Sanitize the source name for use as a tag
        safe_name = (
            self.source_name.replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )
        return f"source::{safe_name}"


@dataclass
class GenerationSession:
    """A session containing generated cards and metadata."""

    cards: list[GeneratedCard]
    source_name: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "source_name": self.source_name,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationSession:
        """Create from dictionary (JSON deserialization)."""
        return cls(
            version=data.get("version", 1),
            session_id=data.get("session_id", str(uuid.uuid4())),
            created_at=datetime.fromisoformat(data["created_at"]),
            source_name=data["source_name"],
            cards=[GeneratedCard.from_dict(c) for c in data.get("cards", [])],
        )

    def get_approved_cards(self) -> list[GeneratedCard]:
        """Get all cards marked as approved."""
        return [c for c in self.cards if c.status == CardStatus.APPROVED]

    def get_pending_cards(self) -> list[GeneratedCard]:
        """Get all cards still pending review."""
        return [c for c in self.cards if c.status == CardStatus.PENDING]

    def is_expired(self, max_age_days: int = 7) -> bool:
        """Check if the session has expired."""
        age = datetime.now() - self.created_at
        return age.days >= max_age_days


@dataclass
class CostEstimate:
    """Estimated cost for processing a document."""

    estimated_tokens: int
    estimated_cost_usd: float
    model: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "model": self.model,
        }


@dataclass
class GenerationResult:
    """Result of flashcard generation including cards and cost data."""

    cards: list[GeneratedCard]
    tokens_used: int
    cost_usd: float
    model: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cards": [card.to_dict() for card in self.cards],
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "model": self.model,
        }
