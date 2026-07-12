"""Tests for cli.py — OMEGA CLI utility functions and theme system."""
from __future__ import annotations
import os, sys, unittest
from unittest.mock import patch

class TestCLIFormatting(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        import cli as _cli
        self.cli = _cli

    def test_format_size_bytes(self) -> None:
        r = self.cli.format_size(500)
        self.assertIn("500", r)

    def test_format_size_kb(self) -> None:
        r = self.cli.format_size(2048)
        self.assertIn("KB", r)

    def test_format_size_mb(self) -> None:
        r = self.cli.format_size(1048576)
        self.assertIn("MB", r)

    def test_format_size_gb(self) -> None:
        r = self.cli.format_size(1073741824)
        self.assertIn("GB", r)

    def test_format_size_zero(self) -> None:
        r = self.cli.format_size(0)
        self.assertIn("0", r)

    def test_safe_char_ascii(self) -> None:
        self.assertEqual(self.cli.safe_char("A", "_"), "A")

    def test_safe_char_newline(self) -> None:
        self.assertEqual(self.cli.safe_char("\n", "_"), "\n")

    def test_safe_char_tab(self) -> None:
        self.assertEqual(self.cli.safe_char("\t", "_"), "\t")

    def test_safe_char_unicode(self) -> None:
        self.assertEqual(self.cli.safe_char("é", "_"), "é")


class TestCLITheme(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        import cli as _cli
        self.cli = _cli

    def test_get_theme_names(self) -> None:
        themes = self.cli.get_theme_names()
        self.assertGreater(len(themes), 0)
        self.assertIn("default-dark", [t[0] for t in themes])

    def test_set_active_theme_valid(self) -> None:
        self.assertTrue(self.cli.set_active_theme("dracula"))
        self.assertEqual(self.cli.get_active_theme(), "dracula")

    def test_set_active_theme_invalid(self) -> None:
        self.assertFalse(self.cli.set_active_theme("nonexistent"))

    def test_get_active_theme_default(self) -> None:
        self.cli.set_active_theme("default-dark")
        self.assertEqual(self.cli.get_active_theme(), "default-dark")

    def test_get_theme_colors(self) -> None:
        self.cli.set_active_theme("default-dark")
        colors = self.cli.get_theme_colors()
        self.assertIsInstance(colors, dict)
        self.assertIn("accent_primary", colors)

    def test_switch_between_themes(self) -> None:
        self.cli.set_active_theme("dracula")
        c1 = self.cli.get_theme_colors()
        self.cli.set_active_theme("monokai")
        c2 = self.cli.get_theme_colors()
        self.assertNotEqual(c1.get("accent_primary"), c2.get("accent_primary"))


if __name__ == "__main__":
    unittest.main()
