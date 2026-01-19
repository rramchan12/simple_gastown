"""Demo script showing LLM integration (Phase 3).

This demo shows how workers can use LLM providers (OpenAI, Anthropic, GitHub Models)
to actually complete tasks instead of simulating them.

Prerequisites:
    Set at least one of these environment variables:
    - OPENAI_API_KEY: For OpenAI GPT models
    - ANTHROPIC_API_KEY: For Anthropic Claude models
    - GITHUB_TOKEN: For GitHub Models (free tier available!)

Usage:
    python demo_llm.py
    python demo_llm.py --provider openai
    python demo_llm.py --provider anthropic --model claude-3-haiku-20240307
    python demo_llm.py --provider github --model gpt-4o-mini
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()


async def test_llm_providers():
    """Test available LLM providers."""
    from sgt.llm.factory import auto_detect_provider, create_llm_client
    
    console.print("\n[bold cyan]═══ LLM Provider Test ═══[/bold cyan]\n")
    
    # Check available providers
    providers = []
    
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "gpt-4o-mini"))
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("anthropic", "claude-3-haiku-20240307"))
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        providers.append(("github", "gpt-4o-mini"))
    
    if not providers:
        console.print("[red]No LLM providers configured![/red]")
        console.print("\nPlease set one of these environment variables:")
        console.print("  - OPENAI_API_KEY")
        console.print("  - ANTHROPIC_API_KEY")
        console.print("  - GITHUB_TOKEN (free with GitHub account!)")
        return None
    
    # Show available providers
    table = Table(title="Available Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Test Model", style="green")
    
    for provider, model in providers:
        table.add_row(provider, model)
    
    console.print(table)
    
    # Test the first available provider
    provider, model = providers[0]
    console.print(f"\n[cyan]Testing {provider} with {model}...[/cyan]")
    
    try:
        client = create_llm_client(provider=provider, model=model)
        
        response = await client.complete(
            system_prompt="You are a helpful assistant. Be brief.",
            user_prompt="Say 'LLM integration working!' and nothing else.",
        )
        
        await client.close()
        
        console.print(f"[green]✓ Response:[/green] {response.content.strip()}")
        return provider
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        return None


async def demo_llm_worker():
    """Demo a worker using LLM to complete a task."""
    from sgt.core.workspace import WorkspaceManager
    from sgt.core.task_manager import TaskManager
    from sgt.core.agent_manager import AgentManager
    from sgt.llm.factory import auto_detect_provider
    
    console.print("\n[bold cyan]═══ LLM Worker Demo ═══[/bold cyan]\n")
    
    # Check for provider
    provider = auto_detect_provider()
    if not provider:
        console.print("[red]No LLM provider available. Skipping worker demo.[/red]")
        return
    
    console.print(f"[cyan]Using provider:[/cyan] {provider}\n")
    
    # Setup demo directory
    demo_dir = Path(__file__).parent / "demo-llm-temp"
    if demo_dir.exists():
        shutil.rmtree(demo_dir, ignore_errors=True)
    
    try:
        # Initialize town
        console.print("[1] Initializing Gas Town...")
        workspace_mgr = WorkspaceManager()
        workspace_mgr.init_town(demo_dir)
        console.print(f"   [green]✓[/green] Town created at {demo_dir}")
        
        # Add project
        console.print("[2] Adding project...")
        workspace_mgr.add_project(demo_dir, "demo-app")
        console.print("   [green]✓[/green] Project 'demo-app' created")
        
        # Create a task
        console.print("[3] Creating task...")
        task_mgr = TaskManager(demo_dir / "projects" / "demo-app")
        
        task = task_mgr.create_task(
            title="Write a Python function",
            description="""Write a Python function called 'fibonacci' that:
1. Takes a single integer argument 'n'
2. Returns the nth Fibonacci number (0-indexed, so fib(0)=0, fib(1)=1)
3. Uses efficient iteration (not recursion)
4. Includes a docstring with examples
5. Handles edge cases (negative numbers, etc.)

