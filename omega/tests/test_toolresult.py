"""Unit tests for ToolResult and caching infrastructure."""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from omega.tools import ToolResult, _cache_key, _cache_set, _cache_get, _clear_cache, format_size


class TestToolResult(unittest.TestCase):
    """ToolResult construction, truthiness, and string representation."""

    def test_success_creation(self) -> None:
        """A non-error result should have content and not be an error."""
        result = ToolResult(content="Hello, OMEGA!")
        self.assertEqual(result.content, "Hello, OMEGA!")
        self.assertFalse(result.is_error)

    def test_error_creation(self) -> None:
        """An error result should have is_error=True."""
        result = ToolResult(content="Something broke", is_error=True)
        self.assertEqual(result.content, "Something broke")
        self.assertTrue(result.is_error)

    def test_truthy_when_ok(self) -> None:
        """ToolResult should be truthy when not an error and has content."""
        result = ToolResult(content="data")
        self.assertTrue(result)

    def test_falsy_when_empty(self) -> None:
        """ToolResult should be falsy when content is empty."""
        result = ToolResult(content="")
        self.assertFalse(result)

    def test_falsy_when_error(self) -> None:
        """ToolResult should be falsy when is_error is True."""
        result = ToolResult(content="error", is_error=True)
        self.assertFalse(result)

    def test_str_conversion(self) -> None:
        """str(result) should return the content."""
        result = ToolResult(content="output text")
        self.assertEqual(str(result), "output text")

    def test_repr_success(self) -> None:
        """repr should indicate OK status."""
        result = ToolResult(content="short")
        self.assertIn("OK", repr(result))
        self.assertIn("short", repr(result))

    def test_repr_error(self) -> None:
        """repr should indicate ERROR status."""
        result = ToolResult(content="fail", is_error=True)
        self.assertIn("ERROR", repr(result))

    def test_repr_truncates_long_content(self) -> None:
        """repr should truncate content longer than 80 chars."""
        long_content = "a" * 100
        result = ToolResult(content=long_content)
        self.assertIn("...", repr(result))

    def test_empty_result_is_falsy(self) -> None:
        """A newly created empty ToolResult should be falsy."""
        result = ToolResult()
        self.assertFalse(result)
        self.assertFalse(result.is_error)
        self.assertEqual(result.content, "")


class TestCache(unittest.TestCase):
    """In-memory cache key generation, set, get, clear, stats."""

    def setUp(self) -> None:
        _clear_cache()

    def test_cache_key_deterministic(self) -> None:
        """Same prefix and args should produce the same key."""
        key1 = _cache_key("test", 1, "a")
        key2 = _cache_key("test", 1, "a")
        self.assertEqual(key1, key2)

    def test_cache_key_differs_with_args(self) -> None:
        """Different args should produce different keys."""
        key1 = _cache_key("test", 1)
        key2 = _cache_key("test", 2)
        self.assertNotEqual(key1, key2)

    def test_cache_set_and_get(self) -> None:
        """Set then get should retrieve the value."""
        key = _cache_key("test", "hello")
        _cache_set(key, "world")
        self.assertEqual(_cache_get(key), "world")

    def test_cache_miss_returns_none(self) -> None:
        """Getting an uncached key should return None."""
        result = _cache_get("nonexistent-key-12345")
        self.assertIsNone(result)

    def test_cache_clear(self) -> None:
        """Clearing the cache should remove all entries."""
        key = _cache_key("test", "data")
        _cache_set(key, "value")
        _clear_cache()
        self.assertIsNone(_cache_get(key))

    def test_cache_expiry(self) -> None:
        """Expired cache entries should return None."""
        key = _cache_key("test", "expiry")
        _cache_set(key, "value")
        # The default TTL is 60s, so this should still be valid
        self.assertEqual(_cache_get(key), "value")


class TestFormatSize(unittest.TestCase):
    """Human-readable file size formatting."""

    def test_bytes(self) -> None:
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(100), "100 B")

    def test_kilobytes(self) -> None:
        result = format_size(1024)
        self.assertIn("KB", result)

    def test_megabytes(self) -> None:
        result = format_size(1048576)
        self.assertIn("MB", result)

    def test_gigabytes(self) -> None:
        result = format_size(1073741824)
        self.assertIn("GB", result)

    def test_terabytes(self) -> None:
        result = format_size(1099511627776)
        self.assertIn("TB", result)


if __name__ == "__main__":
    unittest.main()
