"""Supervisor CLI commands."""

import asyncio
import os
import sys
import signal
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sgt.agents.supervisor import Supervisor, SupervisorConfig, run_supervisor
from sgt.storage.state import StateManager

console = Console()


@click.group()
def supervisor():
    """Supervisor monitoring commands."""
    pass


@supervisor.command("start")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
@click.option("--interval", "-i", default=30, help="Health check interval in seconds")
@click.option("--timeout", default=300, help="Worker timeout in seconds")
@click.option("--nudge-interval", default=60, help="Interval between nudges in seconds")
@click.option("--max-nudges", default=3, help="Max nudges before marking worker as failed")
@click.option("--daemon", "-d", is_flag=True, help="Run as background daemon")
@click.option("--auto-restart", is_flag=True, help="Auto-restart failed workers")
def start_supervisor(town, interval, timeout, nudge_interval, max_nudges, daemon, auto_restart):
    """Start the supervisor agent."""
    town_path = Path(town).resolve()
    
    # Check if already running
    if Supervisor.is_running(town_path):
        pid = Supervisor.get_running_pid(town_path)
        console.print(f"[yellow]Supervisor already running (PID: {pid})[/yellow]")
        return
    
    config = SupervisorConfig(
        check_interval=interval,
        worker_timeout=timeout,
        nudge_interval=nudge_interval,
        max_nudges=max_nudges,
        auto_restart=auto_restart,
    )
    
    console.print(Panel.fit(
        f"[cyan]Starting Supervisor[/cyan]\n"
        f"Check interval: {interval}s\n"
        f"Worker timeout: {timeout}s\n"
        f"Max nudges: {max_nudges}",
        border_style="cyan"
    ))
    
    if daemon:
        # Run in background
        _start_daemon(town_path, config)
    else:
        # Run in foreground
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            asyncio.run(run_supervisor(town_path, config))
        except KeyboardInterrupt:
            console.print("\n[yellow]Supervisor stopped by user[/yellow]")


def _start_daemon(town_path: Path, config: SupervisorConfig):
    """Start supervisor as a background daemon process."""
    import subprocess
    
    # Build command to run supervisor
    cmd = [
        sys.executable, "-m", "sgt", "supervisor", "start",
        "--town", str(town_path),
        "--interval", str(config.check_interval),
        "--timeout", str(config.worker_timeout),
        "--nudge-interval", str(config.nudge_interval),
        "--max-nudges", str(config.max_nudges),
    ]
    
    if config.auto_restart:
        cmd.append("--auto-restart")
    
    # Start process in background
    if os.name == 'nt':
        # Windows
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        
        process = subprocess.Popen(
            cmd,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # Unix
        process = subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    
    console.print(f"[green]✓[/green] Supervisor started in background (PID: {process.pid})")
    console.print("[dim]Use 'sgt supervisor status' to check status[/dim]")
    console.print("[dim]Use 'sgt supervisor stop' to stop[/dim]")


@supervisor.command("stop")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
@click.option("--force", "-f", is_flag=True, help="Force kill if graceful stop fails")
def stop_supervisor(town, force):
    """Stop the supervisor agent."""
    town_path = Path(town).resolve()
    
    if not Supervisor.is_running(town_path):
        console.print("[yellow]Supervisor is not running[/yellow]")
        return
    
    pid = Supervisor.get_running_pid(town_path)
    
    if not pid:
        console.print("[yellow]Could not determine supervisor PID[/yellow]")
        return
    
    try:
        # Send SIGTERM for graceful shutdown
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, pid)  # PROCESS_TERMINATE
            if handle:
                kernel32.TerminateProcess(handle, 0)
                kernel32.CloseHandle(handle)
        else:
            os.kill(pid, signal.SIGTERM)
        
        console.print(f"[green]✓[/green] Sent stop signal to supervisor (PID: {pid})")
        
        # Wait briefly and check if stopped
        import time
        time.sleep(1)
        
        if not Supervisor.is_running(town_path):
            console.print("[green]✓[/green] Supervisor stopped successfully")
        elif force:
            # Force kill
            if os.name != 'nt':
                os.kill(pid, signal.SIGKILL)
            console.print("[yellow]Force killed supervisor[/yellow]")
        else:
            console.print("[yellow]Supervisor still running, use --force to kill[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error stopping supervisor:[/red] {e}")
        
        # Clean up stale PID file
        pid_file = town_path / "supervisor" / "supervisor.pid"
        if pid_file.exists():
            pid_file.unlink()
            console.print("[dim]Cleaned up stale PID file[/dim]")


