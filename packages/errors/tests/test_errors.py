"""Tests for the Ω OMEGA Error Code Catalog."""

import json
import sys
import unittest
from pathlib import Path

# Add packages to path for direct test execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.errors import (
    AUTH_INVALID_CREDENTIALS,
    AUTH_REQUIRED,
    AUTH_SESSION_EXPIRED,
    AI_CONTEXT_TOO_LARGE,
    AI_PROVIDER_UNAVAILABLE,
    AI_STREAMING_INTERRUPTED,
    AI_TOOL_EXECUTION_FAILED,
    DEPLOY_ENV_MISCONFIGURED,
    DEPLOY_FAILED,
    DEPLOY_ROLLBACK_COMPLETED,
    REPO_NOT_FOUND,
    REPO_NOT_INDEXED,
    REPO_SYNC_FAILED,
    TASK_EXECUTION_CANCELLED,
    TASK_NOT_FOUND,
    TASK_VALIDATION_FAILED,
    ErrorCode,
    OmegaException,
    format_error,
    list_codes,
    lookup,
)


class TestErrorCatalog(unittest.TestCase):
    """Test the error code definitions and catalog."""

    def test_all_codes_defined(self):
        """All 16 spec codes exist."""
        codes = list_codes()
        self.assertEqual(len(codes), 16)

    def test_code_structure(self):
        """Each code has required fields."""
        for code in list_codes():
            self.assertIsInstance(code, ErrorCode)
            self.assertRegex(code.code, r"^[A-Z]+_\d{3}$")
            self.assertTrue(len(code.message) > 0)
            self.assertTrue(len(code.suggestion) > 0)
            self.assertIn(code.http_status, {200, 400, 401, 404, 413, 422, 500, 502, 503})

    def test_code_uniqueness(self):
        """No duplicate code strings."""
        code_strings = [e.code for e in list_codes()]
        self.assertEqual(len(code_strings), len(set(code_strings)))

    def test_lookup_by_code(self):
        """lookup() returns the right code."""
        err = lookup("AUTH_001")
        self.assertIsNotNone(err)
        self.assertEqual(err, AUTH_INVALID_CREDENTIALS)

        err = lookup("REPO_002")
        self.assertIsNotNone(err)
        self.assertEqual(err, REPO_NOT_INDEXED)

    def test_lookup_missing(self):
        """lookup() returns None for unknown codes."""
        self.assertIsNone(lookup("NONEXISTENT_001"))

    def test_list_codes_by_category(self):
        """list_codes(category) filters correctly."""
        auth_codes = list_codes("AUTH")
        self.assertEqual(len(auth_codes), 3)
        for code in auth_codes:
            self.assertTrue(code.code.startswith("AUTH_"))

        ai_codes = list_codes("AI")
        self.assertEqual(len(ai_codes), 4)

        task_codes = list_codes("TASK")
        self.assertEqual(len(task_codes), 3)

    def test_auth_codes(self):
        """Authentication error codes."""
        self.assertEqual(AUTH_INVALID_CREDENTIALS.code, "AUTH_001")
        self.assertEqual(AUTH_INVALID_CREDENTIALS.http_status, 401)
        self.assertEqual(AUTH_SESSION_EXPIRED.code, "AUTH_002")
        self.assertEqual(AUTH_REQUIRED.code, "AUTH_003")

    def test_repo_codes(self):
        """Repository error codes."""
        self.assertEqual(REPO_NOT_FOUND.code, "REPO_001")
        self.assertEqual(REPO_NOT_INDEXED.code, "REPO_002")
        self.assertEqual(REPO_SYNC_FAILED.code, "REPO_003")

    def test_ai_codes(self):
        """AI Runtime error codes."""
        self.assertEqual(AI_PROVIDER_UNAVAILABLE.code, "AI_001")
        self.assertEqual(AI_PROVIDER_UNAVAILABLE.http_status, 503)
        self.assertEqual(AI_CONTEXT_TOO_LARGE.code, "AI_002")
        self.assertEqual(AI_CONTEXT_TOO_LARGE.http_status, 413)
        self.assertEqual(AI_TOOL_EXECUTION_FAILED.code, "AI_003")
        self.assertEqual(AI_STREAMING_INTERRUPTED.code, "AI_004")

    def test_task_codes(self):
        """Task error codes."""
        self.assertEqual(TASK_NOT_FOUND.code, "TASK_001")
        self.assertEqual(TASK_EXECUTION_CANCELLED.code, "TASK_002")
        self.assertEqual(TASK_VALIDATION_FAILED.code, "TASK_003")
        self.assertEqual(TASK_VALIDATION_FAILED.http_status, 422)

    def test_deploy_codes(self):
        """Deployment error codes."""
        self.assertEqual(DEPLOY_FAILED.code, "DEPLOY_001")
        self.assertEqual(DEPLOY_ROLLBACK_COMPLETED.code, "DEPLOY_002")
        self.assertEqual(DEPLOY_ROLLBACK_COMPLETED.http_status, 200)
        self.assertEqual(DEPLOY_ENV_MISCONFIGURED.code, "DEPLOY_003")


class TestOmegaException(unittest.TestCase):
    """Test the OmegaException class."""

    def test_basic_exception(self):
        """OmegaException stores code and formats message."""
        exc = OmegaException(AUTH_REQUIRED)
        self.assertEqual(exc.code, AUTH_REQUIRED)
        self.assertIn("[AUTH_003]", str(exc))
        self.assertIn("Authentication Required", str(exc))
        self.assertEqual(exc.http_status(), 401)

    def test_exception_with_details(self):
        """OmegaException includes optional details."""
        exc = OmegaException(REPO_NOT_FOUND, details="repo 'foo' not in index")
        self.assertIn("repo 'foo'", str(exc))

    def test_exception_with_request_id(self):
        """OmegaException includes request_id."""
        exc = OmegaException(AI_PROVIDER_UNAVAILABLE, request_id="req-xyz")
        self.assertIn("req-xyz", str(exc))

    def test_to_dict(self):
        """OmegaException serializes to dict."""
        exc = OmegaException(
            AUTH_SESSION_EXPIRED,
            details="token expired 5min ago",
            request_id="req-123",
        )
        d = exc.to_dict()
        self.assertIn("error", d)
        self.assertEqual(d["error"]["code"], "AUTH_002")
        self.assertEqual(d["error"]["details"], "token expired 5min ago")
        self.assertEqual(d["error"]["request_id"], "req-123")

    def test_to_dict_json_serializable(self):
        """to_dict output is JSON-serializable."""
        exc = OmegaException(AI_CONTEXT_TOO_LARGE)
        json.dumps(exc.to_dict())  # should not raise


class TestFormatError(unittest.TestCase):
    """Test the format_error utility."""

    def test_format_basic(self):
        result = format_error(REPO_NOT_FOUND)
        self.assertIn("[REPO_001]", result)
        self.assertIn("Repository Not Found", result)

    def test_format_with_request_id(self):
        result = format_error(REPO_NOT_FOUND, request_id="req-abc")
        self.assertIn("req-abc", result)

    def test_format_with_details(self):
        result = format_error(REPO_NOT_FOUND, details="path /x not found")
        self.assertIn("path /x", result)


if __name__ == "__main__":
    unittest.main()
