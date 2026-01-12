#!/usr/bin/env python
"""Demo script showing Simple Gas Town in action."""

import asyncio
import sys
from pathlib import Path
from rich.console import Console

# Add the project to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sgt.core.agent_manager import AgentManager
from sgt.core.task_manager import TaskManager
from sgt.core.convoy_manager import ConvoyManager
from sgt.core.workspace import WorkspaceManager
from sgt.storage.state import StateManager
from sgt.agents.worker import run_worker
from sgt.models import TaskPriority

console = Console()


async def main():
    """Run a complete demo of Simple Gas Town."""
    
    # Setup
    console.print("\n[bold cyan]Simple Gas Town Demo[/bold cyan]\n")
    
    town_root = Path("./demo-town").resolve()
    if town_root.exists():
        import shutil
        shutil.rmtree(town_root)
    
    # 1. Initialize town
    console.print("[bold]Step 1: Initializing town...[/bold]")
    town_root.mkdir(parents=True)
    (town_root / ".gastown").mkdir()
    (town_root / "state").mkdir()
    (town_root / "projects").mkdir()
    
    workspace_manager = WorkspaceManager(town_root)
    workspace_manager.create_manager_workspace()
    
    state_manager = StateManager(town_root)
    agent_manager = AgentManager(town_root)
    agent_manager.create_manager()
    
    console.print(f"[green]✓[/green] Town initialized at {town_root}\n")
    
    # 2. Create project
    console.print("[bold]Step 2: Creating project...[/bold]")
    project_name = "demo-app"
    project_path = town_root / "projects" / project_name
    project_path.mkdir(parents=True)
    (project_path / ".tasks").mkdir()
    
    task_manager = TaskManager(project_path)
    console.print(f"[green]✓[/green] Project '{project_name}' created\n")
    
    # 3. Create tasks
    console.print("[bold]Step 3: Creating tasks...[/bold]")
    
    task1 = task_manager.create_task(
        title="Setup authentication",
        description="Implement JWT-based authentication system",
        priority=TaskPriority.HIGH
    )
    console.print(f"[green]✓[/green] Created task: {task1.title} ({task1.id[-12:]})")
    
    task2 = task_manager.create_task(
        title="Add user registration",
        description="Create registration endpoint with validation",
        priority=TaskPriority.HIGH
    )
    console.print(f"[green]✓[/green] Created task: {task2.title} ({task2.id[-12:]})")
    
    task3 = task_manager.create_task(
        title="Implement password reset",
        description="Email-based password reset flow",
        priority=TaskPriority.NORMAL
    )
    console.print(f"[green]✓[/green] Created task: {task3.title} ({task3.id[-12:]})\n")
    
    # 4. Create convoy
    console.print("[bold]Step 4: Creating convoy...[/bold]")
    convoy_manager = ConvoyManager(state_manager, task_manager)
    convoy = convoy_manager.create_convoy(
        name="Authentication System",
        task_ids=[task1.id, task2.id, task3.id]
    )
    console.print(f"[green]✓[/green] Convoy '{convoy.name}' created with 3 tasks\n")
    
    # 5. Spawn workers and execute tasks
    console.print("[bold]Step 5: Spawning workers and executing tasks...[/bold]\n")
    
    for task in [task1, task2, task3]:
        console.print(f"[cyan]Processing task: {task.title}[/cyan]")
        
        # Spawn worker
        worker = agent_manager.spawn_worker(project_name, task.id, priority=task.priority)
        console.print(f"  [dim]Spawned worker {worker.id[-12:]}[/dim]")
        
        # Assign task
        task_manager.assign_task(task.id, worker.id)
        console.print(f"  [dim]Assigned task to worker[/dim]")
        
        # Run worker
        workspace = Path(worker.workspace)
        await run_worker(worker.id, workspace, town_root, project_name)
        console.print(f"  [green]✓ Worker completed task[/green]\n")
        
        # Clean up worker
        agent_manager.kill_worker(worker.id)
    
    # 6. Check convoy status
    console.print("[bold]Step 6: Checking convoy status...[/bold]")
    progress = convoy_manager.get_convoy_progress(convoy.id)
    
    console.print(f"[green]Convoy Progress:[/green]")
    console.print(f"  Total tasks: {progress['total']}")
    console.print(f"  Completed: {progress['completed']} ✅")
    console.print(f"  Progress: {progress['percent_complete']:.0f}%\n")
    
    # 7. Show task results
    console.print("[bold]Step 7: Task results...[/bold]\n")
    
    for task_id in [task1.id, task2.id, task3.id]:
        task = task_manager.get_task(task_id)
        console.print(f"[cyan]{task.title}[/cyan]")
        console.print(f"  Status: {task.status.value}")
        if task.result:
            console.print(f"  Result: {task.result[:100]}...")
        console.print()
    
    # Summary
    console.print("[bold green]Demo Complete! 🎉[/bold green]\n")
    console.print("Key features demonstrated:")
    console.print("  ✓ Town initialization")
    console.print("  ✓ Project and task creation")
    console.print("  ✓ Convoy (batch) management")
    console.print("  ✓ Worker spawning and execution")
    console.print("  ✓ Automatic task completion")
    console.print("  ✓ Progress tracking\n")
    
    console.print(f"[dim]Demo files created in: {town_root}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