@supervisor.command("status")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
def supervisor_status(town):
    """Check supervisor and worker health status."""
    town_path = Path(town).resolve()
    
    # Check if supervisor is running
    is_running = Supervisor.is_running(town_path)
    pid = Supervisor.get_running_pid(town_path)
    
    console.print(Panel.fit(
        f"[bold]Supervisor Status[/bold]\n\n"
        f"Running: {'[green]Yes[/green]' if is_running else '[red]No[/red]'}\n"
        f"PID: {pid or 'N/A'}",
        border_style="cyan" if is_running else "red"
    ))
    
    # Show supervisor state if available
    state_file = town_path / "supervisor" / "state.json"
    if state_file.exists():
        import json
        with open(state_file) as f:
            state = json.load(f)
        
        console.print(f"\n[dim]Started: {state.get('started_at', 'Unknown')}[/dim]")
        console.print(f"[dim]Config: interval={state.get('config', {}).get('check_interval', '?')}s, timeout={state.get('config', {}).get('worker_timeout', '?')}s[/dim]")
    
    # Show worker health
    console.print("\n[bold]Worker Health[/bold]\n")
    
    sup = Supervisor(town_path)
    health_list = sup.get_all_worker_health()
    
    if not health_list:
        console.print("[dim]No active workers[/dim]")
        return
    
    table = Table()
    table.add_column("Worker", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Task", style="magenta")
    table.add_column("Last Heartbeat", style="dim")
    table.add_column("Health", style="green")
    
    for health in health_list:
        # Determine health indicator
        if health.is_healthy:
            health_str = "[green]✓ OK[/green]"
        elif health.is_stuck:
            health_str = f"[red]✗ Stuck ({health.nudge_count} nudges)[/red]"
        else:
            health_str = f"[yellow]⚠ {health.message}[/yellow]"
        
        table.add_row(
            health.worker_id[-12:],
            health.status.value,
            health.task_id[-12:] if health.task_id else "-",
            f"{int(health.seconds_since_heartbeat)}s ago",
            health_str,
        )
    
    console.print(table)
    
    # Summary
    summary = sup.get_summary()
    console.print(f"\n[dim]Total: {summary['total_workers']} | Healthy: {summary['healthy']} | Stuck: {summary['stuck']} | Failed: {summary['failed']}[/dim]")


@supervisor.command("health")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def health_check(town, as_json):
    """Perform a one-time health check on all workers."""
    town_path = Path(town).resolve()
    
    sup = Supervisor(town_path)
    health_list = sup.get_all_worker_health()
    summary = sup.get_summary()
    
    if as_json:
        import json
        output = {
            "summary": summary,
            "workers": [
                {
                    "worker_id": h.worker_id,
                    "status": h.status.value,
                    "task_id": h.task_id,
                    "seconds_since_heartbeat": h.seconds_since_heartbeat,
                    "is_healthy": h.is_healthy,
                    "is_stuck": h.is_stuck,
                    "nudge_count": h.nudge_count,
                    "message": h.message,
                }
                for h in health_list
            ]
        }
        click.echo(json.dumps(output, indent=2))
    else:
        console.print(Panel.fit(
            f"[bold]Health Check Summary[/bold]\n\n"
            f"Total Workers: {summary['total_workers']}\n"
            f"Healthy: [green]{summary['healthy']}[/green]\n"
            f"Stuck: [red]{summary['stuck']}[/red]\n"
            f"Failed: [red]{summary['failed']}[/red]",
            border_style="green" if summary['stuck'] == 0 and summary['failed'] == 0 else "yellow"
        ))


@supervisor.command("nudge")
@click.argument("worker_id")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
def nudge_worker(worker_id, town):
    """Manually nudge a worker."""
    town_path = Path(town).resolve()
    
    state_manager = StateManager(town_path)
    worker = state_manager.get_agent(worker_id)
    
    if not worker:
        # Try partial match
        all_agents = state_manager.list_agents(agent_type="worker")
        matches = [a for a in all_agents if worker_id in a.id]
        
        if len(matches) == 1:
            worker = matches[0]
        elif len(matches) > 1:
            console.print(f"[red]Multiple workers match '{worker_id}':[/red]")
            for m in matches:
                console.print(f"  - {m.id}")
            return
        else:
            console.print(f"[red]Worker {worker_id} not found[/red]")
            return
    
    # Send nudge
    from sgt.storage.mailbox import send_message
    
    mailbox_path = Path(worker.mailbox_path)
    send_message(
        from_agent="manager",
        to_mailbox=mailbox_path,
        subject="Manual Nudge",
        body="You have been nudged by the manager. Please report your status.",
        metadata={
            "type": "manual_nudge",
            "task_id": worker.task_id,
        }
    )
    
    console.print(f"[green]✓[/green] Nudged worker {worker.id}")
