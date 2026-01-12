"""Convoy management commands."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sgt.models import ConvoyStatus
from sgt.storage.state import StateManager
from sgt.core.task_manager import TaskManager
from sgt.core.convoy_manager import ConvoyManager

console = Console()


@click.group()
def convoy():
    """Manage convoys (task batches)."""
    pass


@convoy.command('create')
@click.argument('name')
@click.argument('task_ids', nargs=-1, required=True)
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def convoy_create(name, task_ids, project, town):
    """Create a new convoy with tasks."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    if not project_path.exists():
        console.print(f"[red]Error: Project '{project}' not found[/red]")
        return
    
    # Verify all tasks exist
    task_manager = TaskManager(project_path)
    for task_id in task_ids:
        if not task_manager.get_task(task_id):
            console.print(f"[red]Error: Task {task_id} not found[/red]")
            return
    
    # Create convoy
    state_manager = StateManager(town_path)
    convoy_manager = ConvoyManager(state_manager, task_manager)
    
    convoy_obj = convoy_manager.create_convoy(name, list(task_ids))
    
    console.print(f"[green]✓[/green] Created convoy {convoy_obj.id}")
    console.print(f"  Name: {name}")
    console.print(f"  Tasks: {len(task_ids)}")


@convoy.command('list')
@click.option('--status', type=click.Choice(['active', 'completed']))
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def convoy_list(status, town):
    """List convoys."""
    town_path = Path(town).resolve()
    
    state_manager = StateManager(town_path)
    
    status_filter = ConvoyStatus(status) if status else None
    convoys = state_manager.list_convoys(status=status_filter.value if status_filter else None)
    
    if not convoys:
        console.print("[yellow]No convoys found[/yellow]")
        return
    
    table = Table(title="Convoys")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Tasks", style="magenta")
    table.add_column("Created", style="dim")
    
    for c in convoys:
        table.add_row(
            c.id[-12:],
            c.name,
            c.status.value,
            str(len(c.tasks)),
            str(c.created_at)[:19]
        )
    
    console.print(table)


@convoy.command('status')
@click.argument('convoy_id')
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def convoy_status(convoy_id, project, town):
    """Show convoy progress and status."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    state_manager = StateManager(town_path)
    task_manager = TaskManager(project_path)
    convoy_manager = ConvoyManager(state_manager, task_manager)
    
    convoy_obj = convoy_manager.get_convoy(convoy_id)
    if not convoy_obj:
        console.print(f"[red]Error: Convoy {convoy_id} not found[/red]")
        return
    
    progress = convoy_manager.get_convoy_progress(convoy_id)
    
    info = f"""[bold]Convoy: {convoy_obj.name}[/bold]

[cyan]ID:[/cyan] {convoy_obj.id}
[cyan]Status:[/cyan] {convoy_obj.status.value}
[cyan]Created:[/cyan] {convoy_obj.created_at}

[bold]Progress:[/bold]
  Total Tasks: {progress['total']}
  Completed: {progress['completed']} ✅
  In Progress: {progress['in_progress']} 🔵
  Failed: {progress['failed']} ❌
  Pending: {progress['pending']} ⚪
  
  Progress: {progress['percent_complete']:.1f}%
"""
    
    console.print(Panel(info, border_style="green"))
    
    # Show individual tasks
    console.print("\n[bold]Tasks:[/bold]\n")
    
    table = Table()
    table.add_column("Task ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Assignee", style="green")
    
    for task_id in convoy_obj.tasks:
        task = task_manager.get_task(task_id)
        if task:
            status_emoji = {
                "open": "⚪",
                "in_progress": "🔵",
                "completed": "✅",
                "failed": "❌"
            }.get(task.status.value, "")
            
            table.add_row(
                task.id[-12:],
                task.title,
                f"{status_emoji} {task.status.value}",
                task.assignee or "-"
            )
    
    console.print(table)
