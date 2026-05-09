"""
LLM abstraction layer.
Supports OpenAI API, Groq (free Mistral/LLaMA), and local Ollama.
The abstraction allows swapping providers without changing business logic.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseLLM(ABC):
    """Interface for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        """Generate a response given system and user prompts."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class OpenAILLM(BaseLLM):
    """OpenAI API provider (GPT-4o-mini, GPT-4o, etc.)."""

    def __init__(self, model: str = None, api_key: str = None):
        from openai import OpenAI

        self._model = model or settings.llm_model
        self._client = OpenAI(api_key=api_key or settings.openai_api_key)
        logger.info("openai_llm_initialized", model=self._model)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        max_tokens = max_tokens or settings.llm_max_tokens
        temperature = temperature if temperature is not None else settings.llm_temperature

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    @property
    def model_name(self) -> str:
        return self._model


class GroqLLM(BaseLLM):
    """Groq API provider — free Mistral/LLaMA inference at high speed."""

    def __init__(self, model: str = None, api_key: str = None):
        from openai import OpenAI

        self._model = model or "mixtral-8x7b-32768"
        # Groq uses OpenAI-compatible API
        self._client = OpenAI(
            api_key=api_key or settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        logger.info("groq_llm_initialized", model=self._model)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        max_tokens = max_tokens or settings.llm_max_tokens
        temperature = temperature if temperature is not None else settings.llm_temperature

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    @property
    def model_name(self) -> str:
        return f"groq/{self._model}"


class OllamaLLM(BaseLLM):
    """Local Ollama provider for fully offline inference."""

    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        import httpx

        self._model = model
        self._base_url = base_url
        self._client = httpx.Client(timeout=120.0)
        logger.info("ollama_llm_initialized", model=model, url=base_url)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        temperature = temperature if temperature is not None else settings.llm_temperature

        response = self._client.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or settings.llm_max_tokens,
                },
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    @property
    def model_name(self) -> str:
        return f"ollama/{self._model}"


def create_llm(provider: str = None) -> BaseLLM:
    """Factory function to create the configured LLM provider."""
    provider = provider or settings.llm_provider

    if provider == "openai":
        return OpenAILLM()
    elif provider == "groq":
        return GroqLLM()
    elif provider == "local" or provider == "ollama":
        return OllamaLLM()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
