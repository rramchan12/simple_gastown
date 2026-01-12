"""Initialization and setup commands."""

import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from sgt.models import TownConfig
from sgt.storage.state import StateManager
from sgt.core.agent_manager import AgentManager
from sgt.core.task_manager import TaskManager
from sgt.core.workspace import WorkspaceManager

console = Console()


@click.command()
@click.argument('town_path', type=click.Path())
def init(town_path):
    """Initialize a new Gas Town."""
    town_path = Path(town_path).resolve()
    
    if town_path.exists() and any(town_path.iterdir()):
        console.print(f"[red]Error: Directory {town_path} already exists and is not empty[/red]")
        return
    
    # Create directory structure
    town_path.mkdir(parents=True, exist_ok=True)
    (town_path / ".gastown").mkdir(exist_ok=True)
    (town_path / "state").mkdir(exist_ok=True)
    (town_path / "state" / "logs").mkdir(exist_ok=True)
    (town_path / "projects").mkdir(exist_ok=True)
    
    # Create config
    config = TownConfig(town_root=str(town_path))
    config_file = town_path / ".gastown" / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)
    
    # Create manager workspace
    workspace_manager = WorkspaceManager(town_path)
    workspace_manager.create_manager_workspace()
    
    # Initialize state
    StateManager(town_path)
    
    # Create manager agent
    agent_manager = AgentManager(town_path)
    agent_manager.create_manager()
    
    console.print(f"[green]✓[/green] Initialized Gas Town at {town_path}")
    console.print(f"[dim]Manager workspace: {town_path / 'manager'}[/dim]")


@click.group()
def project():
    """Manage projects."""
    pass


@project.command('add')
@click.argument('project_name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def project_add(project_name, town):
    """Add a new project."""
    town_path = Path(town).resolve()
    
    if not (town_path / ".gastown").exists():
        console.print("[red]Error: Not a Gas Town directory[/red]")
        console.print("Run 'sgt init <path>' first")
        return
    
    # Create project directory
    project_path = town_path / "projects" / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Create .tasks directory
    tasks_dir = project_path / ".tasks"
    tasks_dir.mkdir(exist_ok=True)
    
    # Initialize task manager (creates tasks.json)
    TaskManager(project_path)
    
    # Create settings directory
    settings_dir = project_path / "settings"
    settings_dir.mkdir(exist_ok=True)
    
    config_file = settings_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump({"project_name": project_name}, f, indent=2)
    
    console.print(f"[green]✓[/green] Added project '{project_name}'")
    console.print(f"[dim]Location: {project_path}[/dim]")


@project.command('list')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def project_list(town):
    """List all projects."""
    town_path = Path(town).resolve()
    projects_path = town_path / "projects"
    
    if not projects_path.exists():
        console.print("[yellow]No projects found[/yellow]")
        return
    
    projects = [p.name for p in projects_path.iterdir() if p.is_dir()]
    
    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        return
    
    table = Table(title="Projects")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    
    for proj in sorted(projects):
        table.add_row(proj, str(projects_path / proj))
    
    console.print(table)


@click.command()
@click.argument('task_id')
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
@click.option('--instructions', help='Additional instructions for worker')
def assign(task_id, project, town, instructions):
    """Assign a task to a worker (spawns worker automatically)."""
    town_path = Path(town).resolve()
    
    # Get task
    project_path = town_path / "projects" / project
    task_manager = TaskManager(project_path)
    task = task_manager.get_task(task_id)
    
    if not task:
        console.print(f"[red]Error: Task {task_id} not found[/red]")
        return
    
    # Spawn worker
    agent_manager = AgentManager(town_path)
    worker = agent_manager.spawn_worker(project, task_id, instructions, task.priority)
    
    # Assign task
    task_manager.assign_task(task_id, worker.id)
    
    console.print(f"[green]✓[/green] Spawned worker {worker.id}")
    console.print(f"[green]✓[/green] Assigned task {task_id} to {worker.id}")
    console.print(f"[dim]Workspace: {worker.workspace}[/dim]")
    console.print("\n[yellow]Note:[/yellow] In Phase 1, workers must be run manually:")
    console.print(f"  python -m sgt.agents.worker {worker.id}")


@click.command()
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def status(town):
    """Show overall system status."""
    town_path = Path(town).resolve()
    
    if not (town_path / ".gastown").exists():
        console.print("[red]Error: Not a Gas Town directory[/red]")
        return
    
    state_manager = StateManager(town_path)
    
    # Show agents
    agents = state_manager.list_agents()
    
    console.print("\n[bold]Agents[/bold]")
    if agents:
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Task", style="dim")
        
        for agent in agents:
            table.add_row(
                agent.id,
                agent.type.value,
                agent.status.value,
                agent.task_id or "-"
            )
        
        console.print(table)
    else:
        console.print("[dim]No agents running[/dim]")
    
    # Show convoys
    convoys = state_manager.list_convoys()
    
    console.print("\n[bold]Convoys[/bold]")
    if convoys:
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Tasks", style="dim")
        
        for convoy in convoys:
            table.add_row(
                convoy.id,
                convoy.name,
                convoy.status.value,
                str(len(convoy.tasks))
            )
        
        console.print(table)
    else:
        console.print("[dim]No active convoys[/dim]")
