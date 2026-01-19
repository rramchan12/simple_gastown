"""OpenAI LLM client implementation."""

import os
from typing import Optional, AsyncIterator

from sgt.llm.base import BaseLLMClient, LLMConfig, LLMResponse, LLMProvider


class OpenAIClient(BaseLLMClient):
    """OpenAI API client for GPT models."""
    
    def __init__(self, config: Optional[LLMConfig] = None, api_key: Optional[str] = None):
        """Initialize the OpenAI client.
        
        Args:
            config: LLM configuration (optional)
            api_key: API key (overrides config and env var)
        """
        if config is None:
            config = LLMConfig(provider=LLMProvider.OPENAI)
        
        super().__init__(config)
        
        # Get API key from argument, config, or environment
        self._api_key = api_key or config.api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key argument."
            )
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
            
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion using OpenAI.
        
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
        """Stream a completion using OpenAI.
        
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
