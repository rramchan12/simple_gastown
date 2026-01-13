"""Git-related CLI commands."""

import click
from pathlib import Path

from ..core.agent_manager import AgentManager
from ..git.worktree import WorktreeManager


@click.group()
def git():
    """Git worktree management commands."""
    pass


@git.command("worktrees")
@click.option("--repo", "-r", type=click.Path(exists=True), help="Path to git repository")
@click.pass_context
def list_worktrees(ctx, repo):
    """List all git worktrees for a repository."""
    if not repo:
        click.echo("Error: --repo is required", err=True)
        return
    
    repo_path = Path(repo).resolve()
    wt_mgr = WorktreeManager(repo_path)
    
    if not wt_mgr.is_git_repo():
        click.echo(f"Error: {repo_path} is not a git repository", err=True)
        return
    
    worktrees = wt_mgr.list_worktrees()
    
    if not worktrees:
        click.echo("No worktrees found")
        return
    
    click.echo(f"Worktrees for {repo_path}:")
    for wt in worktrees:
        branch = wt.get("branch", "detached")
        commit = wt.get("commit", "unknown")[:8]
        click.echo(f"  {branch}: {wt.get('path')} ({commit})")


@git.command("status")
@click.argument("worker_id")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
def worker_git_status(worker_id, town):
    """Show git status for a worker's worktree."""
    town_root = Path(town).resolve()
    agent_mgr = AgentManager(town_root)
    
    status = agent_mgr.get_work_status(worker_id)
    
    if status is None:
        click.echo(f"Worker {worker_id} not found or has no worktree", err=True)
        return
    
    if not status.strip():
        click.echo("No changes")
        return
    
    click.echo(f"Changes in worker {worker_id}:")
    click.echo(status)


@git.command("commit")
@click.argument("worker_id")
@click.option("--message", "-m", required=True, help="Commit message")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
def commit_worker_work(worker_id, message, town):
    """Commit changes in a worker's worktree."""
    town_root = Path(town).resolve()
    agent_mgr = AgentManager(town_root)
    
    success = agent_mgr.commit_worker_work(worker_id, message)
    
    if success:
        click.echo(f"✓ Committed changes for worker {worker_id}")
    else:
        click.echo(f"Error: Could not commit changes for worker {worker_id}", err=True)


@git.command("init")
@click.argument("path", type=click.Path())
def init_repo(path):
    """Initialize a new git repository."""
    repo_path = Path(path).resolve()
    wt_mgr = WorktreeManager(repo_path)
    
    if wt_mgr.is_git_repo():
        click.echo(f"Repository already exists at {repo_path}")
        return
    
    if wt_mgr.init_repo():
        click.echo(f"✓ Initialized git repository at {repo_path}")
    else:
        click.echo(f"Error: Could not initialize repository", err=True)


@git.command("worktree-path")
@click.argument("worker_id")
@click.option("--town", "-t", type=click.Path(exists=True), default=".", help="Gas Town root directory")
def show_worktree_path(worker_id, town):
    """Show the worktree path for a worker."""
    town_root = Path(town).resolve()
    agent_mgr = AgentManager(town_root)
    
    path = agent_mgr.get_worktree_path(worker_id)
    
    if path:
        click.echo(str(path))
    else:
        click.echo(f"Worker {worker_id} has no worktree", err=True)
