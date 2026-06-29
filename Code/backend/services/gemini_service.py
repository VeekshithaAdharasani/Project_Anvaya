import os
import logging
from typing import Any, Type, TypeVar
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar("T")


class GeminiConfigurationError(Exception):
    """Raised when the Gemini API is not configured correctly (e.g., missing API key)."""

    pass


class GeminiService:
    """Service to interact with the Google Gemini API.

    Handles text generation and structured JSON extraction.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY environment variable is not set. API calls will fail."
            )

        genai.configure(api_key=self.api_key)
        self.model_name = model_name

    def _get_model(
        self, system_instruction: str | None = None
    ) -> genai.GenerativeModel:
        """Helper to instantiate the GenerativeModel with optional system instructions."""
        if not self.api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not set. Please set the environment variable."
            )
        return genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
        )

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generates raw text from a prompt.

        Args:
            prompt: The user prompt.
            system_instruction: Optional system instruction.
            temperature: Creativity control.

        Returns:
            The generated text response.
        """
        try:
            model = self._get_model(system_instruction)
            config = GenerationConfig(temperature=temperature)
            response = model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            logger.error(f"Error during Gemini text generation: {e}")
            raise

    def generate_json(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> T:
        """Generates structured JSON output conforming to a Pydantic model.

        Args:
            prompt: The prompt.
            response_schema: The Pydantic model class to enforce.
            system_instruction: Optional system instruction.
            temperature: Creativity control (default low for extraction tasks).

        Returns:
            An instance of the response_schema Pydantic model.
        """
        try:
            model = self._get_model(system_instruction)
            config = GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_schema,
            )
            response = model.generate_content(prompt, generation_config=config)
            # Parse the JSON string directly into the Pydantic model
            return response_schema.model_validate_json(response.text)
        except Exception as e:
            logger.error(f"Error during Gemini JSON generation: {e}")
            raise
