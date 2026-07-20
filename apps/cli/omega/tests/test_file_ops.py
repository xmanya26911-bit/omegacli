"""Unit tests for file operations module."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from omega.tools.file_ops import (
    read_file,
    write_file,
    edit_file,
    hash_file,
    format_size,
)


class TestReadFile(unittest.TestCase):
    """File reading with pagination and error handling."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        self.tmp.write("line1\nline2\nline3\nline4\nline5\n")
        self.tmp.close()

    def tearDown(self) -> None:
        os.unlink(self.tmp.name)

    def test_read_full_file(self) -> None:
        result = read_file(self.tmp.name)
        self.assertFalse(result.is_error)
        self.assertIn("line1", result.content)
        self.assertIn("line5", result.content)

    def test_read_with_offset(self) -> None:
        result = read_file(self.tmp.name, offset=3)
        self.assertFalse(result.is_error)
        self.assertIn("line3", result.content)
        self.assertNotIn("line1", result.content)
        self.assertNotIn("line2", result.content)

    def test_read_with_limit(self) -> None:
        result = read_file(self.tmp.name, limit=2)
        self.assertFalse(result.is_error)
        self.assertIn("line1", result.content)
        self.assertIn("line2", result.content)
        self.assertNotIn("line3", result.content)

    def test_read_nonexistent_file(self) -> None:
        result = read_file("/nonexistent/path/file.txt")
        self.assertTrue(result.is_error)
        self.assertIn("not found", result.content.lower())

    def test_read_empty_file(self) -> None:
        empty = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        empty.write("")
        empty.close()
        result = read_file(empty.name)
        self.assertFalse(result.is_error)
        os.unlink(empty.name)


class TestWriteFile(unittest.TestCase):
    """File writing, overwrites, and error handling."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        self.tmp.write("original\n")
        self.tmp.close()

    def tearDown(self) -> None:
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_write_new_file(self) -> None:
        path = self.tmp.name + ".new"
        result = write_file(path, "hello")
        self.assertFalse(result.is_error)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertEqual(f.read(), "hello")
        os.unlink(path)

    def test_write_overwrite(self) -> None:
        result = write_file(self.tmp.name, "replaced")
        self.assertFalse(result.is_error)
        with open(self.tmp.name) as f:
            self.assertEqual(f.read(), "replaced")

    def test_write_creates_dirs(self) -> None:
        path = os.path.join(tempfile.mkdtemp(), "subdir", "test.txt")
        result = write_file(path, "nested")
        self.assertFalse(result.is_error)
        self.assertTrue(os.path.exists(path))
        os.unlink(path)
        os.rmdir(os.path.dirname(path))


class TestEditFile(unittest.TestCase):
    """Find-and-replace editing."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        self.tmp.write("hello world\nfoo bar\n")
        self.tmp.close()

    def tearDown(self) -> None:
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_edit_replacement(self) -> None:
        result = edit_file(self.tmp.name, "hello world", "HELLO WORLD")
        self.assertFalse(result.is_error)
        with open(self.tmp.name) as f:
            content = f.read()
        self.assertIn("HELLO WORLD", content)
        self.assertIn("foo bar", content)

    def test_edit_string_not_found(self) -> None:
        result = edit_file(self.tmp.name, "nonexistent string 12345", "replacement")
        self.assertTrue(result.is_error)

    def test_edit_file_not_found(self) -> None:
        result = edit_file("/nonexistent/path.txt", "a", "b")
        self.assertTrue(result.is_error)

    def test_edit_empty_new_string(self) -> None:
        """Replacing with empty string should delete the text."""
        result = edit_file(self.tmp.name, "hello world", "")
        self.assertFalse(result.is_error)
        with open(self.tmp.name) as f:
            content = f.read()
        self.assertNotIn("hello world", content)


class TestHashFile(unittest.TestCase):
    """File hashing."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        self.tmp.write("test data for hashing")
        self.tmp.close()

    def tearDown(self) -> None:
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_sha256_hash(self) -> None:
        result = hash_file(self.tmp.name, "sha256")
        self.assertFalse(result.is_error)
        self.assertIn("SHA256", result.content)
        # SHA-256 produces 64 hex chars
        hex_part = result.content.split("= ")[-1]
        self.assertEqual(len(hex_part.strip()), 64)

    def test_md5_hash(self) -> None:
        result = hash_file(self.tmp.name, "md5")
        self.assertFalse(result.is_error)
        self.assertIn("MD5", result.content)
        hex_part = result.content.split("= ")[-1]
        self.assertEqual(len(hex_part.strip()), 32)

    def test_hash_nonexistent(self) -> None:
        result = hash_file("/nonexistent/file.bin")
        self.assertTrue(result.is_error)

    def test_unknown_algorithm(self) -> None:
        result = hash_file(self.tmp.name, "fake-algo")
        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
