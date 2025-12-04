# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""OpenAI client for AI flashcard generation."""

from __future__ import annotations

import json
import re
from typing import Any

from anki.ai_flashcards.document_parser import chunk_text, estimate_tokens
from anki.ai_flashcards.models import (
    CardType,
    CostEstimate,
    GeneratedCard,
    GenerationConfig,
)

# OpenAI model configuration
DEFAULT_MODEL = "gpt-4o-mini"
# Pricing per 1M tokens (as of late 2024)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}

SYSTEM_PROMPT = """You are an expert educator creating Anki flashcards.
Generate flashcards from the provided text following these rules:

1. Create clear, atomic cards (one concept per card)
2. For definitions and simple facts, use "basic" format
3. For vocabulary, terminology, or concepts that benefit from bidirectional learning, use "basic_reversed" format
4. For processes, sequences, lists, or fill-in-the-blank content, use "cloze" format
5. Ensure answers are concise but complete
6. Include context when the question would be ambiguous without it
7. For cloze cards, use {{c1::text}} syntax for deletions. Use multiple cloze numbers (c1, c2, etc.) only when testing different concepts in the same sentence.

Respond ONLY with valid JSON in this exact format:
{
  "cards": [
    {
      "type": "basic",
      "front": "What is X?",
      "back": "X is Y",
      "suggested_tags": ["topic1", "topic2"]
    },
    {
      "type": "cloze",
      "front": "The {{c1::mitochondria}} is the powerhouse of the cell",
      "back": "",
      "suggested_tags": ["biology", "cell"]
    }
  ]
}

Important:
- "type" must be one of: "basic", "basic_reversed", "cloze"
- For cloze cards, "back" should be empty string
- suggested_tags should be lowercase, no spaces (use underscores)
- Create high-quality cards that test understanding, not just memorization
"""


class OpenAIError(Exception):
    """Raised when OpenAI API calls fail."""

    pass


