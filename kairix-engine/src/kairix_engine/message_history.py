import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

import aiofiles
import yaml

logger = logging.getLogger(__name__)


class MessageHistory:
    """Handles persistent storage of chat message history in YAML format."""
    
    def __init__(
        self,
        log_dir: str = "chat_logs",
        max_context_pairs: int = 10
    ):
        """
        Initialize message history handler.
        
        Args:
            log_dir: Directory for storing daily chat logs
            max_context_pairs: Number of recent message pairs to load on startup
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_context_pairs = max_context_pairs
        self._file: Any | None = None  # aiofiles typing is incomplete
        self._write_lock = asyncio.Lock()
        
        # Create today's file and open it
        today = datetime.date.today()
        self._filename = self.log_dir / f"chat_{today.strftime('%Y-%m-%d')}.yaml"
        
    async def start(self) -> None:
        """Open the log file for writing."""
        # If file doesn't exist, create with header
        if not self._filename.exists():
            async with aiofiles.open(self._filename, 'w') as f:
                await f.write("messages:\n")
        
        # Open file in append mode
        self._file = await aiofiles.open(self._filename, 'a')
        
    async def stop(self) -> None:
        """Close the file handle."""
        if self._file:
            await self._file.close()
            self._file = None
            
    async def append_message_pair(self, user_msg: str, assistant_msg: str) -> None:
        """
        Append a message pair to the log file.
        
        Args:
            user_msg: User's message
            assistant_msg: Assistant's response
        """
        message = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "user": user_msg,
            "assistant": assistant_msg
        }
        
        # Fire and forget the write operation
        asyncio.create_task(  # type: ignore[unused-awaitable]  # noqa: RUF006
            self._write_message_async(message)
        )
        
    async def load_recent_context(self) -> list[dict[str, str]]:
        """
        Load the most recent message pairs from history.
        
        Returns:
            List of message dictionaries
        """
        # Get list of log files sorted by date (newest first)
        log_files = sorted(self.log_dir.glob("chat_*.yaml"), reverse=True)
        
        all_messages: list[dict[str, str]] = []
        
        # Read messages from files until we have enough
        for log_file in log_files:
            try:
                async with aiofiles.open(log_file) as f:
                    content = await f.read()
                    data = yaml.safe_load(content) or {}
                    messages = data.get("messages", [])
                    
                    # Prepend messages (newer files first)
                    all_messages = messages + all_messages
                    
                    # Stop if we have enough messages
                    if len(all_messages) >= self.max_context_pairs:
                        return all_messages[-self.max_context_pairs:]
                        
            except Exception as e:
                logger.error(f"Error loading messages from {log_file}: {e}")
                continue
                
        return all_messages
            
    async def _write_message_async(self, message: dict[str, str]) -> None:
        """
        Write a message to the log file.
        
        Args:
            message: Message dictionary to write
        """
        try:
            # Log the message pair at debug level
            logger.debug(
                f"Writing message pair - User: {message['user']} | "
                f"Assistant: {message['assistant']}"
            )
            
            async with self._write_lock:
                if self._file:
                    # Format message as YAML list item with proper escaping
                    # Use yaml.dump to properly escape special characters
                    yaml_entry = yaml.dump(
                        [{
                            "timestamp": message['timestamp'],
                            "user": message['user'],
                            "assistant": message['assistant']
                        }], 
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False
                    ).strip()  # Remove trailing newline
                    
                    # Ensure proper indentation for list item
                    yaml_entry = yaml_entry.replace("\n", "\n  ")  # Indent all lines
                    yaml_entry = "  " + yaml_entry  # Indent first line
                    
                    # Write and flush with newline
                    await self._file.write(yaml_entry + "\n")
                    await self._file.flush()
                    
        except Exception as e:
            # Log each message on its own line as error
            logger.error(f"Failed to write message pair to file: {e}")
            logger.error(f"User message: {message['user']}")
            logger.error(f"Assistant message: {message['assistant']}")
            # Don't re-raise to prevent losing messages