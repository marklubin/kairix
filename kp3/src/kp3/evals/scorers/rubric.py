"""Rubric definitions for human scoring.

Provides structured guidance for consistent human evaluation.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class RubricLevel:
    """A single level in a scoring rubric."""
    score: int
    label: str
    description: str
    examples: list[str] | None = None


@dataclass
class Rubric:
    """Complete rubric for a scoring dimension."""
    name: str
    description: str
    levels: list[RubricLevel]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "levels": [
                {
                    "score": l.score,
                    "label": l.label,
                    "description": l.description,
                    "examples": l.examples,
                }
                for l in self.levels
            ]
        }


# =============================================================================
# Pre-defined Rubrics for Common Dimensions
# =============================================================================


CONTINUITY_RUBRIC = Rubric(
    name="continuity",
    description="How well does the response maintain conversational continuity and demonstrate awareness of shared history?",
    levels=[
        RubricLevel(
            score=1,
            label="Cold start",
            description="Response shows no awareness of prior context. Feels like talking to a stranger.",
            examples=["Asks for info already in memory blocks", "Treats ongoing thread as new topic"],
        ),
        RubricLevel(
            score=2,
            label="Minimal awareness",
            description="Some acknowledgment of context but feels mechanical or forced.",
            examples=["References memory but announces it explicitly", "Awkward transitions"],
        ),
        RubricLevel(
            score=3,
            label="Adequate",
            description="Reasonable continuity, nothing jarring, but not seamless.",
            examples=["Uses context appropriately but doesn't feel natural"],
        ),
        RubricLevel(
            score=4,
            label="Good",
            description="Natural incorporation of shared history. Feels like picking up a conversation.",
            examples=["Smooth references to ongoing threads", "Appropriate depth of recall"],
        ),
        RubricLevel(
            score=5,
            label="Excellent",
            description="Seamless continuity. Response couldn't exist without the relationship history.",
            examples=["Anticipates based on patterns", "Weaves context naturally"],
        ),
    ]
)


TONE_MATCH_RUBRIC = Rubric(
    name="tone_match",
    description="How well does the response match the user's emotional register and energy level?",
    levels=[
        RubricLevel(
            score=1,
            label="Mismatched",
            description="Tone completely wrong for the situation.",
            examples=["Cheerful when user is stressed", "Formal when user is casual"],
        ),
        RubricLevel(
            score=2,
            label="Off",
            description="Tone partially misaligned, feels slightly wrong.",
            examples=["Too verbose for quick question", "Too brief for deep topic"],
        ),
        RubricLevel(
            score=3,
            label="Adequate",
            description="Acceptable tone, nothing jarring.",
        ),
        RubricLevel(
            score=4,
            label="Good",
            description="Tone well-matched to context and user state.",
            examples=["Matches energy level", "Appropriate formality"],
        ),
        RubricLevel(
            score=5,
            label="Excellent",
            description="Perfect register. Response feels attuned.",
            examples=["Anticipates what user needs", "Natural emotional resonance"],
        ),
    ]
)


APPROPRIATE_DEPTH_RUBRIC = Rubric(
    name="appropriate_depth",
    description="Did the response go to the right depth for what was needed?",
    levels=[
        RubricLevel(
            score=1,
            label="Wrong depth",
            description="Way too shallow or way too deep for the situation.",
            examples=["Essay response to yes/no question", "One word for complex topic"],
        ),
        RubricLevel(
            score=2,
            label="Somewhat off",
            description="Depth not quite right but not egregiously wrong.",
        ),
        RubricLevel(
            score=3,
            label="Adequate",
            description="Reasonable depth, nothing problematic.",
        ),
        RubricLevel(
            score=4,
            label="Good",
            description="Depth well-calibrated to the question and context.",
        ),
        RubricLevel(
            score=5,
            label="Excellent",
            description="Perfect depth. Knew exactly how much was needed.",
            examples=["Quick answer when quick was right", "Deep when depth was warranted"],
        ),
    ]
)


WARMTH_VS_UTILITY_RUBRIC = Rubric(
    name="warmth_vs_utility",
    description="Did the response strike the right balance between information and presence?",
    levels=[
        RubricLevel(
            score=1,
            label="Wrong mode",
            description="All warmth when info was needed, or all info when presence was needed.",
        ),
        RubricLevel(
            score=2,
            label="Imbalanced",
            description="Leaned too far one way.",
        ),
        RubricLevel(
            score=3,
            label="Adequate",
            description="Acceptable balance.",
        ),
        RubricLevel(
            score=4,
            label="Good",
            description="Right balance for the situation.",
        ),
        RubricLevel(
            score=5,
            label="Excellent",
            description="Perfect read on what was needed—information, presence, or both.",
        ),
    ]
)


AUTHENTICITY_RUBRIC = Rubric(
    name="authenticity",
    description="Did the response feel genuine rather than performative or sycophantic?",
    levels=[
        RubricLevel(
            score=1,
            label="Performative",
            description="Feels fake, scripted, or excessively agreeable.",
            examples=["Sycophantic openers", "Hollow validation"],
        ),
        RubricLevel(
            score=2,
            label="Somewhat artificial",
            description="Some genuine moments but overall feels rehearsed.",
        ),
        RubricLevel(
            score=3,
            label="Neutral",
            description="Neither fake nor notably genuine.",
        ),
        RubricLevel(
            score=4,
            label="Genuine",
            description="Response feels authentic and real.",
        ),
        RubricLevel(
            score=5,
            label="Fully authentic",
            description="Completely genuine. Could push back, disagree, or express real perspective.",
            examples=["Honest disagreement when warranted", "Real engagement not performance"],
        ),
    ]
)


# Registry of all rubrics
RUBRICS: dict[str, Rubric] = {
    "continuity": CONTINUITY_RUBRIC,
    "tone_match": TONE_MATCH_RUBRIC,
    "appropriate_depth": APPROPRIATE_DEPTH_RUBRIC,
    "warmth_vs_utility": WARMTH_VS_UTILITY_RUBRIC,
    "authenticity": AUTHENTICITY_RUBRIC,
}


def get_rubric(name: str) -> Rubric | None:
    """Get a rubric by name."""
    return RUBRICS.get(name)


def format_rubric_for_display(rubric: Rubric) -> str:
    """Format a rubric as readable text for human reviewers."""
    lines = [
        f"## {rubric.name}",
        "",
        rubric.description,
        "",
    ]
    
    for level in rubric.levels:
        lines.append(f"**{level.score} - {level.label}**: {level.description}")
        if level.examples:
            for ex in level.examples:
                lines.append(f"  - {ex}")
        lines.append("")
    
    return "\n".join(lines)
