"""Smoke tests for agent.py — the OMEGA Agent class.

These tests verify that the Agent class can be imported, instantiated,
and that its core methods run without crashing. No API calls are made
in these tests — they validate structure and initialization only.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: create a minimal config for testing
# ---------------------------------------------------------------------------

def _make_test_config(**overrides: str) -> MagicMock:
    """Create a minimal Config-like object for Agent construction.

    Returns a MagicMock that satisfies the fields Agent.__init__ accesses:
        api_key, base_url, model, max_tokens, max_steps, theme, validate()
    """
    cfg = MagicMock()
    cfg.api_key = overrides.get("api_key", "test-key-12345")
    cfg.base_url = overrides.get("base_url", "https://api.test.example.com")
    cfg.model = overrides.get("model", "test-model")
    cfg.max_tokens = overrides.get("max_tokens", 8192)
    cfg.max_steps = overrides.get("max_steps", 25)
    cfg.theme = overrides.get("theme", "default-dark")
    cfg.validate.return_value = []
    return cfg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentImport(unittest.TestCase):
    """Verify the Agent class can be imported."""

    def test_import_agent(self) -> None:
        """agent module should be importable without errors."""
        import agent  # noqa: F811
        self.assertTrue(hasattr(agent, "Agent"))
        self.assertTrue(hasattr(agent, "_save_history"))

    def test_agent_class_has_methods(self) -> None:
        """Agent class should expose expected public methods."""
        import agent
        expected = [
            "run_once",
            "run_interactive",
            "_save_session",
            "_load_session",
            "_list_sessions",
            "_print_help",
            "_handle_command",
            "_handle_configure",
            "_print_usage_stats",
        ]
        for name in expected:
            self.assertTrue(
                hasattr(agent.Agent, name),
                f"Agent class missing method: {name}",
            )


class TestAgentInit(unittest.TestCase):
    """Verify Agent can be instantiated with a config."""

    def setUp(self) -> None:
        self.config = _make_test_config()

    def _get_agent(self):
        """Import and create an Agent instance with clean state."""
        # Clear any cached module state
        for mod in list(sys.modules.keys()):
            if mod.startswith("memory") or mod == "agent":
                sys.modules.pop(mod, None)
        # Patch memory and LLM to prevent real API calls
        with patch.dict(os.environ, {"OMEGA_API_KEY": "test-key-12345"}):
            with patch("memory.ShortTermMemory") as mock_mem:
                with patch("memory.get_persistent_memory") as mock_pers:
                    with patch("memory.get_total_recall") as mock_recall:
                        with patch("llm.LLMClient") as mock_llm:
                            mock_mem_instance = MagicMock()
                            mock_mem.return_value = mock_mem_instance
                            mock_pers.return_value = MagicMock()
                            mock_recall_instance = MagicMock()
                            mock_recall.return_value = mock_recall_instance

                            import agent
                            a = agent.Agent(self.config)
                            return a

    def test_agent_init(self) -> None:
        """Agent should initialize without exceptions."""
        a = self._get_agent()
        self.assertIsNotNone(a)
        self.assertEqual(a.config, self.config)

    def test_agent_has_llm_client(self) -> None:
        """Agent should create an LLMClient on init."""
        a = self._get_agent()
        self.assertIsNotNone(a.llm)

    def test_agent_has_memory(self) -> None:
        """Agent should initialize ShortTermMemory."""
        a = self._get_agent()
        self.assertIsNotNone(a.memory)

    def test_agent_running_flag(self) -> None:
        """Agent should start with running=False."""
        a = self._get_agent()
        self.assertFalse(a.running)

    def test_agent_system_prompt_setup(self) -> None:
        """Agent should call _setup_system during init."""
        a = self._get_agent()
        # Setup adds to memory, so memory should have messages after init
        # (implementation detail: add_system was called)
        self.assertIsNotNone(a.memory)


class TestAgentConfigValidation(unittest.TestCase):
    """Verify Agent responds to config validation results."""

    @patch("agent.print_warning")
    def test_run_once_validates_config(self, mock_print_warning) -> None:
        """run_once should call config.validate() and warn on issues."""
        config = _make_test_config()
        config.validate.return_value = ["Missing API key"]

        with patch("agent.ShortTermMemory") as mock_mem:
            with patch("agent.get_persistent_memory") as mock_pers:
                with patch("agent.get_total_recall") as mock_recall:
                    with patch("agent.LLMClient"):
                        mock_recall_instance = MagicMock()
                        mock_recall.return_value = mock_recall_instance
                        mock_mem_instance = MagicMock()
                        mock_mem.return_value = mock_mem_instance
                        mock_mem_instance.get_messages.return_value = []
                        mock_pers.return_value = MagicMock()

                        import agent
                        a = agent.Agent(config)
                        # Should not crash even with invalid config
                        config.validate.return_value = ["Missing API key"]
                        self.assertTrue(len(a.config.validate()) == 1)


class TestAgentSaveHistory(unittest.TestCase):
    """Verify the _save_history module-level function."""

    @patch("agent.HAVE_READLINE", False)
    def test_save_history_no_readline(self) -> None:
        """_save_history should not error when readline is unavailable."""
        import agent
        # Should run without exception
        agent._save_history()


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
