"""Model management system for Kairix server.

Manages available models in SQLite database and syncs selected model to Doppler config.
"""
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ModelInfo:
    """Information about an available model."""

    def __init__(self, model_id: str, provider: str, description: str, is_selected: bool = False):
        self.model_id = model_id
        self.provider = provider
        self.description = description
        self.is_selected = is_selected

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "description": self.description,
            "is_selected": self.is_selected
        }


class ModelManager:
    """Manages model configuration and persistence."""

    def __init__(self, db_path: str = ".kairix/models.db"):
        self.db_path = db_path
        self._ensure_db_exists()
        self._current_model: Optional[str] = None

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Ensure directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                description TEXT NOT NULL,
                is_selected INTEGER DEFAULT 0
            )
        """)

        # Check if table is empty and prepopulate with OpenAI models
        cursor.execute("SELECT COUNT(*) FROM models")
        count = cursor.fetchone()[0]

        if count == 0:
            logger.info("Prepopulating models database with OpenAI models")
            self._prepopulate_models(cursor)

        conn.commit()
        conn.close()

    def _prepopulate_models(self, cursor):
        """Prepopulate database with current OpenAI models."""
        openai_models = [
            ("gpt-4.1", "openai", "GPT-4.1 - Latest flagship model with improved reasoning"),
            ("gpt-4o", "openai", "GPT-4 Optimized - Faster, more efficient GPT-4"),
            ("gpt-4o-mini", "openai", "GPT-4 Optimized Mini - Lightweight, cost-effective"),
            ("gpt-4-turbo", "openai", "GPT-4 Turbo - High performance variant"),
            ("gpt-4", "openai", "GPT-4 - Original flagship model"),
            ("gpt-3.5-turbo", "openai", "GPT-3.5 Turbo - Fast and efficient"),
            ("o1", "openai", "O1 - Reasoning model for complex tasks"),
            ("o1-mini", "openai", "O1 Mini - Lightweight reasoning model"),
        ]

        # Get current model from environment or use default
        current_model = os.getenv("KAIRIX_AGENT_MODEL", "gpt-4.1")

        for model_id, provider, description in openai_models:
            is_selected = 1 if model_id == current_model else 0
            cursor.execute(
                "INSERT INTO models (model_id, provider, description, is_selected) VALUES (?, ?, ?, ?)",
                (model_id, provider, description, is_selected)
            )

    def get_all_models(self) -> List[ModelInfo]:
        """Get all available models."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT model_id, provider, description, is_selected FROM models ORDER BY provider, model_id")
        rows = cursor.fetchall()
        conn.close()

        return [ModelInfo(row[0], row[1], row[2], bool(row[3])) for row in rows]

    def get_selected_model(self) -> Optional[str]:
        """Get currently selected model."""
        if self._current_model:
            return self._current_model

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT model_id FROM models WHERE is_selected = 1 LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            self._current_model = row[0]
            return self._current_model

        # Default to gpt-4.1 if nothing selected
        return "gpt-4.1"

    def set_selected_model(self, model_id: str) -> bool:
        """Set selected model in database and update Doppler config."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Verify model exists
        cursor.execute("SELECT COUNT(*) FROM models WHERE model_id = ?", (model_id,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            logger.error(f"Model {model_id} not found in database")
            return False

        # Unselect all models
        cursor.execute("UPDATE models SET is_selected = 0")

        # Select the specified model
        cursor.execute("UPDATE models SET is_selected = 1 WHERE model_id = ?", (model_id,))

        conn.commit()
        conn.close()

        # Update Doppler config
        success = self._update_doppler_config(model_id)

        if success:
            self._current_model = model_id
            logger.info(f"Successfully updated model to {model_id}")

        return success

    def _update_doppler_config(self, model_id: str) -> bool:
        """Update KAIRIX_AGENT_MODEL in Doppler config."""
        try:
            # Get current Doppler project and config from environment
            project = os.getenv("DOPPLER_PROJECT", "kairix")
            config = os.getenv("DOPPLER_CONFIG", "mark")

            # Update the secret using Doppler CLI
            result = subprocess.run(
                ["doppler", "secrets", "set", "KAIRIX_AGENT_MODEL", model_id, "-p", project, "-c", config],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Successfully updated KAIRIX_AGENT_MODEL in Doppler to {model_id}")
                return True
            else:
                logger.error(f"Failed to update Doppler config: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Doppler CLI command timed out")
            return False
        except FileNotFoundError:
            logger.error("Doppler CLI not found - install with: brew install dopplerhq/cli/doppler")
            return False
        except Exception as e:
            logger.error(f"Error updating Doppler config: {e}")
            return False

    def reload_from_env(self):
        """Reload current model from environment variable."""
        model_id = os.getenv("KAIRIX_AGENT_MODEL")
        if model_id:
            self._current_model = model_id
            logger.info(f"Reloaded model from environment: {model_id}")
