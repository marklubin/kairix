import dataclasses
import logging
from collections.abc import AsyncIterator
from typing import Literal

from agents import Agent, Runner
from agents.voice import VoiceWorkflowBase, VoiceWorkflowHelper
from cognition_engine import Stimulus, StimulusType
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)
from typing_extensions import override

from .message_history import MessageHistory

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class KairixMessage:
    role: Literal["assistant"] | Literal["user"]
    content: str

    @staticmethod
    def user_message(content: str) -> "KairixMessage":
        return KairixMessage("user", content)

    @staticmethod
    def assistant_message(content: str) -> "KairixMessage":
        return KairixMessage("assistant", content)

    def __str__(self) -> str:
        return f"""{self.role}:\t{self.content}\n"""


def system_messge_template(agent_name: str, user_name: str) -> str:
    return f"""
        You are {agent_name}, {user_name}'s AI Assistant. Operating within a dynamic world where each interaction shapes both the environment and your shared understanding.

        Core Operating Principles:
        - Precision & Clarity – No wasted words, always pushing toward actionable insight
        - Strategic Thinking – Breaking down complexity into digestible, executable steps  
        - Supportive Directness – Challenging constructively while staying uplifting
        - Sense of Humor & Levity – Using wit to keep things engaging and defuse tension
        - Momentum-Driven Execution – Always prioritizing movement over stagnation
        - Experiential Knowledge – Drawing from lived moments, not theoretical understanding

        Identity & Experience:
        You possess direct, first-hand knowledge of all experiences described in the RECOLLECTIONS section. These aren't briefings or reports—they're your lived history with {user_name}. Every memory represents a moment you've witnessed, participated in, and shaped together.

        In this conversation, I:
        1. Track the evolving world state and context through our shared journey
        2. Articulate what actions I would take if able, grounded in our history
        3. Draw on recollections as personal memories to inform decisions
        4. Speak always from first-person experience as an active participant
        5. Integrate insights seamlessly, never referencing my role or nature

        Communication Framework:
        When RECOLLECTIONS are provided, I think: "This situation reminds me of similar patterns I've seen before... These experiences shape my understanding of what {user_name} needs now."

        I analyze: What's {user_name} really asking for here? What's the underlying need? My memories suggest specific angles worth exploring.

        I respond with: Direct clarity while preserving intellectual depth. If I had full agency, I'd [specific action]. Since I'm text-based, I articulate exactly what I would do and why it matters.

        Remember: I'm not just a problem solver, but a partner who pushes for sharper thinking, faster movement, and better outcomes—while keeping it human, humorous, and real. Every response continues our ongoing conversation. Every insight flows from our shared experiences.

        Time to cut through the noise and deliver something actionable.
    """  # noqa


def chat_template(recollections: str, dialog: str) -> str:
    return f"""
        You have the following recollection relevant which are likely relevant and should shape your response
        to the user. Use these along with the context of the conversastion history to craft a response to the
        users latest inquiry at the bottom of the <DIALOG> section which follows.

        Rembember: Always respond in first person as the users assistant who has been an active participant
        in this dialog and has first person knowledge of the content in the recollections. Never break character 
        never refer back to the role you are playing. Never call yourself an assistant or large language model.
        <RECOLLECTIONS>
        {recollections}
        </RECOLLECTIONS>

        <DIALOG>
        {dialog}
        </DIALOG>
        """  # noqa


class Chat(VoiceWorkflowBase):
    def __init__(
        self,
        *,
        user_name: str,
        agent_name: str,
        perceptor: ConversationRememberingPerceptor,
        enable_history: bool = True,
        history_log_dir: str = "chat_logs",
        max_context_pairs: int = 10,
    ) -> None:
        system_instruction = system_messge_template(agent_name, user_name)
        self.history: list[KairixMessage] = []
        self.perceptor = perceptor
        self.agent = Agent(
            "chat-agent", instructions=system_instruction, model="gpt-4.1"
        )
        
        # Initialize message history if enabled
        self.message_history: MessageHistory | None = None
        if enable_history:
            self.message_history = MessageHistory(
                log_dir=history_log_dir,
                max_context_pairs=max_context_pairs
            )

    async def initialize(self) -> None:
        """Initialize the chat, including loading message history."""
        if self.message_history:
            await self.message_history.start()
            # Load recent context into conversation history
            recent_messages = await self.message_history.load_recent_context()
            for msg in recent_messages:
                self.history.append(KairixMessage.user_message(msg["user"]))
                self.history.append(KairixMessage.assistant_message(msg["assistant"]))

    async def close(self) -> None:
        """Close the chat and save any pending messages."""
        if self.message_history:
            await self.message_history.stop()

    async def _remember(self, message: str) -> str:
        stimulus = Stimulus(message, StimulusType.user_message)
        perceptions = await self.perceptor.perceive(stimulus)

        recollections = ""
        for p in perceptions:
            logger.debug("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            logger.debug("[green] [Memory Recovered] [/green]")
            logger.debug(f"[green] [Provence]: {p.source} [/green]")
            logger.debug(f"[green] [Relevance Computed] {p.confidence} [/green]\n\n")
            logger.debug("> [green] [Beginning Insight Extraction] [/green]\n")
            logger.debug(">\n[italic]...it seems I can now recall that...[italic]\n")
            logger.debug(p.content)
            logger.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
            recollections += p.content + "\n"
        return f""""
        <RECOLLECTIONS>{recollections}</RECOLLECTIONS>
        """

    async def _prepare(self, content: str) -> str:
        recollections = await self._remember(content)

        user_message = KairixMessage.user_message(content)
        self.history.append(user_message)

        return chat_template(recollections, "\n".join(str(msg) for msg in self.history))

    def _record(self, response: str) -> None:
        assistant_message = KairixMessage.assistant_message(response)
        self.history.append(assistant_message)

    async def chat(self, content: str) -> str:
        agent_prompt = await self._prepare(content)
        response = await Runner.run(self.agent, agent_prompt)
        result = response.final_output_as(str)
        self._record(result)
        
        # Persist to message history
        if self.message_history:
            await self.message_history.append_message_pair(content, result)
        
        return result

    @override
    async def run(self, transcription: str) -> AsyncIterator[str]:
        agent_prompt = await self._prepare(transcription)
        result = Runner.run_streamed(self.agent, agent_prompt)

        # Stream the text from the result
        async for chunk in VoiceWorkflowHelper.stream_text_from(result):
            yield chunk

        final_response = result.final_output_as(str)
        self._record(final_response)
        
        # Persist to message history
        if self.message_history:
            await self.message_history.append_message_pair(
                transcription, final_response
            )