class OpenAIFlashcardClient:
    """Client for generating flashcards using OpenAI API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        """Initialize the client.

        Args:
            api_key: OpenAI API key
            model: Model to use for generation
        """
        if not api_key:
            raise OpenAIError("API key is required")

        self.api_key = api_key
        self.model = model

    def test_connection(self) -> tuple[bool, str | None]:
        """Test the API connection and key validity.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            # Make a minimal API call to verify the key
            client.models.list()
            return True, None
        except ImportError:
            return False, "OpenAI library not installed. Run: pip install openai"
        except openai.AuthenticationError:
            return False, "Invalid API key"
        except openai.RateLimitError:
            return False, "Rate limit exceeded. Please try again later."
        except openai.APIConnectionError:
            return False, "Could not connect to OpenAI API"
        except Exception as e:
            return False, str(e)

    def estimate_cost(self, text: str) -> CostEstimate:
        """Estimate the cost of processing the given text.

        Args:
            text: The text to process

        Returns:
            Cost estimate with tokens and USD
        """
        input_tokens = estimate_tokens(text)
        # Estimate output tokens (roughly 50% of input for flashcards)
        output_tokens = input_tokens // 2

        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING[DEFAULT_MODEL])
        cost = (
            input_tokens * pricing["input"] + output_tokens * pricing["output"]
        ) / 1_000_000

        return CostEstimate(
            estimated_tokens=input_tokens + output_tokens,
            estimated_cost_usd=round(cost, 4),
            model=self.model,
        )

    def generate_flashcards(
        self,
        text: str,
        config: GenerationConfig,
    ) -> list[GeneratedCard]:
        """Generate flashcards from the given text.

        Args:
            text: The source text to generate cards from
            config: Generation configuration

        Returns:
            List of generated flashcard objects

        Raises:
            OpenAIError: If generation fails
        """
        try:
            import openai
        except ImportError as e:
            raise OpenAIError(
                "OpenAI library not installed. Run: pip install openai"
            ) from e

        # Build the user prompt
        user_prompt = self._build_user_prompt(text, config)

        # Chunk text if needed
        chunks = chunk_text(text)
        all_cards: list[GeneratedCard] = []

        client = openai.OpenAI(api_key=self.api_key)

        for i, chunk in enumerate(chunks):
            chunk_limit = config.card_limit - len(all_cards)
            if chunk_limit <= 0:
                break

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": self._build_user_prompt(
                                chunk,
                                GenerationConfig(
                                    card_limit=chunk_limit,
                                    preferred_card_type=config.preferred_card_type,
                                    source_name=config.source_name,
                                    auto_tags=config.auto_tags,
                                ),
                            ),
                        },
                    ],
                    temperature=0.7,
                    max_tokens=4000,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                if content:
                    cards = self._parse_response(content, config)
                    all_cards.extend(cards)

            except openai.APIError as e:
                raise OpenAIError(f"API error: {e}") from e

        return all_cards[: config.card_limit]

    def regenerate_card(
        self,
        original_card: GeneratedCard,
        source_text: str,
        hint: str | None = None,
    ) -> GeneratedCard:
        """Regenerate a single card with optional hint.

        Args:
            original_card: The card to regenerate
            source_text: Original source text for context
            hint: Optional user hint for regeneration

        Returns:
            New generated card

        Raises:
            OpenAIError: If regeneration fails
        """
        try:
            import openai
        except ImportError as e:
            raise OpenAIError("OpenAI library not installed") from e

        prompt = f"""Based on this source text, create ONE new flashcard to replace the rejected one.

Source text excerpt:
{source_text[:2000]}

The previous card was rejected:
- Type: {original_card.card_type.value}
- Front: {original_card.front}
- Back: {original_card.back}

{"User feedback: " + hint if hint else ""}

Create a better card covering similar content. Respond with JSON containing exactly one card."""

        client = openai.OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                cards = self._parse_response(
                    content,
                    GenerationConfig(card_limit=1, auto_tags=["ai-generated"]),
                )
                if cards:
                    return cards[0]

            raise OpenAIError("No card generated")

        except openai.APIError as e:
            raise OpenAIError(f"API error: {e}") from e

    def _build_user_prompt(self, text: str, config: GenerationConfig) -> str:
        """Build the user prompt for card generation."""
        parts = [
            f"Generate up to {config.card_limit} flashcards from the following text.",
        ]

        if config.preferred_card_type:
            parts.append(
                f"Prefer {config.preferred_card_type.value} format when appropriate."
            )

        if config.source_name:
            parts.append(f"Source: {config.source_name}")

        parts.append("\n---\n")
        parts.append(text)

        return "\n".join(parts)

    def _parse_response(
        self,
        response_text: str,
        config: GenerationConfig,
    ) -> list[GeneratedCard]:
        """Parse the OpenAI response into GeneratedCard objects."""
        try:
            # Try to parse as JSON
            data = json.loads(response_text)

            if "cards" not in data:
                raise OpenAIError("Response missing 'cards' field")

            cards = []
            for card_data in data["cards"]:
                try:
                    card_type = CardType(card_data["type"])
                except ValueError:
                    # Default to basic if type is invalid
                    card_type = CardType.BASIC

                # Combine auto_tags with suggested_tags
                tags = list(config.auto_tags)
                source_tag = config.get_source_tag()
                if source_tag:
                    tags.append(source_tag)
                tags.extend(card_data.get("suggested_tags", []))

                card = GeneratedCard(
                    card_type=card_type,
                    front=card_data.get("front", ""),
                    back=card_data.get("back", ""),
                    suggested_tags=tags,
                )
                cards.append(card)

            return cards

        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return self._parse_response(json_match.group(), config)
            raise OpenAIError("Failed to parse response as JSON")


def test_api_key(api_key: str) -> tuple[bool, str | None]:
    """Test if an API key is valid.

    Args:
        api_key: The API key to test

    Returns:
        Tuple of (is_valid, error_message)
    """
    client = OpenAIFlashcardClient(api_key)
    return client.test_connection()
