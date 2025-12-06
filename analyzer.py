from google import genai
import json
import re
from datetime import datetime

from config import GEMINI_API_KEY, GEMINI_MODEL
from state import Concept


# Configure Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def extract_concepts(note_content: str, file_path: str) -> list[Concept]:
    """
    Send note content to Gemini and extract concepts with scores.
    Returns a list of Concept objects.
    """
    prompt = f"""Analyze these notes and extract the key concepts being discussed.

For each concept, assess:
1. How well is it explained? (score 0.0 to 1.0)
   - 0.0 = just named, no explanation
   - 0.4 = partially explained, vague
   - 0.6 = explained but shallow
   - 0.8 = explained with reasoning/why
   - 1.0 = deep understanding shown

2. Effort signal: How much work did the writer put into explaining this?
   - "low" = just named it, jargon, one-liner
   - "medium" = some explanation but vague
   - "high" = detailed, specific, shows reasoning

3. Complexity signal: How inherently complex is this concept?
   - "low" = simple definition, single idea
   - "medium" = has moving parts or dependencies  
   - "high" = abstract, multi-step mechanism, or counterintuitive

NOTES:
---
{note_content}
---

Return ONLY valid JSON array. No markdown, no explanation. Format:
[
  {{
    "name": "concept name",
    "score": 0.0-1.0,
    "effort_signal": "low|medium|high",
    "complexity_signal": "low|medium|high", 
    "current_coverage": "brief summary of what notes say about this",
    "what_would_raise_score": "what's missing that would deepen understanding",
    "location": "which section/paragraph discusses this"
  }}
]
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return parse_concept_response(response.text, file_path)
    except Exception as e:
        print(f"[analyzer] Error calling Gemini: {e}")
        return []


def parse_concept_response(response_text: str, file_path: str) -> list[Concept]:
    """Parse Gemini's JSON response into Concept objects."""

    # Try to extract JSON from response (handle markdown code blocks)
    json_match = re.search(r"\[[\s\S]*\]", response_text)
    if not json_match:
        print(f"[analyzer] Could not find JSON in response: {response_text[:200]}")
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"[analyzer] JSON parse error: {e}")
        print(f"[analyzer] Response was: {response_text[:500]}")
        return []

    concepts = []
    for item in data:
        try:
            concept = Concept(
                name=item.get("name", "Unknown"),
                score=float(item.get("score", 0.5)),
                effort_signal=item.get("effort_signal", "medium"),
                complexity_signal=item.get("complexity_signal", "medium"),
                current_coverage=item.get("current_coverage", ""),
                what_would_raise_score=item.get("what_would_raise_score", ""),
                location=item.get("location", file_path),
                last_seen=datetime.now(),
            )
            concepts.append(concept)
        except (KeyError, ValueError) as e:
            print(f"[analyzer] Error parsing concept: {e}, item: {item}")
            continue

    return concepts


def generate_mentor_prompt(
    concept: Concept, learner_profile: dict | None = None
) -> str:
    """
    Generate a thought-provoking prompt for a gap concept.
    This is the mentor agent - turns analysis into curiosity.
    """
    # Default profile if none provided
    profile = learner_profile or {
        "depth_target": "build",
        "learning_direction": "why_first",
        "challenge_tolerance": "medium",
        "guidance_level": "foothold",
    }

    prompt = f"""You are a curious mentor helping someone build deep intuition.

CONCEPT GAP:
- Concept: {concept.name}
- Current coverage: {concept.current_coverage}
- What's missing: {concept.what_would_raise_score}
- Complexity: {concept.complexity_signal}
- User's effort so far: {concept.effort_signal}

LEARNER PROFILE:
- Depth target: {profile.get("depth_target")} (how deep they want to go)
- Learning direction: {profile.get("learning_direction")} (how they prefer to learn)
- Challenge tolerance: {profile.get("challenge_tolerance")} (how hard to push)
- Guidance level: {profile.get("guidance_level")} (how much to lead them)

YOUR TASK:
Generate ONE thought-provoking prompt that:
1. Sparks curiosity, doesn't quiz
2. Leads toward the missing understanding
3. Matches their guidance level:
   - "minimal": Just point, they'll figure it out
   - "foothold": Give a conceptual anchor, then ask
   - "guided": Walk them toward the insight step by step

If this is a complex concept they haven't encountered, give a foothold first.

BAD: "What is VMAT?" (just asks for definition)
BAD: "Look up GABAergic interneurons" (sends them away)
GOOD: "You said amphetamines disrupt VMAT. But VMAT loads dopamine into vesicles for storage. If that's disrupted... where does the dopamine go instead?"

Return ONLY the prompt text. No explanation, no quotes, no preamble.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[analyzer] Error generating prompt: {e}")
        return f"What would help you understand {concept.name} more deeply?"


def analyze_note(note_content: str, file_path: str) -> tuple[list[Concept], list[str]]:
    """
    Full analysis pipeline: extract concepts and generate prompts for top gaps.
    Returns (concepts, prompts).
    """
    concepts = extract_concepts(note_content, file_path)

    if not concepts:
        return [], []

    # Sort by priority, get top gaps
    gaps = sorted(
        [c for c in concepts if c.score < 0.6], key=lambda c: c.priority, reverse=True
    )[:5]

    # Generate prompts for top gaps
    prompts = []
    for gap in gaps:
        prompt = generate_mentor_prompt(gap)
        prompts.append(prompt)

    return concepts, prompts
