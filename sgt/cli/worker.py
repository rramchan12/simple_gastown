"""Worker management commands."""

import click
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table

from sgt.storage.state import StateManager
from sgt.core.agent_manager import AgentManager
from sgt.agents.worker import run_worker

console = Console()


@click.group()
def worker():
    """Manage workers."""
    pass


@worker.command('list')
@click.option('--project', help='Filter by project')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def worker_list(project, town):
    """List all workers."""
    town_path = Path(town).resolve()
    
    state_manager = StateManager(town_path)
    workers = state_manager.list_agents(agent_type="worker")
    
    if project:
        workers = [w for w in workers if w.project == project]
    
    if not workers:
        console.print("[yellow]No workers running[/yellow]")
        return
    
    table = Table(title="Workers")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="yellow")
    table.add_column("Project", style="green")
    table.add_column("Task", style="magenta")
    table.add_column("Started", style="dim")
    
    for w in workers:
        table.add_row(
            w.id[-12:],  # Show last 12 chars
            w.status.value,
            w.project or "-",
            w.task_id[-12:] if w.task_id else "-",
            str(w.started_at)[:19]  # Show date/time only
        )
    
    console.print(table)


@worker.command('spawn')
@click.argument('task_id')
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def worker_spawn(task_id, project, town):
    """Spawn a worker for a task."""
    town_path = Path(town).resolve()
    
    agent_manager = AgentManager(town_path)
    worker = agent_manager.spawn_worker(project, task_id)
    
    console.print(f"[green]✓[/green] Spawned worker {worker.id}")
    console.print(f"[dim]Workspace: {worker.workspace}[/dim]")


@worker.command('kill')
@click.argument('worker_id')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def worker_kill(worker_id, town):
    """Terminate a worker."""
    town_path = Path(town).resolve()
    
    agent_manager = AgentManager(town_path)
    agent_manager.kill_worker(worker_id)
    
    console.print(f"[green]✓[/green] Killed worker {worker_id}")


@worker.command('run')
@click.argument('worker_id')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
@click.option('--llm/--no-llm', default=True, help='Use LLM for task execution')
@click.option('--provider', '-p', type=click.Choice(['openai', 'anthropic', 'github']), help='LLM provider')
@click.option('--model', '-m', help='LLM model to use')
def worker_run(worker_id, town, llm, provider, model):
    """Run a worker (for testing/manual execution)."""
    town_path = Path(town).resolve()
    
    state_manager = StateManager(town_path)
    worker_agent = state_manager.get_agent(worker_id)
    
    if not worker_agent:
        console.print(f"[red]Error: Worker {worker_id} not found[/red]")
        return
    
    if not worker_agent.project:
        console.print(f"[red]Error: Worker has no project assigned[/red]")
        return
    
    console.print(f"[cyan]Running worker {worker_id}...[/cyan]")
    if llm:
        console.print(f"[dim]LLM enabled (provider: {provider or 'auto'}, model: {model or 'default'})[/dim]")
    else:
        console.print(f"[dim]LLM disabled (simulation mode)[/dim]")
    
    workspace = Path(worker_agent.workspace)
    
    # Run the worker
    try:
        asyncio.run(run_worker(
            worker_id, 
            workspace, 
            town_path, 
            worker_agent.project,
            use_llm=llm,
            llm_provider=provider,
            llm_model=model,
        ))
        console.print(f"[green]✓[/green] Worker {worker_id} completed")
    except Exception as e:
        console.print(f"[red]Error: Worker failed - {e}[/red]")


@worker.command('logs')
@click.argument('worker_id')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def worker_logs(worker_id, town):
    """View worker logs."""
    town_path = Path(town).resolve()
    
    state_manager = StateManager(town_path)
    worker_agent = state_manager.get_agent(worker_id)
    
    if not worker_agent:
        console.print(f"[red]Error: Worker {worker_id} not found[/red]")
        return
    
    workspace = Path(worker_agent.workspace)
    state_file = workspace / "state.json"
    
    if not state_file.exists():
        console.print("[yellow]No state file found[/yellow]")
        return
    
    import json
    with open(state_file) as f:
        state = json.load(f)
    
    console.print(f"\n[bold]Worker {worker_id} State[/bold]\n")
    for key, value in state.items():
        console.print(f"[cyan]{key}:[/cyan] {value}")
