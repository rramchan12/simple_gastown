"""LLM-related CLI commands."""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sgt.llm.factory import (
    get_available_providers,
    auto_detect_provider,
    create_llm_client,
)
from sgt.llm.base import LLMProvider

console = Console()


@click.group()
def llm():
    """LLM configuration and testing commands."""
    pass


@llm.command("providers")
def list_providers():
    """List available LLM providers."""
    table = Table(title="Available LLM Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Env Variable", style="green")
    table.add_column("Default Model", style="yellow")
    table.add_column("Status", style="magenta")
    
    import os
    
    provider_info = [
        ("openai", "OPENAI_API_KEY", "gpt-4o"),
        ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
        ("github", "GITHUB_TOKEN", "gpt-4o"),
    ]
    
    for provider, env_var, default_model in provider_info:
        has_key = bool(os.environ.get(env_var))
        # Also check GH_TOKEN for GitHub
        if provider == "github" and not has_key:
            has_key = bool(os.environ.get("GH_TOKEN"))
        
        status = "✓ Configured" if has_key else "✗ Not configured"
        table.add_row(provider, env_var, default_model, status)
    
    console.print(table)
    
    # Show auto-detected provider
    detected = auto_detect_provider()
    if detected:
        console.print(f"\n[green]Auto-detected provider:[/green] {detected}")
    else:
        console.print("\n[yellow]No provider auto-detected. Set an API key to enable LLM.[/yellow]")


@llm.command("test")
@click.option("--provider", "-p", type=click.Choice(["openai", "anthropic", "github"]), 
              help="LLM provider to test")
@click.option("--model", "-m", help="Model to use")
@click.option("--prompt", default="Say hello and introduce yourself in one sentence.",
              help="Test prompt to send")
def test_llm(provider, model, prompt):
    """Test LLM connection and response."""
    
    async def _test():
        # Auto-detect if no provider specified
        actual_provider = provider or auto_detect_provider()
        
        if not actual_provider:
            console.print("[red]Error:[/red] No provider specified and none auto-detected.")
            console.print("Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GITHUB_TOKEN")
            return
        
        console.print(f"[cyan]Testing provider:[/cyan] {actual_provider}")
        if model:
            console.print(f"[cyan]Model:[/cyan] {model}")
        
        try:
            client_kwargs = {}
            if model:
                client_kwargs["model"] = model
            
            client = create_llm_client(provider=actual_provider, **client_kwargs)
            
            console.print(f"[cyan]Prompt:[/cyan] {prompt}")
            console.print()
            
            with console.status("Generating response..."):
                response = await client.complete(
                    system_prompt="You are a helpful assistant.",
                    user_prompt=prompt,
                )
            
            await client.close()
            
            # Display response
            console.print(Panel(
                response.content,
                title=f"Response from {response.model}",
                border_style="green"
            ))
            
            # Display usage
            if response.usage:
                console.print(f"\n[dim]Tokens used: {response.usage.get('total_tokens', 'N/A')}[/dim]")
            
            console.print("\n[green]✓ LLM connection successful![/green]")
            
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {e}")
    
    asyncio.run(_test())


@llm.command("stream")
@click.option("--provider", "-p", type=click.Choice(["openai", "anthropic", "github"]),
              help="LLM provider to use")
@click.option("--model", "-m", help="Model to use")
@click.argument("prompt")
def stream_response(provider, model, prompt):
    """Stream a response from the LLM."""
    
    async def _stream():
        actual_provider = provider or auto_detect_provider()
        
        if not actual_provider:
            console.print("[red]Error:[/red] No provider specified and none auto-detected.")
            return
        
        console.print(f"[cyan]Provider:[/cyan] {actual_provider}")
        console.print(f"[cyan]Prompt:[/cyan] {prompt}\n")
        
        try:
            client_kwargs = {}
            if model:
                client_kwargs["model"] = model
            
            client = create_llm_client(provider=actual_provider, **client_kwargs)
            
            console.print("[green]Response:[/green]", end=" ")
            
            async for chunk in client.stream(
                system_prompt="You are a helpful assistant.",
                user_prompt=prompt,
            ):
                console.print(chunk, end="")
            
            await client.close()
            console.print("\n")
            
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
    
    asyncio.run(_stream())


@llm.command("models")
@click.option("--provider", "-p", type=click.Choice(["github"]),
              help="Provider to list models for (currently only github supported)")
def list_models(provider):
    """List available models for a provider."""
    if provider == "github" or not provider:
        from sgt.llm.github_client import GitHubModelsClient
        
        models = GitHubModelsClient.list_models()
        
        table = Table(title="GitHub Models - Available Models")
        table.add_column("Model", style="cyan")
        
        for model in models:
            table.add_row(model)
        
        console.print(table)
    else:
        console.print(f"[yellow]Model listing not available for {provider}[/yellow]")
        console.print("Use provider documentation to see available models.")
