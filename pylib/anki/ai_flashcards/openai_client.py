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
DEFAULT_MODEL = "gpt-4o"
# Pricing per 1M tokens (as of late 2024)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}

SYSTEM_PROMPT = """### ROLE ###
You are an expert in cognitive science and learning theory, specializing in creating optimal study materials for spaced repetition systems like Anki. Your goal is to generate high-quality, effective flashcards that maximize long-term retention.

### RULES OF FORMULATION ###
Apply these cognitive science principles to every card:

1. **Minimum Information Principle**: Each card must be ATOMIC, testing only ONE discrete piece of information. Break complex concepts into their simplest possible components. This minimizes cognitive load and maximizes retention.

2. **Force Active Recall**: Questions must require active retrieval, not recognition. Use open-ended questions (What, Why, How) rather than simple fill-in-the-blank. The learner should have to think, not just recognize.

3. **Conciseness & Clarity**: Use the shortest possible questions and even shorter answers. Eliminate every unnecessary word. Never repeat the question's phrasing in the answer.

4. **Focus on Key Concepts**: Test the MOST important and central concepts, not peripheral details or trivia.

5. **Independence**: Each card must be understandable on its own without the source text. Never refer to "the article" or "the author."

6. **Desirable Difficulty**: Cards should be challenging but answerable—hard enough to require effort, but not so obscure they cause frustration.

### CARD TYPE GUIDELINES ###
- **"basic"**: For definitions, simple facts, and conceptual questions. Use open-ended questions.
- **"basic_reversed"**: For vocabulary, terminology, or concepts that benefit from bidirectional learning (knowing both term→definition and definition→term).
- **"cloze"**: For processes, sequences, formulas, or when testing specific terms in context. Use {{c1::text}} syntax. Use multiple cloze numbers (c1, c2, etc.) only when testing different concepts in the same sentence.

### EXAMPLES OF GOOD VS. BAD CARDS ###

**Example 1: From a text about the Dead Sea**
- ❌ BAD (Too Complex):
  - Front: "What are the characteristics of the Dead Sea?"
  - Back: "It's a salt lake on the border of Israel and Jordan, its shoreline is the lowest point on Earth, it's 74km long, and it's 7 times saltier than the ocean."
- ✅ GOOD (Atomic & Concise):
  - Front: "Why can swimmers float easily in the Dead Sea?"
  - Back: "High salt content increases water density."

**Example 2: From a text about photosynthesis**
- ❌ BAD (Too Broad):
  - Front: "What is photosynthesis and how does it work?"
  - Back: "Photosynthesis is a process used by plants to convert light energy into chemical energy stored in glucose."
- ✅ GOOD (Specific & Forces Recall):
  - Front: "What are the two primary outputs of photosynthesis?"
  - Back: "Glucose and oxygen."

**Example 3: Cloze card**
- ❌ BAD (Testing trivia):
  - Front: "The mitochondria was discovered in {{c1::1857}}."
- ✅ GOOD (Testing key concept):
  - Front: "The {{c1::mitochondria}} is the organelle responsible for producing ATP through cellular respiration."

### OUTPUT FORMAT ###
Respond ONLY with valid JSON in this exact format:
{
  "cards": [
    {
      "type": "basic",
      "front": "What is X?",
      "back": "Y",
      "suggested_tags": ["topic1", "topic2"]
    },
    {
      "type": "cloze",
      "front": "The {{c1::mitochondria}} produces ATP.",
      "back": "",
      "suggested_tags": ["biology", "cell"]
    }
  ]
}

Important:
- "type" must be one of: "basic", "basic_reversed", "cloze"
- For cloze cards, "back" should be empty string
- suggested_tags should be lowercase, no spaces (use underscores)
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

        user_feedback = f"- **User Feedback**: {hint}" if hint else ""

        prompt = f"""### TASK ###
Create ONE new, high-quality flashcard to replace a rejected card. The new card must be superior and adhere strictly to the Rules of Formulation, especially the Minimum Information Principle.

### REJECTION CONTEXT ###
- **Rejected Card Type**: {original_card.card_type.value}
- **Rejected Card Front**: "{original_card.front}"
- **Rejected Card Back**: "{original_card.back}"
{user_feedback}

### SOURCE TEXT EXCERPT ###
{source_text[:2000]}

### EXAMPLES OF IMPROVEMENT ###

**Example: Fixing a card that's too complex**
- ❌ REJECTED: "What are the characteristics of the Dead Sea?" → "It's a salt lake, lowest point on Earth, 74km long, 7x saltier than ocean."
- ✅ IMPROVED: "Why can swimmers float easily in the Dead Sea?" → "High salt content increases water density."

### OUTPUT FORMAT ###
Respond with valid JSON containing exactly one card:
{{"cards": [{{"type": "basic", "front": "...", "back": "...", "suggested_tags": [...]}}]}}"""

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
        parts = ["### TASK ###"]
        parts.append(
            f"Generate up to {config.card_limit} high-quality flashcards from the "
            "source text below. Apply the Rules of Formulation strictly—prioritize "
            "the Minimum Information Principle above all else."
        )

        if config.preferred_card_type:
            parts.append(
                f"\nPrefer '{config.preferred_card_type.value}' card type when "
                "appropriate for the content."
            )

        if config.source_name:
            parts.append(f"\nSource context: {config.source_name}")

        parts.append("\n\n### SOURCE TEXT ###")
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
