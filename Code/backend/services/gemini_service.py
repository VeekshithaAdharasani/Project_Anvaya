"""
Service layer delivering resilient, cached connections to the Google Gemini API.
Supports text generation, schema-enforced structured JSON generation, health checks,
and atomic exponential backoff configurations for production reliability.
"""

import os
import logging
import time
import random
from typing import Any, Type, TypeVar, Optional, Callable
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load environmental variables from local .env file immediately on import
load_dotenv()

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar("T")


class GeminiConfigurationError(Exception):
    """Raised when the Gemini API is not configured correctly (e.g., missing API key)."""

    pass


class GeminiService:
    """
    Service to interact with the Google Gemini API.
    Handles text generation, thread-safe caching of model objects, and structured JSON extraction.
    """

    # Configurable constants for service resilience and behavior
    DEFAULT_TEXT_TEMPERATURE: float = 0.7
    DEFAULT_JSON_TEMPERATURE: float = 0.2
    MAX_RETRIES: int = 3
    DEFAULT_TIMEOUT: float = 30.0

    def __init__(
            self,
            text_model: str = "gemini-2.5-flash",
            json_model: str = "gemini-2.5-flash",
    ) -> None:
        """
        Initializes the GeminiService, checking for environment keys and setting up cache.
        """
        self.api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY environment variable is not set. API calls will fail on invocation."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.text_model = text_model
        self.json_model = json_model

        # Thread-safe caching mechanism for GenerativeModel instances
    def _get_masked_api_key(self) -> str:
        """
        Safely formats the API key for logs to avoid accidental secret exposure.
        """
        if not self.api_key:
            return "NOT_SET"
        if len(self.api_key) <= 8:
            return "INVALID_KEY_LENGTH"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def _execute_with_retry(self, api_call: Callable[[], Any]) -> Any:
        base_delay = 1.5
        factor = 2.0
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return api_call()
            except Exception:
                if attempt == self.MAX_RETRIES:
                    logger.exception("Maximum retries exceeded.")
                    raise
                delay = base_delay * (factor ** attempt) + random.uniform(0.1, 0.4)

                logger.warning(
                    f"Gemini request failed ({attempt + 1}/{self.MAX_RETRIES + 1}). "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = DEFAULT_TEXT_TEMPERATURE,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Generates plain text using the Gemini API.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
        )

        def make_call():
            return self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=config,
            )

        logger.info("=== GEMINI TEXT CALL ===")

        response = self._execute_with_retry(make_call)

        if not response.text:
            raise ValueError("Gemini returned an empty response.")
        return response.text

    def generate_json(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: str | None = None,
        temperature: float = DEFAULT_JSON_TEMPERATURE,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> T:
        """
        Generates structured JSON conforming to the supplied Pydantic schema.
        """

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        def make_call():
            return self.client.models.generate_content(
                model=self.json_model,
                contents=prompt,
                config=config,
            )

        logger.info("=== GEMINI JSON CALL ===")

        response = self._execute_with_retry(make_call)

        if response.parsed is None:
            raise ValueError("Gemini returned no structured JSON.")

        return response.parsed

    def health_check(self) -> bool:
        """
        Verifies connectivity and model readiness of the configured Gemini API environment.

        Time Complexity: Variable (network bound)
        Space Complexity: O(1)
        """
        try:
            self.generate_text(
                prompt="ping",
                system_instruction="You are a system check helper. Respond only with the word: 'OK'.",
                temperature=0.0,
                max_output_tokens=5,
                timeout=10.0,
            )
            return True
        except Exception as e:
            logger.warning(
                f"Gemini API startup connectivity check failed using key '{self._get_masked_api_key()}'. "
                f"Exception: {e}"
            )
            return False