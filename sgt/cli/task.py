"""Task management commands."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sgt.models import TaskPriority, TaskStatus
from sgt.core.task_manager import TaskManager

console = Console()


@click.group()
def task():
    """Manage tasks."""
    pass


@task.command('create')
@click.argument('title')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--priority', type=click.Choice(['high', 'normal', 'low']), default='normal')
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def task_create(title, description, priority, project, town):
    """Create a new task."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    if not project_path.exists():
        console.print(f"[red]Error: Project '{project}' not found[/red]")
        console.print("Run 'sgt project add <name>' first")
        return
    
    task_manager = TaskManager(project_path)
    task = task_manager.create_task(
        title=title,
        description=description,
        priority=TaskPriority(priority)
    )
    
    console.print(f"[green]✓[/green] Created task {task.id}")
    console.print(f"  Title: {task.title}")
    console.print(f"  Priority: {task.priority.value}")
    if description:
        console.print(f"  Description: {task.description}")


@task.command('list')
@click.option('--status', type=click.Choice(['open', 'in_progress', 'completed', 'failed']))
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def task_list(status, project, town):
    """List tasks."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    if not project_path.exists():
        console.print(f"[red]Error: Project '{project}' not found[/red]")
        return
    
    task_manager = TaskManager(project_path)
    
    status_filter = TaskStatus(status) if status else None
    tasks = task_manager.list_tasks(status=status_filter)
    
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return
    
    table = Table(title=f"Tasks - {project}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Assignee", style="green")
    
    for t in tasks:
        status_emoji = {
            "open": "⚪",
            "in_progress": "🔵",
            "completed": "✅",
            "failed": "❌"
        }.get(t.status.value, "")
        
        table.add_row(
            t.id[-12:],  # Show last 12 chars
            t.title,
            f"{status_emoji} {t.status.value}",
            t.priority.value,
            t.assignee or "-"
        )
    
    console.print(table)


@task.command('show')
@click.argument('task_id')
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def task_show(task_id, project, town):
    """Show detailed task information."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    task_manager = TaskManager(project_path)
    task = task_manager.get_task(task_id)
    
    if not task:
        console.print(f"[red]Error: Task {task_id} not found[/red]")
        return
    
    info = f"""[bold]Task Details[/bold]

[cyan]ID:[/cyan] {task.id}
[cyan]Title:[/cyan] {task.title}
[cyan]Description:[/cyan] {task.description or '(none)'}
[cyan]Status:[/cyan] {task.status.value}
[cyan]Priority:[/cyan] {task.priority.value}
[cyan]Project:[/cyan] {task.project}
[cyan]Assignee:[/cyan] {task.assignee or '(unassigned)'}
[cyan]Created:[/cyan] {task.created_at}
[cyan]Updated:[/cyan] {task.updated_at}
"""
    
    if task.completed_at:
        info += f"[cyan]Completed:[/cyan] {task.completed_at}\n"
    
    if task.result:
        info += f"\n[bold]Result:[/bold]\n{task.result}\n"
    
    if task.convoy_id:
        info += f"[cyan]Convoy:[/cyan] {task.convoy_id}\n"
    
    console.print(Panel(info, border_style="green"))


@task.command('update')
@click.argument('task_id')
@click.option('--status', type=click.Choice(['open', 'in_progress', 'completed', 'failed']))
@click.option('--project', required=True, help='Project name')
@click.option('--town', type=click.Path(), default='.', help='Town root directory')
def task_update(task_id, status, project, town):
    """Update a task's status."""
    town_path = Path(town).resolve()
    project_path = town_path / "projects" / project
    
    task_manager = TaskManager(project_path)
    
    if not task_manager.get_task(task_id):
        console.print(f"[red]Error: Task {task_id} not found[/red]")
        return
    
    task_manager.update_task_status(task_id, TaskStatus(status))
    
    console.print(f"[green]✓[/green] Updated task {task_id} status to {status}")
