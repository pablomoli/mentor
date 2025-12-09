from google import genai
from google.genai import types
import json
import re
from datetime import datetime

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    ANALYST_SYSTEM_PROMPT,
    MENTOR_SYSTEM_PROMPT,
    CONCEPT_EXTRACTION_TEMPLATE,
    MENTOR_PROMPT_TEMPLATE,
    CONCEPT_SCORE_THRESHOLD,
    TOP_GAPS_COUNT,
    DEFAULT_LEARNER_PROFILE,
    get_random_prompt_type_hint,
)
from state import Concept


# Configure Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def extract_concepts(note_content: str, file_path: str) -> list[Concept]:
    """
    Send note content to Gemini and extract concepts with scores.
    Returns a list of Concept objects.
    """
    user_prompt = CONCEPT_EXTRACTION_TEMPLATE.format(note_content=note_content)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=ANALYST_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for consistent analysis
            ),
        )
        return parse_concept_response(response.text, file_path)
    except Exception as e:
        print(f"[analyzer] Error calling Gemini: {e}")
        return []


def parse_concept_response(response_text: str, file_path: str) -> list[Concept]:
    """Parse Gemini's JSON response into Concept objects."""

    # Try to extract JSON from response (handle markdown code blocks)
    # First try to find a JSON array
    json_match = re.search(r"\[[\s\S]*\]", response_text)
    if not json_match:
        print(f"[analyzer] Could not find JSON array in response")
        print(f"[analyzer] Response preview: {response_text[:300]}...")
        return []

    json_str = json_match.group()

    # Clean up common issues
    json_str = json_str.strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[analyzer] JSON parse error: {e}")
        print(f"[analyzer] Attempted to parse: {json_str[:500]}...")
        return []

    if not isinstance(data, list):
        print(f"[analyzer] Expected list, got {type(data)}")
        return []

    concepts = []
    for item in data:
        try:
            # Validate and normalize fields
            score = float(item.get("score", 0.5))
            score = max(0.0, min(1.0, score))  # Clamp to 0-1

            effort = item.get("effort_signal", "medium").lower()
            if effort not in ("low", "medium", "high"):
                effort = "medium"

            complexity = item.get("complexity_signal", "medium").lower()
            if complexity not in ("low", "medium", "high"):
                complexity = "medium"

            concept = Concept(
                name=str(item.get("name", "Unknown")).strip(),
                score=score,
                effort_signal=effort,
                complexity_signal=complexity,
                current_coverage=str(item.get("current_coverage", "")),
                what_would_raise_score=str(item.get("what_would_raise_score", "")),
                location=str(item.get("location", file_path)),
                last_seen=datetime.now(),
            )
            concepts.append(concept)
        except (KeyError, ValueError, TypeError) as e:
            print(f"[analyzer] Error parsing concept: {e}")
            print(f"[analyzer] Problematic item: {item}")
            continue

    return concepts


def generate_mentor_prompt(
    concept: Concept, learner_profile: dict | None = None, prompt_type_hint: str | None = None
) -> str:
    """
    Generate a thought-provoking prompt for a gap concept.
    This is the mentor agent - turns analysis into curiosity.
    """
    # Use provided profile or default
    profile = learner_profile or DEFAULT_LEARNER_PROFILE

    # Get random prompt type for variety (or use provided one)
    if prompt_type_hint is None:
        prompt_type_hint = get_random_prompt_type_hint()

    user_prompt = MENTOR_PROMPT_TEMPLATE.format(
        concept_name=concept.name,
        current_coverage=concept.current_coverage,
        what_would_raise_score=concept.what_would_raise_score,
        complexity_signal=concept.complexity_signal,
        effort_signal=concept.effort_signal,
        depth_target=profile.get("depth_target", "build"),
        learning_direction=profile.get("learning_direction", "why_first"),
        challenge_tolerance=profile.get("challenge_tolerance", "medium"),
        guidance_level=profile.get("guidance_level", "foothold"),
        prompt_type_hint=prompt_type_hint,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=MENTOR_SYSTEM_PROMPT,
                temperature=0.7,  # Higher temperature for creative prompts
            ),
        )

        # Clean up response
        result = response.text.strip()

        # Remove quotes if the model wrapped it in quotes
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]

        return result

    except Exception as e:
        print(f"[analyzer] Error generating prompt: {e}")
        return f"What would help you understand {concept.name} more deeply?"


def analyze_note(
    note_content: str, file_path: str, learner_profile: dict | None = None
) -> tuple[list[Concept], list[tuple[Concept, str, str]]]:
    """
    Full analysis pipeline: extract concepts and generate prompts for top gaps.

    Returns:
        (concepts, gap_prompts) where gap_prompts is list of (Concept, prompt_text, prompt_type_hint) tuples
    """
    concepts = extract_concepts(note_content, file_path)

    if not concepts:
        return [], []

    # Sort by priority, get top gaps below threshold
    gaps = sorted(
        [c for c in concepts if c.score < CONCEPT_SCORE_THRESHOLD],
        key=lambda c: c.priority,
        reverse=True,
    )[:TOP_GAPS_COUNT]

    # Generate prompts for top gaps, keeping concept association and prompt type
    gap_prompts = []
    for gap in gaps:
        prompt_type_hint = get_random_prompt_type_hint()
        prompt = generate_mentor_prompt(gap, learner_profile, prompt_type_hint)
        gap_prompts.append((gap, prompt, prompt_type_hint))

    return concepts, gap_prompts


def get_concept_summary(concepts: list[Concept]) -> str:
    """Generate a brief summary of extracted concepts for logging."""
    if not concepts:
        return "No concepts found"

    lines = []
    for c in sorted(concepts, key=lambda x: x.priority, reverse=True):
        entropy = c.entropy_delta
        lines.append(
            f"  • {c.name}: score={c.score:.2f}, "
            f"effort={c.effort_signal}, complexity={c.complexity_signal}, "
            f"entropy_delta={entropy}"
        )

    return "\n".join(lines)
