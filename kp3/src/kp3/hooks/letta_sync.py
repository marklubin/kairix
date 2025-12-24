"""Letta sync hook for pushing world model state to Letta core memory."""

import logging
from pathlib import Path

import httpx
import yaml

from kp3.config import get_settings
from kp3.db.models import Passage
from kp3.services.refs import register_hook

logger = logging.getLogger(__name__)


class LettaSyncConfig:
    """Configuration for Letta sync."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Load config from YAML file or use defaults.

        Args:
            config_path: Path to YAML config file (optional)
        """
        self.base_url = get_settings().LETTA_BASE_URL
        self.mappings: list[dict[str, str]] = []

        if config_path:
            self._load_from_file(config_path)

    def _load_from_file(self, path: str | Path) -> None:
        """Load config from YAML file."""
        path = Path(path)
        if not path.exists():
            logger.warning("Letta sync config not found: %s", path)
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data:
            return

        if "letta_base_url" in data:
            self.base_url = data["letta_base_url"]

        if "mappings" in data:
            self.mappings = data["mappings"]

    def get_mapping(self, ref_name: str) -> dict[str, str] | None:
        """Get the Letta mapping for a ref name.

        Returns:
            Dict with agent_id and block_label, or None if not mapped
        """
        for mapping in self.mappings:
            if mapping.get("ref") == ref_name:
                return mapping
        return None


class LettaSyncClient:
    """Client for syncing to Letta core memory."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """Initialize the Letta sync client.

        Args:
            base_url: Letta API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def update_block(
        self,
        agent_id: str,
        block_label: str,
        content: str,
    ) -> bool:
        """Update a Letta core memory block.

        Args:
            agent_id: Letta agent ID
            block_label: Block label (human, persona, world)
            content: New content for the block

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First, get the block to find its ID
                response = await client.get(
                    f"{self.base_url}/v1/agents/{agent_id}/memory/block/{block_label}"
                )

                if response.status_code == 200:
                    block = response.json()
                    block_id = block.get("id")

                    # Update the block value
                    response = await client.patch(
                        f"{self.base_url}/v1/blocks/{block_id}",
                        json={"value": content},
                    )

                    if response.status_code == 200:
                        logger.info(
                            "Updated Letta block %s for agent %s",
                            block_label,
                            agent_id,
                        )
                        return True
                    else:
                        logger.error(
                            "Failed to update Letta block: %s %s",
                            response.status_code,
                            response.text,
                        )
                        return False

                elif response.status_code == 404:
                    # Block doesn't exist, create it
                    response = await client.post(
                        f"{self.base_url}/v1/agents/{agent_id}/memory/block",
                        json={
                            "label": block_label,
                            "value": content,
                            "limit": 5000,
                        },
                    )

                    if response.status_code in (200, 201):
                        logger.info(
                            "Created Letta block %s for agent %s",
                            block_label,
                            agent_id,
                        )
                        return True
                    else:
                        logger.error(
                            "Failed to create Letta block: %s %s",
                            response.status_code,
                            response.text,
                        )
                        return False

                else:
                    logger.error(
                        "Failed to get Letta block: %s %s",
                        response.status_code,
                        response.text,
                    )
                    return False

        except httpx.RequestError as e:
            logger.exception("Letta sync request failed: %s", e)
            return False


# Global config and client (initialized by register_letta_hooks)
_config: LettaSyncConfig | None = None
_client: LettaSyncClient | None = None


async def push_to_letta(ref_name: str, passage: Passage) -> None:
    """Push state passage content to Letta core memory block.

    This is the hook callback registered for world model refs.

    Args:
        ref_name: Name of the ref that was updated
        passage: The passage the ref now points to
    """
    if not _config or not _client:
        logger.warning("Letta sync not configured, skipping push")
        return

    mapping = _config.get_mapping(ref_name)
    if not mapping:
        logger.debug("No Letta mapping for ref %s, skipping", ref_name)
        return

    agent_id = mapping.get("agent_id")
    block_label = mapping.get("block_label")

    if not agent_id or not block_label:
        logger.warning("Invalid Letta mapping for %s: %s", ref_name, mapping)
        return

    await _client.update_block(
        agent_id=agent_id,
        block_label=block_label,
        content=passage.content,
    )


def register_letta_hooks(config_path: str | Path | None = None) -> None:
    """Register hooks to sync HEAD refs to Letta.

    Args:
        config_path: Path to YAML config file. If None, uses
                     settings.LETTA_SYNC_CONFIG_PATH
    """
    global _config, _client

    settings = get_settings()
    config_path = config_path or settings.LETTA_SYNC_CONFIG_PATH

    if not config_path:
        logger.info("No Letta sync config path set, skipping hook registration")
        return

    _config = LettaSyncConfig(config_path)
    _client = LettaSyncClient(_config.base_url)

    # Register hooks for each mapping
    for mapping in _config.mappings:
        ref_name = mapping.get("ref")
        if ref_name:
            register_hook(ref_name, push_to_letta)
            logger.info("Registered Letta sync hook for %s", ref_name)

    logger.info("Letta sync hooks registered (%d mappings)", len(_config.mappings))