Provide just the function code."""
        )
        console.print(f"   [green]✓[/green] Task created: {task.id[:16]}...")
        
        # Spawn worker
        console.print("[4] Spawning worker...")
        agent_mgr = AgentManager(demo_dir)
        worker_state = agent_mgr.spawn_worker(
            project="demo-app",
            task_id=task.id,
            instructions="Write clean, well-documented Python code."
        )
        console.print(f"   [green]✓[/green] Worker: {worker_state.id[:16]}...")
        
        # Run worker with LLM
        console.print("[5] Running worker with LLM...")
        console.print(f"   [dim]This may take a few seconds...[/dim]\n")
        
        from sgt.agents.worker import Worker
        
        worker = Worker(
            worker_id=worker_state.id,
            workspace=Path(worker_state.workspace),
            town_root=demo_dir,
            project="demo-app",
            use_llm=True,
            llm_provider=provider,
        )
        
        await worker.run()
        
        # Show result
        console.print("\n[6] Task result:")
        updated_task = task_mgr.get_task(task.id)
        
        if updated_task and updated_task.result:
            console.print(Panel(
                updated_task.result,
                title="LLM Generated Code",
                border_style="green"
            ))
        
        console.print("\n[bold green]✓ LLM Worker Demo Complete![/bold green]")
        
    finally:
        # Cleanup
        if demo_dir.exists():
            shutil.rmtree(demo_dir, ignore_errors=True)


async def demo_streaming():
    """Demo streaming LLM responses."""
    from sgt.llm.factory import auto_detect_provider, create_llm_client
    
    console.print("\n[bold cyan]═══ Streaming Demo ═══[/bold cyan]\n")
    
    provider = auto_detect_provider()
    if not provider:
        console.print("[red]No LLM provider available.[/red]")
        return
    
    console.print(f"[cyan]Provider:[/cyan] {provider}")
    console.print("[cyan]Prompt:[/cyan] Explain what makes Python great in 3 sentences.\n")
    console.print("[green]Streaming response:[/green]", end=" ")
    
    try:
        client = create_llm_client(provider=provider)
        
        async for chunk in client.stream(
            system_prompt="You are concise and informative.",
            user_prompt="Explain what makes Python great in 3 sentences.",
        ):
            console.print(chunk, end="")
        
        await client.close()
        console.print("\n")
        
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")


async def main():
    """Run the LLM demo."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Gas Town - LLM Demo")
    parser.add_argument("--provider", "-p", choices=["openai", "anthropic", "github"],
                       help="LLM provider to use")
    parser.add_argument("--model", "-m", help="Model to use")
    parser.add_argument("--test-only", action="store_true", help="Only test providers")
    parser.add_argument("--stream-only", action="store_true", help="Only demo streaming")
    args = parser.parse_args()
    
    console.print(Panel.fit(
        "[bold cyan]Simple Gas Town[/bold cyan]\n"
        "[dim]Phase 3: LLM Integration Demo[/dim]",
        border_style="cyan"
    ))
    
    # Override provider/model via env if specified
    if args.provider:
        os.environ["SGT_LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["SGT_LLM_MODEL"] = args.model
    
    # Test providers
    available_provider = await test_llm_providers()
    
    if args.test_only:
        return
    
    if not available_provider:
        console.print("\n[yellow]Set an API key to see the full demo.[/yellow]")
        return
    
    if args.stream_only:
        await demo_streaming()
        return
    
    # Demo streaming
    await demo_streaming()
    
    # Demo worker with LLM
    await demo_llm_worker()
    
    console.print("\n" + "═" * 50)
    console.print("[bold green]Phase 3 Demo Complete![/bold green]")
    console.print("\nWorkers can now use LLM to complete tasks!")
    console.print("\nUsage:")
    console.print("  sgt llm providers      # Check configured providers")
    console.print("  sgt llm test           # Test LLM connection")
    console.print("  sgt worker run <id>    # Run worker with LLM (default)")
    console.print("  sgt worker run <id> --no-llm  # Run in simulation mode")


if __name__ == "__main__":
    asyncio.run(main())
