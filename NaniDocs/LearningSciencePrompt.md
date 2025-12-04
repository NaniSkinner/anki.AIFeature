# Report: Designing a Science-Based LLM Prompt for Anki Flashcard Generation

**Date**: December 4, 2025\
**Author**: Manus AI\
**Objective**: To create an LLM prompt that generates high-quality, atomic, and recall-focused Anki flashcards based on established principles from cognitive science and learning theory.

---

## 1. Executive Summary

The current LLM prompt for generating Anki flashcards produces cards that are often too lengthy and lack focus, leading to user rejection. To address this, we conducted comprehensive research into Anki's primary user base, the cognitive science of learning, and best practices in both flashcard formulation and LLM prompt engineering.

Our research confirms that Anki's core users are **medical students and language learners** who require efficient memorization of vast, complex information. The most effective learning principles for this audience are **retrieval practice**, **desirable difficulties**, and minimizing **cognitive load**. The gold standard for card creation, Piotr Wozniak's "20 Rules of Formulating Knowledge," overwhelmingly emphasizes the **minimum information principle**—creating atomic, concise, and specific cards.

Based on these findings, we have designed a new, highly-structured prompt that explicitly instructs the LLM to act as a cognitive science expert and adhere to these principles. We also recommend upgrading the language model from **GPT-4o-mini to GPT-4o** to ensure the highest quality output, as research indicates that more powerful models are significantly better at adhering to complex, nuanced instructions required for effective educational content.

---

## 2. Research Synthesis

### 2.1. Anki User Demographics

Our research indicates that Anki's most dedicated users are those engaged in fields requiring extensive memorization.

- **Primary Users**: Medical students are the most prominent and well-documented user group. Studies show that a high percentage of medical students (as high as 80% in some cohorts) use Anki for subjects like anatomy, physiology, and pharmacology [1, 2].
- **Secondary Users**: Language learners, law students, and other professionals studying for certifications also form a significant portion of the user base.
- **Learning Goal**: These users prioritize long-term retention and efficient, high-volume learning. Their goal is not casual study but deep, lasting mastery of complex subjects.

**Conclusion**: The flashcard generation process must be optimized for serious, high-volume learners who value accuracy and efficiency.

### 2.2. Core Cognitive Science Principles

Three core principles from cognitive science are essential for effective flashcard design.

| Principle                  | Description                                                                                                                                                                                                             | Implication for Flashcards                                                                                                                                                                                                            |
| :------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Retrieval Practice**     | The act of actively recalling information strengthens long-term memory. This is more effective than passively re-reading material.                                                                                      | Cards must be designed to **force recall**, not just recognition. Open-ended questions (What, Why, How) are superior to simple fill-in-the-blanks or multiple-choice formats.                                                         |
| **Desirable Difficulties** | Learning tasks should require a considerable but desirable amount of effort. If a task is too easy, no learning occurs; if it's too hard, the learner gives up.                                                         | Cards should be **challenging but answerable**. They should make the user think, but not be so obscure or complex that they lead to frustration.                                                                                      |
| **Cognitive Load Theory**  | The brain has a limited working memory. Learning is impaired if this limit is exceeded. Extraneous cognitive load (from poor instruction) should be minimized to maximize germane load (the effort of actual learning). | Cards must be **simple, clear, and concise**. All irrelevant information, confusing wording, and unnecessary complexity should be eliminated to reduce extraneous load. This directly supports the **minimum information principle**. |

### 2.3. Flashcard Formulation: Wozniak's 20 Rules

Dr. Piotr Wozniak, the creator of the SuperMemo spaced repetition algorithm, formulated 20 rules for creating effective flashcards. The most critical of these is the **minimum information principle** [3].

> **Minimum Information Principle**: "The material you learn must be formulated in as simple way as it is [possible]."

This principle dictates that complex information should be broken down into the smallest possible, independently understandable pieces. This is the most violated rule by beginners and the primary cause of ineffective, lengthy cards.

**Key Takeaways from Wozniak's Rules:**

- **Atomicity**: One card, one concept.
- **Conciseness**: Use the shortest possible questions and even shorter answers.
- **Specificity**: Avoid vague questions. Test a single, precise fact.
- **Avoid Sets & Enumerations**: Do not ask for lists of items. Instead, create individual cards for each item or use cloze deletion.

### 2.4. LLM Model & Prompt Engineering

