"""LLM client factory for creating provider-specific clients."""

import os
from typing import Optional

from sgt.llm.base import BaseLLMClient, LLMConfig, LLMProvider


def get_available_providers() -> list[str]:
    """Get list of available LLM providers.
    
    Returns:
        List of provider names
    """
    return [p.value for p in LLMProvider]


def create_llm_client(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.
    
    Args:
        provider: LLM provider name ("openai", "anthropic", "github")
        api_key: API key for the provider (optional, will use env vars)
        model: Model to use (optional, will use provider default)
        **kwargs: Additional configuration options
        
    Returns:
        Configured LLM client
        
    Raises:
        ValueError: If provider is not supported
    """
    # Normalize provider name
    provider_lower = provider.lower()
    
    # Map provider strings to enum
    provider_map = {
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
        "claude": LLMProvider.ANTHROPIC,
        "github": LLMProvider.GITHUB,
        "gh": LLMProvider.GITHUB,
    }
    
    if provider_lower not in provider_map:
        available = ", ".join(get_available_providers())
        raise ValueError(
            f"Unknown provider: {provider}. Available providers: {available}"
        )
    
    llm_provider = provider_map[provider_lower]
    
    # Create config
    config = LLMConfig(
        provider=llm_provider,
        api_key=api_key,
        model=model,
        max_tokens=kwargs.get("max_tokens", 4096),
        temperature=kwargs.get("temperature", 0.7),
        timeout=kwargs.get("timeout", 120),
        base_url=kwargs.get("base_url"),
    )
    
    # Create client based on provider
    if llm_provider == LLMProvider.OPENAI:
        from sgt.llm.openai_client import OpenAIClient
        return OpenAIClient(config, api_key)
    
    elif llm_provider == LLMProvider.ANTHROPIC:
        from sgt.llm.anthropic_client import AnthropicClient
        return AnthropicClient(config, api_key)
    
    elif llm_provider == LLMProvider.GITHUB:
        from sgt.llm.github_client import GitHubModelsClient
        return GitHubModelsClient(config, api_key)
    
    else:
        raise ValueError(f"Provider not implemented: {provider}")


def auto_detect_provider() -> Optional[str]:
    """Auto-detect which provider to use based on available API keys.
    
    Returns:
        Provider name or None if no keys found
    """
    # Check in order of preference
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        return "github"
    
    return None


def create_auto_client(**kwargs) -> BaseLLMClient:
    """Create an LLM client using auto-detected provider.
    
    Args:
        **kwargs: Additional configuration options
        
    Returns:
        Configured LLM client
        
    Raises:
        ValueError: If no API keys found
    """
    provider = auto_detect_provider()
    
    if not provider:
        raise ValueError(
            "No LLM API keys found. Please set one of: "
            "OPENAI_API_KEY, ANTHROPIC_API_KEY, or GITHUB_TOKEN"
        )
    
    return create_llm_client(provider=provider, **kwargs)
