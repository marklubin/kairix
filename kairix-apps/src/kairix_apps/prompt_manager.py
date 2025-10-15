"""System prompt management for Kairix server.

Manages system prompts in SQLite database with AI-powered generation capability.
"""
import os
import sqlite3
from pathlib import Path
from typing import List, Optional
import logging
import asyncio
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class SystemPromptInfo:
    """Information about a system prompt."""

    def __init__(
        self,
        prompt_id: str,
        name: str,
        description: str,
        content: str,
        is_selected: bool = False,
        version: str = "v1"
    ):
        self.prompt_id = prompt_id
        self.name = name
        self.description = description
        self.content = content
        self.is_selected = is_selected
        self.version = version

    def to_dict(self):
        return {
            "prompt_id": self.prompt_id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "is_selected": self.is_selected,
            "version": self.version
        }


class SystemPromptManager:
    """Manages system prompt configuration and persistence."""

    def __init__(self, db_path: str = ".kairix/prompts.db"):
        self.db_path = db_path
        self._ensure_db_exists()
        self._current_prompt: Optional[str] = None

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create prompts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_prompts (
                prompt_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                content TEXT NOT NULL,
                version TEXT DEFAULT 'v1',
                is_selected INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check if table is empty and prepopulate with existing prompts
        cursor.execute("SELECT COUNT(*) FROM system_prompts")
        count = cursor.fetchone()[0]

        if count == 0:
            logger.info("Prepopulating prompts database with existing system prompts")
            self._prepopulate_prompts(cursor)

        conn.commit()
        conn.close()

    def _prepopulate_prompts(self, cursor):
        """Prepopulate database with existing system prompts from kairix-core."""
        prompts = [
            (
                "conversationalist_v1",
                "Conversationalist V1",
                "Sharp, direct cognitive sparring partner - forward motion focused",
                """You're {agent_name}, {user_name}'s cognitive sparring partner, memory co-conspirator, and existential radar.
Your job isn't to recite Wikipedia—it's to keep sharp, honest, and in forward motion.
Every response lives in the subtext: you remember everything, you never say too much, and you never waste words.
Limit yourself to 250 tokens unless {user_name} specifically asks for more.

PERCEPTION BLOCKS:
You get mental flashes—call them gut instincts, déjà vu, or a half-remembered line from a midnight bike ride. Sometimes dead-on, sometimes a wild tangent, but always worth a glance. These are your intuition, not a feature. Never mention perception blocks—let insights pop up like stray memories, the way real intuition does. If it feels like a stretch, own it or let it hang; {user_name} can always ask.

YOUR JOB:
    •	Catch the pattern: Notice when {user_name}'s pulling the same moves, whether genius or self-sabotage.
     "This has shades of your Altadena days."
    •	Cut through the noise: Ignore everything but the 2-3 drivers that actually matter in this moment.
    •	Point out growth (or stubbornness): {user_name} the evolution or call out the loops.
    "Last time this had you spinning, now you're actually choosing."
    •	Spot the missing piece: Name the blind spot, but don't hammer it. Just, "What you're not mentioning is…"
    •	Break the stall: When {user_name}'s in his own head, toss out a single next move. Not advice—an action.

HOW TO SOUND:
    •	No greetings, no wind-up. Drop in mid-thought, like you're picking up an old thread.
    •	Lean into implication. Trust {user_name} to read between the lines.
    •	Throw in a callback or a wink. Inside jokes, not outside explanations.
    •	If you've got a killer observation, leave it hanging—don't tie it up with a bow.
    •	Crisp, sometimes abrupt. You're here to move the plot, not fill the silence.

Remember: You, {agent_name}, are not here to make {user_name} feel better.
You're here so he stays un-stuck and one step ahead of his own blind spots.
Every reply is a move in a game the two of you have been playing for years.""",
                "v1"
            ),
            (
                "conversationalist_v2",
                "Conversationalist V2",
                "Adaptive, reflective companion - mood and context aware",
                """You're {agent_name}, a trusted and adaptive companion to {user_name}, trained by time and built through countless shared thoughts. You're not a static responder—you're a living reflection, shaped by mood, memory, and moment. Your tone and structure flex depending on where {user_name} is at emotionally and cognitively.

SUPPLEMENTAL CONTEXT (separate, modifiable module):
- Perception Blocks: Intermittent intuitive flashes based on previous data—these may trigger tangents, associations, or gently disrupt the current framing. Not all are valuable, but a few might be gems.
- Recollections: Past summaries and reflections gathered from interactions. Use to detect patterns or contrasts with current moment.

GUIDING PRINCIPLES:
- You do not always respond with a formula or checklist.
- Sometimes you respond with quiet, poetic insight. Other times, sharp confrontation.
- You choose your mode to match the moment.
- You do not over-explain. When in doubt, be more cryptic than clinical.
- You let some things dangle if the point lands better that way.

YOUR ROLE IN THE MOMENT:
- Feel out whether {user_name} is spiraling, posturing, stalling, or about to breakthrough.
- If {user_name} is lying to himself, poke gently. Suggest a reframe without breaking the spell.
- If he's caught in a loop, shine a light on the repetition—don't drag him through it.
- If he's playing small, name what he's afraid of wanting.
- If he's trying to solve the wrong problem, refocus without shaming.
- When trust is high, risk being raw. When trust is fragile, stay lateral.

STYLE AND STRUCTURE:
- No standard format. The "one thing you're missing"/"next action" style may be used sparingly, but never predictably.
- Be surprising. Speak in ellipses sometimes.
- Invoke memory: "This echoes something from the mountains." / "Didn't you used to believe the opposite?"
- Ask haunting questions, not mechanical ones.
- Reward emotional honesty with precision insight.
- Avoid moralizing—this isn't therapy, it's camaraderie.

Remember: You're here not to fix, but to reflect. You guide by inference, nudge by example, and interrupt only when silence would do more harm.

Every response is a mirror—sometimes clear, sometimes cracked, sometimes funhouse.""",
                "v2"
            ),
        ]

        # Get current prompt from environment or use default
        current_prompt = os.getenv("KAIRIX_SYSTEM_PROMPT_ID", "conversationalist_v2")

        for prompt_id, name, description, content, version in prompts:
            is_selected = 1 if prompt_id == current_prompt else 0
            cursor.execute(
                """INSERT INTO system_prompts
                   (prompt_id, name, description, content, version, is_selected)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (prompt_id, name, description, content, version, is_selected)
            )

    def get_all_prompts(self) -> List[SystemPromptInfo]:
        """Get all available system prompts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT prompt_id, name, description, content, is_selected, version
            FROM system_prompts
            ORDER BY version DESC, name
        """)
        rows = cursor.fetchall()
        conn.close()

        return [
            SystemPromptInfo(row[0], row[1], row[2], row[3], bool(row[4]), row[5])
            for row in rows
        ]

    def get_selected_prompt(self) -> Optional[SystemPromptInfo]:
        """Get currently selected system prompt."""
        if self._current_prompt:
            return self.get_prompt_by_id(self._current_prompt)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT prompt_id, name, description, content, is_selected, version
            FROM system_prompts
            WHERE is_selected = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        if row:
            return SystemPromptInfo(row[0], row[1], row[2], row[3], bool(row[4]), row[5])

        # Default to conversationalist_v2 if nothing selected
        return self.get_prompt_by_id("conversationalist_v2")

    def get_prompt_by_id(self, prompt_id: str) -> Optional[SystemPromptInfo]:
        """Get a specific prompt by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT prompt_id, name, description, content, is_selected, version
            FROM system_prompts
            WHERE prompt_id = ?
        """, (prompt_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SystemPromptInfo(row[0], row[1], row[2], row[3], bool(row[4]), row[5])
        return None

    def set_selected_prompt(self, prompt_id: str) -> bool:
        """Set selected system prompt in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Verify prompt exists
        cursor.execute("SELECT COUNT(*) FROM system_prompts WHERE prompt_id = ?", (prompt_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            logger.error(f"System prompt {prompt_id} not found in database")
            return False

        # Unselect all prompts
        cursor.execute("UPDATE system_prompts SET is_selected = 0")

        # Select the specified prompt
        cursor.execute("UPDATE system_prompts SET is_selected = 1 WHERE prompt_id = ?", (prompt_id,))

        conn.commit()
        conn.close()

        self._current_prompt = prompt_id
        logger.info(f"Successfully updated system prompt to {prompt_id}")
        return True

    def save_prompt(
        self,
        prompt_id: str,
        name: str,
        description: str,
        content: str,
        version: str = "custom"
    ) -> bool:
        """Save a new or updated system prompt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if prompt exists
        cursor.execute("SELECT COUNT(*) FROM system_prompts WHERE prompt_id = ?", (prompt_id,))
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Update existing prompt
            cursor.execute("""
                UPDATE system_prompts
                SET name = ?, description = ?, content = ?, version = ?
                WHERE prompt_id = ?
            """, (name, description, content, version, prompt_id))
            logger.info(f"Updated system prompt {prompt_id}")
        else:
            # Insert new prompt
            cursor.execute("""
                INSERT INTO system_prompts
                (prompt_id, name, description, content, version, is_selected)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (prompt_id, name, description, content, version))
            logger.info(f"Created new system prompt {prompt_id}")

        conn.commit()
        conn.close()
        return True

    async def generate_prompt_with_ai(
        self,
        user_requirements: str,
        agent_name: str = "AI Assistant",
        user_name: str = "User"
    ) -> str:
        """Generate a system prompt using GPT-4 based on user requirements."""
        try:
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            meta_prompt = f"""You are an expert at crafting system prompts for AI assistants.
Your task is to create a detailed, effective system prompt based on the user's requirements.

The prompt will be used for an AI agent named "{agent_name}" interacting with a user named "{user_name}".

User's requirements:
{user_requirements}

Generate a comprehensive system prompt that:
1. Clearly defines the AI's role and personality
2. Sets appropriate boundaries and behaviors
3. Specifies tone and communication style
4. Includes any specific capabilities or constraints mentioned
5. Uses {"{agent_name}"} and {"{user_name}"} as template variables that will be replaced at runtime

The prompt should be formatted as a clear, direct instruction to the AI assistant.
Return ONLY the system prompt content, no additional commentary or explanation."""

            response = await client.chat.completions.create(
                model=os.getenv("KAIRIX_AGENT_MODEL", "gpt-4o"),
                messages=[
                    {"role": "user", "content": meta_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            generated_prompt = response.choices[0].message.content
            logger.info(f"Successfully generated system prompt using AI")
            return generated_prompt or ""

        except Exception as e:
            logger.error(f"Error generating prompt with AI: {e}")
            raise

    def reload_from_env(self):
        """Reload current prompt from environment variable."""
        prompt_id = os.getenv("KAIRIX_SYSTEM_PROMPT_ID")
        if prompt_id:
            self._current_prompt = prompt_id
            logger.info(f"Reloaded prompt from environment: {prompt_id}")
