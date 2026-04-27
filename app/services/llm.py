"""OpenAI-compatible Chat Completions API wrapper.

Single gateway for all LLM calls. Every skill imports only this module.
"""

import asyncio
import json
import os
from typing import AsyncIterator, Optional

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)


class LLMService:
    """Singleton LLM service. Configured from config.json on startup."""

    def __init__(self, config: dict):
        self.config = config
        self.client: Optional[AsyncOpenAI] = None
        self._init_client()

    def _init_client(self):
        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.openai.com/v1")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def update_config(self, config: dict):
        self.config = config
        self._init_client()

    @property
    def model(self) -> str:
        return self.config.get("model", "gpt-4o")

    @property
    def temperature(self) -> float:
        return self.config.get("temperature", 0.7)

    @property
    def max_tokens(self) -> int:
        return self.config.get("max_tokens", 4096)

    RETRYABLE_EXCEPTIONS = (
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        InternalServerError,
    )

    async def _retry_with_backoff(self, fn, max_retries: int = 3):
        """Execute fn with exponential backoff on transient errors.
        Does NOT retry BadRequestError or AuthenticationError.
        """
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                return await fn()
            except self.RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < max_retries:
                    delay = 2 ** (attempt - 1)
                    await asyncio.sleep(delay)
            except (BadRequestError, AuthenticationError):
                raise
        raise last_exception

    def is_configured(self) -> bool:
        return self.client is not None and bool(self.config.get("api_key"))

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        max_retries: int = 3,
    ):
        """Single-turn chat completion. Returns full text or async stream."""
        if not self.client:
            raise ValueError("LLM not configured. Please set API key and base URL.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        if stream:
            return self._chat_stream(messages, temperature, max_tokens, max_retries)

        async def _make_request():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            )
            return response.choices[0].message.content

        return await self._retry_with_backoff(_make_request, max_retries)

    async def _chat_stream(self, messages: list, temperature: Optional[float], max_tokens: Optional[int], max_retries: int = 3) -> AsyncIterator[str]:
        async def _create_stream():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                stream=True,
            )

        response = await self._retry_with_backoff(_create_stream, max_retries)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat_with_context(
        self,
        system_prompt: str,
        context_docs: list[dict],
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        max_retries: int = 3,
    ):
        """Assemble context into user message, then call chat()."""
        context_parts = ["参考以下已有资料：\n"]
        for doc in context_docs:
            context_parts.append(f"【{doc['title']}】")
            context_parts.append(doc["content"])
            context_parts.append("")

        context_parts.append("---")
        context_parts.append(f"用户指令：{user_message}")

        full_message = "\n".join(context_parts)
        return await self.chat(system_prompt, full_message, temperature, max_tokens, stream, max_retries)

    async def chat_with_context_and_json(
        self,
        system_prompt: str,
        context_docs: list[dict],
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Chat with context, expecting JSON-structured output.

        The system prompt should instruct the LLM to output markdown + a JSON block
        separated by ---JSON--- marker. The JSON portion is parsed and returned.
        Returns {"content": "...", "json": {...}} where json may be None.
        """
        full_response = await self.chat_with_context(
            system_prompt, context_docs, user_message, temperature, max_tokens
        )
        return self._parse_json_response(full_response)

    @staticmethod
    def _parse_json_response(response: str) -> dict:
        """Split response into markdown content and optional JSON block.

        Tries multiple extraction strategies in order:
        1. '---JSON---' marker (custom format)
        2. Last ```json ... ``` code fence block (common LLM format)
        3. Last ``` ... ``` code fence block
        4. Balanced { ... } JSON object at end of response (raw JSON, no fences)
        """
        result = {"content": response, "json": None}

        def _try_parse_json(json_str: str):
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                return None

        # Strategy 1: ---JSON--- marker
        if "---JSON---" in response:
            parts = response.split("---JSON---", 1)
            result["content"] = parts[0].strip()
            json_str = parts[1].strip()
            if json_str.startswith("```"):
                json_str = json_str.strip("`").strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
            parsed = _try_parse_json(json_str)
            if parsed:
                result["json"] = parsed
                return result

        # Strategy 2: Last ```json ... ``` block
        json_fences = response.split("```json")
        if len(json_fences) > 1:
            last_block = json_fences[-1]
            end = last_block.find("```")
            if end != -1:
                json_str = last_block[:end].strip()
                parsed = _try_parse_json(json_str)
                if parsed:
                    result["json"] = parsed
                    result["content"] = response[:response.rfind("```json")].strip()
                    return result

        # Strategy 3: Last ``` ... ``` block (try as JSON)
        fences = response.split("```")
        if len(fences) >= 3:
            for i in range(len(fences) - 2, 0, -2):
                candidate = fences[i].strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                parsed = _try_parse_json(candidate)
                if parsed:
                    result["json"] = parsed
                    result["content"] = response[:response.rfind("```" + fences[i][:min(len(fences[i]), 20)])].strip()
                    return result

        # Strategy 4: Find all balanced { ... } objects, pick the one with most keys.
        # Avoids nested objects being mistaken for the main JSON container.
        brace_positions = [i for i, ch in enumerate(response) if ch == '{']
        best_json = None
        best_keys = 0
        best_start = -1
        for brace_start in brace_positions:
            depth = 0
            in_string = False
            escape = False
            for pos in range(brace_start, len(response)):
                ch = response[pos]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = response[brace_start:pos + 1]
                        parsed = _try_parse_json(json_str)
                        if parsed and len(parsed) > best_keys:
                            best_json = parsed
                            best_keys = len(parsed)
                            best_start = brace_start
                        break
        if best_json:
            result["json"] = best_json
            result["content"] = response[:best_start].strip()
            return result

        return result


# Config file management
def load_config(config_path: str) -> dict:
    """Load LLM config from JSON file. Returns defaults if file missing."""
    defaults = {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
            defaults.update(saved)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults


def save_config(config_path: str, config: dict):
    """Save LLM config to JSON file, masking API key in logs."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
