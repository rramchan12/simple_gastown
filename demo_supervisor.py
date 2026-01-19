"""Demo script showing supervisor monitoring (Phase 4).

This demo shows:
1. Supervisor health monitoring of workers
2. Heartbeat tracking
3. Detection of stuck workers
4. Automatic nudging system

Usage:
    python demo_supervisor.py
"""

import asyncio
import os
import sys
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

console = Console()


async def demo_supervisor():
    """Demo the supervisor monitoring system."""
    from sgt.core.workspace import WorkspaceManager
    from sgt.core.task_manager import TaskManager
    from sgt.core.agent_manager import AgentManager
    from sgt.agents.supervisor import Supervisor, SupervisorConfig
    from sgt.storage.state import StateManager
    from sgt.models import AgentStatus
    
    console.print(Panel.fit(
        "[bold cyan]Simple Gas Town[/bold cyan]\n"
        "[dim]Phase 4: Supervisor & Monitoring Demo[/dim]",
        border_style="cyan"
    ))
    
    # Setup demo directory
    demo_dir = Path(__file__).parent / "demo-supervisor-temp"
    if demo_dir.exists():
        shutil.rmtree(demo_dir, ignore_errors=True)
    
    try:
        # Initialize town
        console.print("\n[1] Initializing Gas Town...")
        workspace_mgr = WorkspaceManager()
        workspace_mgr.init_town(demo_dir)
        console.print(f"   [green]✓[/green] Town created at {demo_dir}")
        
        # Add project
        console.print("\n[2] Adding project...")
        workspace_mgr.add_project(demo_dir, "demo-app")
        console.print("   [green]✓[/green] Project 'demo-app' created")
        
        # Create tasks
        console.print("\n[3] Creating tasks...")
        task_mgr = TaskManager(demo_dir / "projects" / "demo-app")
        
        tasks = []
        for i in range(3):
            t = task_mgr.create_task(
                title=f"Task {i+1}",
                description=f"Demo task number {i+1}"
            )
            tasks.append(t)
            console.print(f"   [green]✓[/green] Created: {t.id[:16]}...")
        
        # Spawn workers
        console.print("\n[4] Spawning workers...")
        agent_mgr = AgentManager(demo_dir)
        state_mgr = StateManager(demo_dir)
        
        workers = []
        for i, t in enumerate(tasks):
            worker = agent_mgr.spawn_worker(
                project="demo-app",
                task_id=t.id,
            )
            workers.append(worker)
            console.print(f"   [green]✓[/green] Worker {worker.id[:12]}... for task {t.id[:12]}...")
        
        # Set one worker as "running" for demo
        console.print("\n[5] Simulating worker states...")
        
        # Worker 1: Running and healthy (recent heartbeat)
        workers[0].status = AgentStatus.RUNNING
        workers[0].last_heartbeat = datetime.utcnow()
        state_mgr.add_agent(workers[0])
        console.print(f"   Worker 1: RUNNING (healthy heartbeat)")
        
        # Worker 2: Running but stuck (old heartbeat)
        workers[1].status = AgentStatus.RUNNING
        workers[1].last_heartbeat = datetime.utcnow() - timedelta(minutes=10)
        state_mgr.add_agent(workers[1])
        console.print(f"   Worker 2: RUNNING (stale heartbeat - 10min)")
        
        # Worker 3: Idle
        workers[2].status = AgentStatus.IDLE
        workers[2].last_heartbeat = datetime.utcnow() - timedelta(minutes=2)
        state_mgr.add_agent(workers[2])
        console.print(f"   Worker 3: IDLE")
        
        # Create supervisor
        console.print("\n[6] Starting supervisor...")
        
        config = SupervisorConfig(
            check_interval=5,  # Fast checks for demo
            worker_timeout=60,  # 60 seconds timeout
            nudge_interval=10,  # 10 seconds between nudges
            max_nudges=3,
        )
        
        supervisor = Supervisor(demo_dir, config)
        console.print("   [green]✓[/green] Supervisor created")
        console.print(f"   Config: timeout={config.worker_timeout}s, nudge_interval={config.nudge_interval}s")
        
        # Show health status
        console.print("\n[7] Initial health check...")
        health_list = supervisor.get_all_worker_health()
        
        table = Table(title="Worker Health Status")
        table.add_column("Worker", style="cyan")
        table.add_column("Status")
        table.add_column("Task")
        table.add_column("Heartbeat Age")
        table.add_column("Health")
        
        for health in health_list:
            if health.is_healthy:
                health_str = "[green]✓ Healthy[/green]"
            elif health.is_stuck:
                health_str = "[red]✗ STUCK[/red]"
            else:
                health_str = f"[yellow]⚠ {health.message}[/yellow]"
            
            status_str = f"[{'green' if health.status == AgentStatus.RUNNING else 'yellow'}]{health.status.value}[/]"
            
            table.add_row(
                health.worker_id[-12:],
                status_str,
                health.task_id[-12:] if health.task_id else "-",
                f"{int(health.seconds_since_heartbeat)}s",
                health_str,
            )
        
        console.print(table)
        
        # Show summary
        summary = supervisor.get_summary()
        console.print(f"\n   Total: {summary['total_workers']} | Healthy: {summary['healthy']} | Stuck: {summary['stuck']}")
        
        # Demo supervisor running for a few cycles
        console.print("\n[8] Running supervisor for 3 health check cycles...")
        console.print("   [dim]Supervisor will detect stuck workers and send nudges[/dim]\n")
        
        check_count = 0
        
        async def run_checks():
            nonlocal check_count
            while check_count < 3:
                # Perform health check
                console.print(f"   [cyan]Health check #{check_count + 1}...[/cyan]")
                
                for worker in state_mgr.list_agents(agent_type="worker"):
                    health = supervisor._assess_worker_health(worker, datetime.utcnow())
                    
                    if health.is_stuck:
                        console.print(f"   [red]→ Worker {worker.id[-12:]} is stuck![/red]")
                        await supervisor._handle_stuck_worker(worker, health)
                        nudge_count = supervisor._nudge_counts.get(worker.id, 0)
                        console.print(f"   [yellow]→ Sent nudge #{nudge_count}[/yellow]")
                    elif not health.is_healthy:
                        console.print(f"   [yellow]→ Worker {worker.id[-12:]}: {health.message}[/yellow]")
                
                check_count += 1
                if check_count < 3:
                    console.print(f"   [dim]Waiting {config.check_interval}s for next check...[/dim]\n")
                    await asyncio.sleep(config.check_interval)
        
        await run_checks()
        
        # Check mailboxes for nudge messages
        console.print("\n[9] Checking mailboxes for nudge messages...")
        
        from sgt.storage.mailbox import Mailbox
        
        for worker in workers:
            mailbox = Mailbox(Path(worker.mailbox_path))
            messages = mailbox.read_all()
            
            nudge_messages = [m for m in messages if "nudge" in m.subject.lower()]
            if nudge_messages:
                console.print(f"   Worker {worker.id[-12:]}: {len(nudge_messages)} nudge message(s)")
        
        # Check manager mailbox
        manager_mailbox = Mailbox(demo_dir / "manager" / "mailbox")
        manager_messages = manager_mailbox.read_all()
        
        nudge_notifications = [m for m in manager_messages if "nudge" in m.subject.lower()]
        if nudge_notifications:
            console.print(f"   Manager: {len(nudge_notifications)} nudge notification(s)")
        
        # Final summary
        console.print("\n[10] Final Summary")
        console.print(Panel.fit(
            f"[bold]Supervisor Demo Complete![/bold]\n\n"
            f"• Created 3 workers with different states\n"
            f"• Detected stuck worker (stale heartbeat)\n"
            f"• Sent {supervisor._nudge_counts.get(workers[1].id, 0)} nudge(s) to stuck worker\n"
            f"• Notified manager of issues\n\n"
            f"[dim]The supervisor monitors worker health and takes\n"
            f"action when workers become unresponsive.[/dim]",
            border_style="green"
        ))
        
        console.print("\n[bold green]✓ Phase 4 Demo Complete![/bold green]")
        
    finally:
        # Cleanup
        if demo_dir.exists():
            shutil.rmtree(demo_dir, ignore_errors=True)


def show_cli_usage():
    """Show CLI usage examples."""
    console.print("\n" + "═" * 50)
    console.print("[bold]Supervisor CLI Commands[/bold]\n")
    
    commands = [
        ("sgt supervisor start", "Start supervisor in foreground"),
        ("sgt supervisor start -d", "Start supervisor as daemon"),
        ("sgt supervisor stop", "Stop supervisor"),
        ("sgt supervisor status", "Check supervisor and worker health"),
        ("sgt supervisor health", "One-time health check"),
        ("sgt supervisor health --json", "Health check as JSON"),
        ("sgt supervisor nudge <worker_id>", "Manually nudge a worker"),
    ]
    
    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd}[/cyan]")
        console.print(f"    {desc}\n")


if __name__ == "__main__":
    asyncio.run(demo_supervisor())
    show_cli_usage()
