"""Base LLM client interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GITHUB = "github"


@dataclass
class LLMConfig:
    """Configuration for LLM clients."""
    provider: LLMProvider
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120
    
    # Default models per provider
    _default_models: dict = field(default_factory=lambda: {
        LLMProvider.OPENAI: "gpt-4o",
        LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
        LLMProvider.GITHUB: "gpt-4o",
    })
    
    def get_model(self) -> str:
        """Get the model to use, defaulting to provider default."""
        if self.model:
            return self.model
        return self._default_models.get(self.provider, "gpt-4o")


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    provider: str
    usage: Optional[dict] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None
    
    def __str__(self) -> str:
        return self.content


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, config: LLMConfig):
        """Initialize the LLM client.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self._client = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional provider-specific arguments
            
        Returns:
            LLMResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional provider-specific arguments
            
        Yields:
            String chunks of the response
        """
        pass
    
    async def close(self):
        """Clean up resources."""
        self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
