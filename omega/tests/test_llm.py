"""Tests for llm.py — LLMClient with mocked HTTP responses."""
from __future__ import annotations
import json, os, sys, unittest
from unittest.mock import MagicMock, patch


class TestLLMClient(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from config import Config
        self.config = MagicMock(spec=Config)
        self.config.api_key = "test-key"
        self.config.base_url = "https://api.test.com/v1"
        self.config.model = "test-model"
        from llm import LLMClient
        self.LLMClient = LLMClient
        self.client = LLMClient(self.config)

    def test_init(self) -> None:
        self.assertEqual(self.client.config, self.config)
        self.assertIsNotNone(self.client.session)
        self.assertEqual(self.client.total_prompt_tokens, 0)

    def test_token_stats_zero(self) -> None:
        stats = self.client.get_token_stats()
        self.assertEqual(stats["total_tokens"], 0)

    @patch('requests.Session.post')
    def test_non_streaming_success(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_post.return_value = mock_resp
        self.client.session.post = mock_post
        result = self.client.chat([{"role": "user", "content": "Hi"}], stream=False)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["content"], "Hello!")

    @patch('requests.Session.post')
    def test_auth_error(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp
        self.client.session.post = mock_post
        from llm import LLMAuthError
        with self.assertRaises(LLMAuthError):
            self.client.chat([{"role": "user", "content": "Hi"}], stream=False)

    @patch('requests.Session.post')
    def test_rate_limit_retry(self, mock_post: MagicMock) -> None:
        rl = MagicMock(); rl.status_code = 429; rl.headers = {"Retry-After": "1"}
        ok = MagicMock()
        ok.status_code = 200
        ok.json.return_value = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}
        }
        mock_post.side_effect = [rl, ok]
        self.client.session.post = mock_post
        result = self.client.chat([{"role": "user", "content": "Hi"}], stream=False)
        self.assertEqual(result["content"], "OK")

    def test_count_tokens_fallback(self) -> None:
        count = self.client.count_tokens([{"role": "user", "content": "test"}])
        self.assertGreater(count, 0)

    def test_token_stats_after_call(self) -> None:
        stats = self.client.get_token_stats()
        self.assertIn("prompt_tokens", stats)


class TestLLMExceptions(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from llm import LLMError, LLMRetryError, LLMAuthError, LLMRateLimitError
        self.LLMError = LLMError
        self.LLMRetryError = LLMRetryError
        self.LLMAuthError = LLMAuthError
        self.LLMRateLimitError = LLMRateLimitError

    def test_hierarchy(self) -> None:
        self.assertTrue(issubclass(self.LLMRetryError, self.LLMError))
        self.assertTrue(issubclass(self.LLMAuthError, self.LLMError))
        self.assertTrue(issubclass(self.LLMRateLimitError, self.LLMError))

    def test_messages(self) -> None:
        self.assertIn("error", str(self.LLMError("an error occurred")))
        self.assertIn("retries", str(self.LLMRetryError("Max retries")).lower())


if __name__ == "__main__":
    unittest.main()
