"""AI provider abstraction and NVIDIA NIM implementation.

The ``AIProvider`` base class defines the contract all providers must satisfy.
``NVIDIAProvider`` implements the NVIDIA NIM chat completions API with retries,
timeouts, and structured logging.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_workflow.config import Config

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised when an AI provider call ultimately fails."""


class AIProvider(ABC):
    """Abstract interface for chat completion providers."""

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat request and return the assistant's reply text.

        Args:
            system_prompt: System-level instructions for the model.
            user_prompt: The user message content.
            model: Override the configured model.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant message content as a string.

        Raises:
            AIError: When the request ultimately fails after retries.
        """

    @abstractmethod
    def name(self) -> str:
        """Return the provider's display name."""


class NVIDIAProvider(AIProvider):
    """NVIDIA NIM chat completions provider."""

    def __init__(self, config: Config) -> None:
        """Initialize the provider with a config."""
        self._config = config

    def name(self) -> str:
        """Return the provider display name."""
        return "nvidia-nim"

    def _headers(self) -> dict[str, str]:
        """Build request headers with the API key."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.require_api_key()}",
        }

    def _payload(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> bytes:
        """Serialize the request payload."""
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return json.dumps(data).encode("utf-8")

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat request with retries and exponential backoff.

        Raises:
            AIError: When the request ultimately fails after retries.
        """
        selected_model = model or self._config.model_generic
        url = f"{self._config.nvidia_base_url.rstrip('/')}/chat/completions"
        body = self._payload(system_prompt, user_prompt, selected_model, temperature, max_tokens)

        attempts = self._config.nvidia_retry_count
        delay = self._config.nvidia_retry_delay

        for attempt in range(1, attempts + 1):
            try:
                logger.debug(
                    "NVIDIA request model=%s system=%d chars user=%d chars",
                    selected_model,
                    len(system_prompt),
                    len(user_prompt),
                )
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers=self._headers(),
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self._config.nvidia_timeout) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                logger.info(
                    "NVIDIA response model=%s finish=%s",
                    selected_model,
                    result.get("choices", [{}])[0].get("finish_reason", "unknown"),
                )
                return content
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise AIError("NVIDIA API key is invalid (HTTP 401)") from exc
                if exc.code == 429:
                    retry_after = exc.headers.get("Retry-After", str(delay))
                    logger.warning(
                        "Rate limited (429), waiting %ss (attempt %d/%d)",
                        retry_after,
                        attempt,
                        attempts,
                    )
                    time.sleep(float(retry_after))
                    continue
                if exc.code in {502, 503, 504}:
                    logger.warning(
                        "NVIDIA service unavailable (%s), attempt %d/%d",
                        exc.code,
                        attempt,
                        attempts,
                    )
                    if attempt < attempts:
                        time.sleep(delay * attempt)
                        continue
                raise AIError(f"NVIDIA HTTP error {exc.code}: {exc.reason}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                logger.warning(
                    "NVIDIA network error (%s), attempt %d/%d",
                    type(exc).__name__,
                    attempt,
                    attempts,
                )
                if attempt < attempts:
                    time.sleep(delay * attempt)
                    continue
                raise AIError(f"NVIDIA network failure: {exc}") from exc
            except (KeyError, json.JSONDecodeError) as exc:
                raise AIError(f"NVIDIA malformed response: {exc}") from exc

        raise AIError("NVIDIA request exhausted all retries")


def extract_json(text: str) -> dict[str, object]:
    """Extract a JSON object from model output, tolerating code fences.

    Args:
        text: Raw model output that may include markdown fences or prose.

    Returns:
        The parsed JSON dictionary.

    Raises:
        json.JSONDecodeError: If no valid JSON object can be extracted.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.removesuffix("```")
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
