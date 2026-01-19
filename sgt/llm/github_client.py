"""GitHub Models LLM client implementation.

Uses the GitHub Models inference endpoint (models.github.ai/inference) with
OpenAI-compatible API.
"""

import os
from typing import Optional, AsyncIterator

from sgt.llm.base import BaseLLMClient, LLMConfig, LLMResponse, LLMProvider


# GitHub Models endpoint
GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"


class GitHubModelsClient(BaseLLMClient):
    """GitHub Models client using OpenAI-compatible API."""
    
    # Available models on GitHub Models
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "o1-preview",
        "o1-mini",
        "AI21-Jamba-1.5-Large",
        "AI21-Jamba-1.5-Mini",
        "Cohere-command-r",
        "Cohere-command-r-plus",
        "meta-llama-3.1-405b-instruct",
        "meta-llama-3.1-70b-instruct",
        "meta-llama-3.1-8b-instruct",
        "Mistral-large",
        "Mistral-large-2407",
        "Mistral-Nemo",
        "Mistral-small",
        "Phi-3.5-MoE-instruct",
        "Phi-3.5-mini-instruct",
        "Phi-3.5-vision-instruct",
    ]
    
    def __init__(self, config: Optional[LLMConfig] = None, api_key: Optional[str] = None):
        """Initialize the GitHub Models client.
        
        Args:
            config: LLM configuration (optional)
            api_key: GitHub token (overrides config and env var)
        """
        if config is None:
            config = LLMConfig(
                provider=LLMProvider.GITHUB,
                base_url=GITHUB_MODELS_BASE_URL,
            )
        
        # Ensure base_url is set
        if not config.base_url:
            config.base_url = GITHUB_MODELS_BASE_URL
        
        super().__init__(config)
        
        # Get API key from argument, config, or environment
        # GitHub Models uses GitHub personal access token
        self._api_key = (
            api_key 
            or config.api_key 
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
        )
        
        if not self._api_key:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN environment variable "
                "or pass api_key argument."
            )
    
    @property
    def provider_name(self) -> str:
        return "github"
    
    def _get_client(self):
        """Get or create the OpenAI client configured for GitHub Models."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
            
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion using GitHub Models.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional arguments (model, temperature, max_tokens)
            
        Returns:
            LLMResponse with the generated content
        """
        client = self._get_client()
        model = kwargs.get("model", self.config.get_model())
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )
    
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion using GitHub Models.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional arguments
            
        Yields:
            String chunks of the response
        """
        client = self._get_client()
        model = kwargs.get("model", self.config.get_model())
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
        self._client = None
    
    @classmethod
    def list_models(cls) -> list[str]:
        """List available models on GitHub Models."""
        return cls.AVAILABLE_MODELS.copy()