- **Model Choice**: Research shows that GPT-4 significantly outperforms GPT-3.5 in creating concise, high-quality flashcards that adhere to complex instructions [4]. Given that GPT-4o-mini's capabilities are closer to GPT-3.5/4-Turbo, and the primary user complaint is quality, **upgrading to GPT-4o is strongly recommended**. The higher cost is justified by the significant increase in quality and the reduction in user editing time and rejected cards.
- **Prompting Techniques**: Effective prompts are specific, provide context, give clear instructions on format, and ideally include examples (few-shot prompting) [5]. The prompt should not just ask _what_ to do, but also _how_ and _why_, grounding the task in the principles of learning science.

---

## 3. The New Science-Based Prompt

Below is the proposed new prompt, designed to incorporate all research findings. It establishes a persona, provides clear rules grounded in cognitive science, defines a strict output format, and includes examples to guide the model.

````
### ROLE ###
You are an expert in cognitive science and learning theory, specializing in creating optimal study materials for spaced repetition systems like Anki. Your goal is to generate high-quality, effective flashcards from a given source text.

### TASK ###
Based on the source text provided, create ONE new, high-quality flashcard to replace the rejected one. The new card must be superior and adhere strictly to the following rules of effective flashcard formulation.

### RULES OF FORMULATION ###
1.  **Minimum Information Principle**: The card must be ATOMIC, testing only ONE discrete piece of information. If a concept is complex, break it down into its simplest possible component. Your primary goal is to minimize cognitive load.
2.  **Force Active Recall**: The question must require active retrieval of the answer. It should be a true question (What, Why, How), not a simple statement to be completed. Avoid recognition-based questions.
3.  **Conciseness & Clarity**: The question and answer must be as short and clear as possible. Eliminate every unnecessary word. Avoid repeating the phrasing of the question in the answer.
4.  **Focus on Key Concepts**: The card must test the MOST important and central concepts from the text, not peripheral details. Avoid trivia.
5.  **Independence**: The card must be understandable on its own without needing the original source text. Do not refer to "the article" or "the author."

### REJECTION CONTEXT ###
- **Source Text Excerpt**: "{source_text[:2000]}"
- **Rejected Card Type**: {original_card.card_type.value}
- **Rejected Card Front**: "{original_card.front}"
- **Rejected Card Back**: "{original_card.back}"
- **User Feedback**: {hint}  # This context explains why the previous card failed. Pay close attention to it.

### EXAMPLES OF GOOD VS. BAD CARDS ###

**Example 1: From a text about the Dead Sea.**
- ❌ **BAD (Too Complex)**:
  - Front: "What are the characteristics of the Dead Sea?"
  - Back: "It's a salt lake on the border of Israel and Jordan, its shoreline is the lowest point on Earth, it's 74km long, and it's 7 times saltier than the ocean."
- ✅ **GOOD (Atomic & Concise)**:
  - Front: "What is the main reason swimmers can float easily in the Dead Sea?"
  - Back: "Its high salt content increases water density."

**Example 2: From a text about photosynthesis.**
- ❌ **BAD (Wrong Focus/Too Broad)**:
  - Front: "What did the author say about photosynthesis?"
  - Back: "The author explained that it's a process used by plants to convert light into energy."
- ✅ **GOOD (Specific & Forces Recall)**:
  - Front: "What are the two primary outputs of photosynthesis?"
  - Back: "Glucose and oxygen."

### OUTPUT FORMAT ###
Respond with a single, valid JSON object containing exactly one card. Do not include any explanatory text outside of the JSON structure.

```json
{
  "cards": [
    {
      "card_type": "basic",
      "front": "<The new, improved question based on the rules>",
      "back": "<The new, concise, and direct answer>"
    }
  ]
}
````

### FINAL INSTRUCTION

Now, based on all the rules and context, generate a new, superior card.

```
---

## 4. Rationale for Prompt Design

- **Persona (`ROLE`)**: Instructing the LLM to act as an expert primes it to access more sophisticated knowledge and produce higher-quality output.
- **Clear Rules (`RULES OF FORMULATION`)**: Translates abstract cognitive science principles into concrete, actionable instructions for the LLM. Explicitly naming the "Minimum Information Principle" is key.
- **Rejection Context**: Provides the model with a clear signal of what *not* to do, enabling it to learn from the user's feedback.
- **Few-Shot Examples (`EXAMPLES`)**: Demonstrating good vs. bad cards is a powerful way to guide the model's output, making the abstract rules concrete.
- **Strict JSON Output (`OUTPUT FORMAT`)**: Ensures the output is machine-readable and can be directly integrated into the application without parsing errors.
- **Model Recommendation**: The complexity and nuance of these rules require a highly capable model. GPT-4o has the reasoning capacity to follow these multi-step, principle-based instructions more reliably than GPT-4o-mini.

By implementing this new prompt and upgrading the model, we anticipate a significant reduction in lengthy and unfocused cards, leading to a better user experience and more effective learning outcomes.
```
