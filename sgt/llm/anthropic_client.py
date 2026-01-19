"""Anthropic LLM client implementation."""

import os
from typing import Optional, AsyncIterator

from sgt.llm.base import BaseLLMClient, LLMConfig, LLMResponse, LLMProvider


class AnthropicClient(BaseLLMClient):
    """Anthropic API client for Claude models."""
    
    def __init__(self, config: Optional[LLMConfig] = None, api_key: Optional[str] = None):
        """Initialize the Anthropic client.
        
        Args:
            config: LLM configuration (optional)
            api_key: API key (overrides config and env var)
        """
        if config is None:
            config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        
        super().__init__(config)
        
        # Get API key from argument, config, or environment
        self._api_key = api_key or config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self._api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key argument."
            )
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            
            self._client = AsyncAnthropic(
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
        """Generate a completion using Anthropic Claude.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional arguments (model, temperature, max_tokens)
            
        Returns:
            LLMResponse with the generated content
        """
        client = self._get_client()
        model = kwargs.get("model", self.config.get_model())
        
        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        
        # Extract text content from response
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        
        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
                "total_tokens": (
                    (response.usage.input_tokens + response.usage.output_tokens)
                    if response.usage else 0
                ),
            },
            finish_reason=response.stop_reason,
            raw_response=response,
        )
    
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion using Anthropic Claude.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message/task
            **kwargs: Additional arguments
            
        Yields:
            String chunks of the response
        """
        client = self._get_client()
        model = kwargs.get("model", self.config.get_model())
        
        async with client.messages.stream(
            model=model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=kwargs.get("temperature", self.config.temperature),
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
        self._client = None
