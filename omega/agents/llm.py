"""
OpenCode LLM — ADK-compatible LLM connector for OpenCode Zen / custom providers.

Allows ADK agents to run on OmegaCLI models (DeepSeek, Mimo, Nemotron, etc.)
by implementing BaseLlm with an OpenAI-compatible API call.
"""

import json
import os
from typing import Any, AsyncGenerator

import requests

from google.adk.models import BaseLlm, LLMRegistry
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

DEFAULT_BASE_URL = os.environ.get("OMEGA_BASE_URL", "https://opencode.ai/zen/v1")
DEFAULT_API_KEY = os.environ.get("OMEGA_API_KEY", "")


class OpenCodeLlm(BaseLlm):
    """ADK LLM connector for OpenCode Zen API and OmegaCLI custom providers.

    Usage:
        LLMRegistry.register(OpenCodeLlm)
        agent = Agent(model="opencode/deepseek-v4-flash-free", ...)
    """

    model: str = "deepseek-v4-flash-free"
    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    temperature: float = 0.7
    max_tokens: int = 4096

    def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """Make an async chat completion call to the OpenCode-compatible API."""
        import asyncio

        async def _generate():
            messages = self._convert_messages(llm_request)
            model = llm_request.model or self.model

            payload = {
                "model": model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": stream,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=120,
                    stream=stream,
                )
                resp.raise_for_status()

                if stream:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield LlmResponse(
                                        content=content,
                                        finish_reason=data.get("choices", [{}])[0].get(
                                            "finish_reason"
                                        ),
                                    )
                            except json.JSONDecodeError:
                                continue
                else:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    yield LlmResponse(
                        content=content,
                        finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                    )

            except requests.exceptions.RequestException as e:
                yield LlmResponse(
                    content=f"Error: {e}",
                    finish_reason="error",
                )

        return _generate()

    def _convert_messages(self, llm_request: LlmRequest) -> list[dict[str, str]]:
        """Convert ADK's internal message format to OpenAI chat format."""
        messages = []
        # System prompt
        if llm_request.system_instruction:
            messages.append({
                "role": "system",
                "content": llm_request.system_instruction,
            })
        # Conversation history
        if llm_request.history:
            for msg in llm_request.history:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
                if content:
                    messages.append({"role": role, "content": str(content)})
        # Current user message
        if llm_request.contents:
            for c in llm_request.contents:
                role = getattr(c, "role", "user")
                content = getattr(c, "content", "")
                if content:
                    messages.append({"role": role, "content": str(content)})
        return messages


# Register with ADK so agents can use "opencode/<model>" syntax
LLMRegistry.register(OpenCodeLlm)
