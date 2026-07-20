"""OpenCode LLM — ADK-compatible LLM connector for OpenCode Zen / custom providers.

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
from google.genai import types

DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_API_KEY = ""


class OpenCodeLlm(BaseLlm):
    """ADK LLM connector for OpenCode Zen API and OmegaCLI custom providers.

    Usage:
        LLMRegistry.register(OpenCodeLlm)
        agent = Agent(model="deepseek-v4-flash-free", ...)
    """

    model: str = "deepseek-v4-flash-free"
    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def supported_models(cls) -> list[str]:
        """Register this LLM for all OpenCode/Omega models."""
        return [
            "deepseek-v4-flash-free",
            "mimo-v2.5-free",
            "hy3-free",
            "nemotron-3-ultra-free",
            "north-mini-code-free",
            "deepseek-v4-flash",
            "mimo-v2.5",
            "hy3",
            "nemotron-3-ultra",
            "north-mini-code",
        ]

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
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

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
                                        content=types.Content(
                                            parts=[types.Part(text=content)]
                                        ),
                                        partial=True,
                                        turn_complete=False,
                                    )
                            except json.JSONDecodeError:
                                continue
                    # Signal turn complete at end of stream
                    yield LlmResponse(
                        content=types.Content(
                            parts=[types.Part(text="")]
                        ),
                        partial=False,
                        turn_complete=True,
                    )
                else:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    yield LlmResponse(
                        content=types.Content(
                            parts=[types.Part(text=content)]
                        ),
                        finish_reason="stop",
                    )

            except requests.exceptions.RequestException as e:
                yield LlmResponse(
                    content=types.Content(
                        parts=[types.Part(text=f"Error: {e}")]
                    ),
                    error_message=str(e),
                    error_code="API_ERROR",
                )

        return _generate()

    def _convert_messages(self, llm_request: LlmRequest) -> list[dict[str, str]]:
        """Convert ADK's internal message format to OpenAI chat format."""
        messages = []
        # System prompt — from config.system_instruction
        try:
            if llm_request.config and llm_request.config.system_instruction:
                si = llm_request.config.system_instruction
                if hasattr(si, "parts") and si.parts:
                    for part in si.parts:
                        if hasattr(part, "text") and part.text:
                            messages.append({
                                "role": "system",
                                "content": part.text,
                            })
                elif hasattr(si, "text") and si.text:
                    messages.append({
                        "role": "system",
                        "content": si.text,
                    })
        except Exception:
            pass  # System instruction is optional
        # Current user message from contents
        if llm_request.contents:
            for c in llm_request.contents:
                role = getattr(c, "role", "user")
                for part in getattr(c, "parts", []) or []:
                    if hasattr(part, "text") and part.text:
                        messages.append({"role": role, "content": str(part.text)})
                    elif hasattr(part, "function_call") and part.function_call:
                        messages.append({
                            "role": "assistant",
                            "content": json.dumps({
                                "function_call": {
                                    "name": part.function_call.name,
                                    "arguments": str(part.function_call.args),
                                }
                            }),
                        })
        return messages


# Register with ADK so agents can use "opencode/<model>" syntax
LLMRegistry.register(OpenCodeLlm)
