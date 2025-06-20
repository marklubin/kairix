import asyncio
import logging
from typing import List, AsyncIterator

from agents import Agent
from openai.types.responses import ResponseTextDeltaEvent

from ..perceptor import Perceptor
from kairix_core.types.cognition import Stimulus, Perception, StimulusType
from kairix_core.util.utils import MessageTurnFormatter

from kairix_core.prompt import agent_prompts as prompts
from kairix_core.runtime.agent import AgentRuntime

logger = logging.getLogger(__name__)


class ConversationalPersona:
    def __init__(
        self,
        *,
        persona_name: str,
        user_name: str,
        runtime: AgentRuntime,
        perceptors: List[Perceptor],
        actuating_agent: Agent,
        reflection_perceptors: List[Perceptor],
    ):
        self.persona_name = persona_name
        self.user_name = user_name
        self.runner: AgentRuntime = runtime
        self.message_turn_formatter = MessageTurnFormatter(user_name, persona_name)
        self.perceptors = perceptors
        self.actuating_agent = actuating_agent
        self.reflection_perceptors = reflection_perceptors

        logger.info(f"""
                Kairix Persona Cognition Engine v.0.01
           
                Cognition Configuration Summary
                
                Persona Name: {self.persona_name}
                User Name: {self.user_name}
                Registered Perceptors: {len(self.perceptors)}
                Actuating Model: {self.actuating_agent.model}
                Reflection Perceptors: {len(self.reflection_perceptors)}
                
                Mark Lubin (supported by Claude)
                Niteshift.ai DBA Apiana Systems, 2025. Los Angeles and San Francisco in California.
        """)

    async def _converse(self, stimulus: Stimulus, perceptions: list[Perception]) -> AsyncIterator[str]:
        logger.info("Preparing %d perceptions.", len(perceptions))
        message = prompts.conversationalist_message_template_v2(perceptions, stimulus.content)

        logger.debug("Prepared message: %s", message)
        i = 0

        async for event in self.runner.run_streamed(self.actuating_agent, message).stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                logger.debug(f"Chunk {i}, yielding from stream")
                yield event.data.delta
                i += 1

    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:
        logger.info(f"Responding to stimulus of type: {stimulus.type}.")

        coroutines = [p.perceive(stimulus) for p in self.perceptors]
        logger.info("Awaiting perceptions..")

        results = await asyncio.gather(*coroutines)

        perceptions: list[Perception] = []
        for r in results:
            perceptions.extend(r)

        if stimulus.type == StimulusType.user_message:
            logger.info("Responding to user message by conversing.")

            full_response = ""
            async for chunk in self._converse(stimulus, perceptions):
                full_response = full_response + chunk
                yield full_response

            message_turn = self.message_turn_formatter.format_turn(stimulus.content, full_response)

            reflection_stimulus = Stimulus(content=message_turn, type=StimulusType.self_perception)

            reflection_tasks = set()
            for reflector in self.reflection_perceptors:
                task = asyncio.create_task(reflector.perceive(reflection_stimulus))
                reflection_tasks.add(task)
                task.add_done_callback(reflection_tasks.discard)
        else:
            raise NotImplementedError("Unsupported stimulus. Unable to respond.")
