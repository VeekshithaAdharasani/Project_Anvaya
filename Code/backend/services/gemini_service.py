"""
Service layer delivering resilient, cached connections to the Google Gemini API.
Supports text generation, schema-enforced structured JSON generation, health checks,
and atomic exponential backoff configurations for production reliability.
"""

import os
import logging
import time
import random
import threading
from typing import Any, Type, TypeVar, Optional, Dict, Tuple, Callable, List
from dotenv import load_dotenv

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.api_core.exceptions import GoogleAPICallError, APIError

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

    def __init__(self, model_name: str = "gemini-1.5-flash") -> None:
        """
        Initializes the GeminiService, checking for environment keys and setting up cache.
        """
        self.api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY environment variable is not set. API calls will fail on invocation."
            )

        genai.configure(api_key=self.api_key)
        self.model_name: str = model_name

        # Thread-safe caching mechanism for GenerativeModel instances
        self._model_cache: Dict[Tuple[str, Optional[str]], genai.GenerativeModel] = {}
        self._cache_lock = threading.Lock()

    def _get_masked_api_key(self) -> str:
        """
        Safely formats the API key for logs to avoid accidental secret exposure.
        """
        if not self.api_key:
            return "NOT_SET"
        if len(self.api_key) <= 8:
            return "INVALID_KEY_LENGTH"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def _get_model(self, system_instruction: str | None = None) -> genai.GenerativeModel:
        """
        Retrieves a cached GenerativeModel instance or creates a new one thread-safely.
        """
        if not self.api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY environment variable is not set. Please set the variable."
            )

        cache_key = (self.model_name, system_instruction)
        
        # Guard lookup/assignment to ensure thread safety under concurrent ASGI requests
        with self._cache_lock:
            if cache_key in self._model_cache:
                return self._model_cache[cache_key]

            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
            )
            self._model_cache[cache_key] = model
            return model

    def _execute_with_retry(self, api_call: Callable[[], Any]) -> Any:
        """
        Executes a Gemini API action with exponential backoff on transient failure codes.
        Treats rate limits (429) and server exceptions (500, 503, 504) as retriable.
        """
        base_delay = 1.5
        factor = 2.0

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return api_call()
            except (GoogleAPICallError, APIError) as e:
                # Resolve the status code representing the error
                status_code = getattr(e, "code", None)
                is_transient = status_code in (429, 500, 503, 504)

                if not is_transient or attempt == self.MAX_RETRIES:
                    logger.exception(
                        f"Permanent or maximum-retried Google API error occurred (Status: {status_code})."
                    )
                    raise

                # Calculate exponential backoff delay with a random jitter (preventing thundering herds)
                delay = base_delay * (factor ** attempt) + random.uniform(0.1, 0.4)
                logger.warning(
                    f"Transient Gemini API failure (Status {status_code}). "
                    f"Retrying in {delay:.2f} seconds (Attempt {attempt + 1}/{self.MAX_RETRIES})..."
                )
                time.sleep(delay)
            except Exception as e:
                logger.exception(
                    f"Non-transient exception captured during API processing: {e}"
                )
                raise

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
        Generates raw text from a prompt, handling caching, retries, and safety validations.

        Raises:
            ValueError: If the API response contains no valid text.

        Time Complexity: Variable (network bound)
        Space Complexity: O(1)
        """
        model = self._get_model(system_instruction)

        config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
        )

        request_options = {"timeout": timeout}

        def make_call() -> genai.types.GenerateContentResponse:
            return model.generate_content(
                prompt,
                generation_config=config,
                request_options=request_options,
            )

        response = self._execute_with_retry(make_call)

        # Validate response candidates to detect safety blocks before accessing response.text
        if not response or not hasattr(response, "candidates") or not response.candidates:
            feedback = getattr(response, "prompt_feedback", "No prompt feedback provided.")
            raise ValueError(
                f"Gemini API returned an empty response with zero candidates. Feedback: {feedback}"
            )

        try:
            text = response.text
        except ValueError as e:
            # Handle prompt block/safety exceptions raised during property extraction
            feedback = getattr(response, "prompt_feedback", "Blocked by safety/recitation settings.")
            raise ValueError(
                f"Gemini API generation failed. Text is inaccessible. Feedback: {feedback}"
            ) from e

        if not text or not text.strip():
            raise ValueError("Gemini API response text is empty or blank.")

        return text

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
        Generates structured JSON output conforming to a Pydantic schema.

        Raises:
            ValueError: If the API response contains no valid text or breaks structural constraint.

        Time Complexity: Variable (network bound)
        Space Complexity: O(V_schema) representation.
        """
        model = self._get_model(system_instruction)

        config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        request_options = {"timeout": timeout}

        def make_call() -> genai.types.GenerateContentResponse:
            return model.generate_content(
                prompt,
                generation_config=config,
                request_options=request_options,
            )

        response = self._execute_with_retry(make_call)

        if not response or not hasattr(response, "candidates") or not response.candidates:
            feedback = getattr(response, "prompt_feedback", "No prompt feedback provided.")
            raise ValueError(
                f"Gemini API JSON generation returned an empty response. Feedback: {feedback}"
            )

        try:
            text = response.text
        except ValueError as e:
            feedback = getattr(response, "prompt_feedback", "Blocked by safety/recitation settings.")
            raise ValueError(
                f"Gemini API JSON generation failed. Text is inaccessible. Feedback: {feedback}"
            ) from e

        if not text or not text.strip():
            raise ValueError("Gemini API JSON response text is empty or blank.")

        # Structural serialization directly from the resulting raw payload
        return response_schema.model_validate_json(text)

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