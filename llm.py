#!/usr/bin/env python3
"""OMEGA LLM Client — Resilient API client with retry, token tracking, and streaming."""

import json
import time
import random
import requests
from datetime import datetime


class LLMError(Exception):
    """Base LLM exception."""
    pass


class LLMRetryError(LLMError):
    """Max retries exceeded."""
    pass


class LLMAuthError(LLMError):
    """Authentication/authorization error."""
    pass


class LLMRateLimitError(LLMError):
    """Rate limited by API."""
    pass


class LLMClient:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        })
        # Token tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_estimate = 0.0
        self._last_request_time = 0.0

    def _rate_limit_wait(self):
        """Ensure minimum delay between requests to avoid rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        min_delay = 0.5  # 500ms between requests
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        self._last_request_time = time.time()

    def chat(self, messages, tools=None, stream=True, max_retries=3):
        """Send chat completion request with retry logic."""
        url = f"{self.config.base_url}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": 16384,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
        }
        if tools:
            payload["tools"] = tools

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                self._rate_limit_wait()

                response = self.session.post(
                    url, json=payload, stream=stream, timeout=120
                )

                # Handle error responses
                if response.status_code == 401:
                    raise LLMAuthError(
                        "Authentication failed. Check your API key. "
                        "Set OMEGA_API_KEY environment variable or configure via /configure."
                    )
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    raise LLMRateLimitError(
                        f"Rate limited. Retry after {retry_after}s"
                    )
                elif response.status_code == 503:
                    raise LLMError("API temporarily unavailable (503)")
                elif response.status_code != 200:
                    try:
                        err = response.json()
                        err_msg = err.get("error", {}).get("message", str(err))
                    except Exception:
                        err_msg = response.text[:500]
                    raise LLMError(f"API error {response.status_code}: {err_msg}")

                # Track tokens from response headers if available
                if "x-ratelimit-remaining" in response.headers:
                    pass  # Could log rate limit info

                if stream:
                    return self._handle_stream(response)
                else:
                    return self._handle_response(response)

            except (LLMAuthError, LLMRetryError) as e:
                raise  # Don't retry auth errors
            except LLMRateLimitError as e:
                last_error = e
                if attempt < max_retries:
                    delay = 2 ** attempt + random.uniform(0, 2)
                    time.sleep(delay)
                    continue
            except requests.Timeout:
                last_error = LLMError(f"Request timed out (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
            except requests.ConnectionError as e:
                last_error = LLMError(f"Connection error: {e}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
            except Exception as e:
                last_error = LLMError(f"Unexpected error: {e}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue

        raise LLMRetryError(f"Failed after {max_retries} retries. Last error: {last_error}")

    def _handle_response(self, response):
        """Handle non-streaming response."""
        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]

        # Track token usage
        if "usage" in data:
            self.total_prompt_tokens += data["usage"].get("prompt_tokens", 0)
            self.total_completion_tokens += data["usage"].get("completion_tokens", 0)

        content = message.get("content", "")
        tool_calls = message.get("tool_calls")

        return {
            "content": content or "",
            "tool_calls": (
                [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]
                if tool_calls
                else None
            ),
            "finish_reason": choice.get("finish_reason", "stop"),
        }

    def _handle_stream(self, response):
        """Handle streaming response, yielding events."""
        collected_content = ""
        tool_calls = {}
        prompt_tokens = 0
        completion_tokens = 0

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="replace")
            if not line.startswith("data: "):
                continue

            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break

            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if "choices" not in data or not data["choices"]:
                continue

            # Track usage if present
            usage = data.get("usage")
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

            delta = data["choices"][0].get("delta", {})

            if "content" in delta and delta["content"]:
                collected_content += delta["content"]
                yield ("content", delta["content"])

            if "tool_calls" in delta:
                for tc_delta in delta["tool_calls"]:
                    idx = tc_delta.get("index", 0)
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tc_delta.get("id", ""),
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if "id" in tc_delta and tc_delta["id"]:
                        tool_calls[idx]["id"] = tc_delta["id"]
                    if "function" in tc_delta:
                        fn = tc_delta["function"]
                        if "name" in fn and fn["name"]:
                            tool_calls[idx]["function"]["name"] = fn["name"]
                        if "arguments" in fn and fn["arguments"]:
                            tool_calls[idx]["function"]["arguments"] += fn["arguments"]

        # Track tokens
        if prompt_tokens or completion_tokens:
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens

        if tool_calls:
            yield ("tool_calls", list(tool_calls.values()))
        else:
            yield ("done", collected_content)

    def count_tokens(self, messages):
        """Estimate token count for messages."""
        try:
            url = f"{self.config.base_url}/chat/completions"
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": 1,
                "stream": False,
            }
            response = self.session.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "usage" in data:
                    return data["usage"].get("prompt_tokens", 0)
        except Exception:
            pass
        return sum(len(str(m)) // 4 for m in messages)

    def get_token_stats(self):
        """Get token usage statistics."""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }
