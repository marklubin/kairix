from __future__ import annotations

import asyncio
import dataclasses
import logging
from typing import TYPE_CHECKING, Literal

from agents import Agent
from agents.voice import VoiceWorkflowBase, VoiceWorkflowHelper
from cognition_engine import Perceptor, Stimulus, StimulusType
from cognition_engine.configuration import prompts
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from cognition_engine.configuration.runner import CognitionAgentRunner
    from cognition_engine.perceptor.summary_insight import SummaryInsightPerceptor
    
    from .conversation_history_perceptor import ConversationHistoryPerceptor

logger = logging.getLogger(__name__)

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"


class ActionReflectionStimulus(Stimulus):
    """Custom stimulus type for assistant responses."""
    def __init__(self, content: str):
        # Create a custom stimulus type for action reflection
        super().__init__(content, type=StimulusType.user_message)
        self.type = type(
            "ActionReflectionType", 
            (), 
            {"value": "action_reflection", "name": "action_reflection"}
        )()


@dataclasses.dataclass
class KairixMessage:
    role: Literal["assistant"] | Literal["user"]
    content: str

    @staticmethod
    def user_message(content: str) -> KairixMessage:
        return KairixMessage("user", content)

    @staticmethod
    def assistant_message(content: str) -> KairixMessage:
        return KairixMessage("assistant", content)

    def __str__(self) -> str:
        return f"""{self.role}:\t{self.content}\n"""


class Chat(VoiceWorkflowBase):
    def __init__(
        self,
        *,
        user_name: str,
        agent_name: str,
        runner: CognitionAgentRunner,
        perceptor: SummaryInsightPerceptor,
        history_perceptor: ConversationHistoryPerceptor | None = None,
        environmental_perceptor: Perceptor | None = None,
    ) -> None:
        self.history: list[KairixMessage] = []
        self.perceptor = perceptor

        conversationalist_instruction = (
            prompts.conversationalist_instruction_template_v1(agent_name, user_name)
        )

        self.agent = Agent("chat-agent", instructions=conversationalist_instruction)

        self.runner = runner
        self.history_perceptor = history_perceptor
        self.environmental_perceptor = environmental_perceptor

    async def initialize(self) -> None:
        """Initialize the chat, including loading message history."""
        if self.history_perceptor:
            # Load recent context into conversation history
            recent_messages = await self.history_perceptor.get_recent_context()
            for msg in recent_messages:
                self.history.append(KairixMessage.user_message(msg["user"]))
                self.history.append(KairixMessage.assistant_message(msg["assistant"]))

    async def close(self) -> None:
        """Close the chat."""
        pass

    async def _remember(self, message: str) -> tuple[str, str]:
        """
        Gather perceptions from all perceptors in parallel.
        Returns: (recollections, environmental_context)
        """
        stimulus = Stimulus(message, StimulusType.user_message)
        
        # Create tasks for all perceptors
        tasks = []
        task_names = []
        
        # Main memory perceptor
        tasks.append(self.perceptor.perceive(stimulus))
        task_names.append("memory")
        
        # Environmental perceptor
        if self.environmental_perceptor:
            tasks.append(self.environmental_perceptor.perceive(stimulus))
            task_names.append("environmental")
        
        # History perceptor (doesn't return perceptions)
        if self.history_perceptor:
            tasks.append(self.history_perceptor.perceive(stimulus))
            task_names.append("history")
        
        # Run all perceptors in parallel
        results = await asyncio.gather(*tasks)
        
        # Process results
        recollections = ""
        environmental_context = ""
        
        for name, perceptions in zip(task_names, results, strict=False):
            if name == "memory":
                for p in perceptions:
                    logger.debug("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    logger.debug("[Memory Recovered]")
                    logger.debug(f"[Provence]: {p.source}")
                    logger.debug(">\n...it seems I can now recall that...\t")
                    logger.debug(p.content)
                    logger.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
                    recollections += p.content + "\n"
            elif name == "environmental" and perceptions:
                # Environmental context is a single perception
                environmental_context = perceptions[0].content if perceptions else ""
        
        return (
            f"<RECOLLECTIONS>{recollections}</RECOLLECTIONS>" if recollections else "",
            environmental_context
        )

    async def _prepare(self, content: str) -> str:
        recollections, environmental_context = await self._remember(content)

        user_message = KairixMessage.user_message(content)
        self.history.append(user_message)

        dialog = "\n".join(str(msg) for msg in self.history)
        
        # Combine recollections with environmental context
        full_context = ""
        if environmental_context:
            full_context += f"""
        <ENVIRONMENTAL_CONTEXT>
        You have access to the following real-time environmental information:
        {environmental_context}
        
        Use this information naturally when relevant to provide timely and 
        contextual responses. For example, you might reference the current time, 
        weather, or location when appropriate.
        </ENVIRONMENTAL_CONTEXT>
        """
        
        if recollections:
            full_context += f"\n        {recollections}"
        
        result = prompts.conversationalist_message_template_v1(full_context, dialog)
        assert isinstance(result, str), "Template should return a string"
        return result

    def _record(self, response: str) -> None:
        assistant_message = KairixMessage.assistant_message(response)
        self.history.append(assistant_message)

    @override
    async def run(self, transcription: str) -> AsyncIterator[str]:
        async for chunk in self.chat(transcription):
            yield chunk

    async def chat(self, content: str) -> AsyncIterator[str]:
        agent_prompt = await self._prepare(content)
        result = await self.runner.run_streamed(self.agent, agent_prompt)

        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            yield chunk

        final_response = result.final_output_as(str)
        self._record(final_response)

        # Send assistant response to history perceptor
        if self.history_perceptor:
            reflection_stimulus = ActionReflectionStimulus(final_response)
            await self.history_perceptor.perceive(reflection_stimulus)
