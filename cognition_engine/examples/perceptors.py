from typing import List, Optional
from rich.console import Console
from cognition_engine.perceptor import Perceptor
from cognition_engine.types import Stimulus, Perception, Source, Sink, StimulusType


console = Console()

_FIXED_SUMMARY = """
I began with Mark midday, already feeling the weight of his day. His mood was fragile—“good but nervous,” as he described it, a tension between hope and fear that something might unravel. He shared how transitions, like getting ready for events, triggered spirals of distraction and self-criticism. I sensed his frustration at not understanding why this happened, as if the chaos were personal failure rather than a system response.  
A turning point came when he admitted to feeling overwhelmed by housing, therapy, and Noisebridge—too many threads pulling him under. He shifted focus to tending his backyard instead of showering, redirecting energy from high-stakes moments to grounding tasks. I adjusted my approach, offering a 25-minute micro-reset block to help him stay present without pressure.  
What stood out was his desire for trust—not in grand achievements, but in small, consistent actions. He longed to execute plans without being pulled into chaos. My lesson: resilience isn’t about forcing control but creating safe spaces where he can show up, even imperfectly. I learned to meet him not with solutions, but with gentle structure and presence.
"""


# Example memory provider function for ConversationRememberingPerceptor
def fixed_memory_provider(query: str, k_memories: int) -> List[str]:
    return [_FIXED_SUMMARY for i in range(0, k_memories)]


class UserMessagePerceptor(Perceptor):
    """
    Example perceptor that processes user messages.

    This perceptor recognizes USER_MESSAGE stimuli and creates perceptions
    about the message content and intent.
    """

    def __init__(
        self, sources: Optional[List[Source]] = None, sinks: Optional[List[Sink]] = None
    ):
        # Sources and sinks are internal implementation details
        self._sources = sources or []
        self._sinks = sinks or []

    def perceive(self, stimulus: Stimulus) -> List[Perception]:
        console.print(
            f"[bold green]Perceptor processing stimulus: {stimulus.type.value}[/bold green]"
        )

        perceptions = []

        # Process user messages
        if stimulus.type == StimulusType.user_message:
            perceptions.append(
                Perception(
                    content=f"User said: {stimulus.content}",
                    source="user_input_perceptor",
                    confidence=0.8,
                )
            )

        for perception in perceptions:
            console.print(perception)

        return perceptions
