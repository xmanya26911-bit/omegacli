"""Tests for the Ω OMEGA Keyboard Shortcut System (§395)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.shortcuts import (
    Shortcut,
    ShortcutCategory,
    all_shortcuts,
    shortcuts_by_category,
    shortcuts_by_scope,
    find_shortcut,
    format_shortcuts_table,
    GLOBAL_COMMAND_PALETTE,
    GLOBAL_NEW_CONVERSATION,
    CHAT_SEND,
    REPO_OPEN_FILE,
    ENGINEER_RUN,
)


class TestShortcutDefinitions(unittest.TestCase):
    """Test the shortcut data definitions."""

    def test_all_shortcuts_count(self):
        """19 shortcuts across 4 categories."""
        self.assertEqual(len(all_shortcuts()), 19)

    def test_shortcut_structure(self):
        """Each shortcut has required fields."""
        for s in all_shortcuts():
            self.assertIsInstance(s, Shortcut)
            self.assertTrue(len(s.id) > 0)
            self.assertTrue(len(s.keys) > 0)
            self.assertTrue(len(s.mac_keys) > 0)
            self.assertTrue(len(s.action) > 0)
            self.assertIsInstance(s.category, ShortcutCategory)
            self.assertTrue(len(s.description) > 0)

    def test_unique_ids(self):
        """No duplicate shortcut IDs."""
        ids = [s.id for s in all_shortcuts()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_categories(self):
        """4 shortcut categories."""
        cats = {s.category for s in all_shortcuts()}
        self.assertEqual(cats, {
            ShortcutCategory.GLOBAL,
            ShortcutCategory.CHAT,
            ShortcutCategory.REPOSITORY,
            ShortcutCategory.ENGINEER,
        })

    def test_category_counts(self):
        """Correct number per category."""
        self.assertEqual(len(shortcuts_by_category(ShortcutCategory.GLOBAL)), 7)
        self.assertEqual(len(shortcuts_by_category(ShortcutCategory.CHAT)), 5)
        self.assertEqual(len(shortcuts_by_category(ShortcutCategory.REPOSITORY)), 4)
        self.assertEqual(len(shortcuts_by_category(ShortcutCategory.ENGINEER)), 3)

    def test_scope_filtering(self):
        """Scope filtering works."""
        chat_scoped = shortcuts_by_scope("chat_input")
        self.assertTrue(len(chat_scoped) > 0)
        for s in chat_scoped:
            self.assertEqual(s.scope, "chat_input")

    def test_find_shortcut(self):
        """find_shortcut by ID."""
        s = find_shortcut("global.command_palette")
        self.assertIsNotNone(s)
        self.assertEqual(s, GLOBAL_COMMAND_PALETTE)
        self.assertIsNone(find_shortcut("nonexistent"))

    def test_specific_shortcuts(self):
        """Verify specific shortcut values."""
        self.assertEqual(GLOBAL_COMMAND_PALETTE.keys, "Ctrl+K")
        self.assertEqual(GLOBAL_NEW_CONVERSATION.keys, "Ctrl+N")
        self.assertEqual(CHAT_SEND.keys, "Enter")
        self.assertEqual(REPO_OPEN_FILE.keys, "Ctrl+P")
        self.assertEqual(ENGINEER_RUN.keys, "Ctrl+R")

    def test_mac_keys(self):
        """Mac equivalents exist."""
        for s in all_shortcuts():
            self.assertTrue(len(s.mac_keys) > 0)
            if "Ctrl" in s.keys:
                self.assertIn("Cmd", s.mac_keys)

    def test_format_table(self):
        """Format returns markdown table."""
        table = format_shortcuts_table(ShortcutCategory.GLOBAL)
        self.assertIn("Ctrl+K", table)
        self.assertIn("Ctrl+N", table)
        self.assertIn("| Shortcut | Action |", table)

    def test_format_all(self):
        """Format all returns all categories."""
        table = format_shortcuts_table()
        self.assertIn("Ctrl+K", table)
        self.assertIn("Ctrl+R", table)
        self.assertIn("Ctrl+P", table)
        self.assertIn("Enter", table)


if __name__ == "__main__":
    unittest.main()
