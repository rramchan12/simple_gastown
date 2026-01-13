"""Agent lifecycle management."""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from sgt.models import AgentState, AgentType, AgentStatus, TaskPriority
from sgt.storage.state import StateManager
from sgt.storage.hooks import HookManager
from sgt.storage.mailbox import send_message
from sgt.core.workspace import WorkspaceManager
from sgt.utils.ids import generate_worker_id
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentManager:
    """Manages agent lifecycle and state."""
    
    def __init__(self, town_root: Path):
        self.town_root = Path(town_root)
        self.state_manager = StateManager(town_root)
        self.workspace_manager = WorkspaceManager(town_root)
    
    def spawn_worker(self, project: str, task_id: str,
                    instructions: Optional[str] = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    repo_path: Optional[Path] = None,
                    use_worktree: bool = False) -> AgentState:
        """Spawn a new worker for a task.
        
        Args:
            project: Project name
            task_id: Task ID to assign
            instructions: Optional instructions for the worker
            priority: Task priority
            repo_path: Optional path to git repository for worktree mode
            use_worktree: If True and repo_path provided, create isolated worktree
        """
        # Generate worker ID
        worker_id = generate_worker_id()
        
        # Create workspace (with optional worktree)
        workspace = self.workspace_manager.create_worker_workspace(
            project, 
            worker_id,
            repo_path=repo_path,
            use_worktree=use_worktree
        )
        
        # Write worker instructions
        self.workspace_manager.write_worker_instructions(workspace, task_id, project)
        
        # Create hook with task assignment
        hook_manager = HookManager(workspace)
        hook_manager.create_hook(
            task_id=task_id,
            assigned_by="manager",
            instructions=instructions,
            priority=priority
        )
        
        # Create agent state
        agent = AgentState(
            id=worker_id,
            type=AgentType.WORKER,
            status=AgentStatus.IDLE,
            project=project,
            task_id=task_id,
            workspace=str(workspace),
            mailbox_path=str(workspace / "mailbox")
        )
        
        # Save to state
        self.state_manager.add_agent(agent)
        
        # Send mailbox message
        mailbox_path = workspace / "mailbox"
        send_message(
            from_agent="manager",
            to_mailbox=mailbox_path,
            subject="Work Assignment",
            body=f"You have been assigned to work on task {task_id}",
            metadata={
                "task_id": task_id,
                "priority": priority.value
            }
        )
        
        logger.info(f"Spawned worker {worker_id} for task {task_id}")
        
        # TODO Phase 1: In Phase 1, we don't actually start the worker process
        # The worker will be started manually or in Phase 2
        # For now, we just create the workspace and state
        
        return agent
    
    def kill_worker(self, worker_id: str, force: bool = False, 
                   commit_message: Optional[str] = None):
        """Terminate a worker and clean up.
        
        Args:
            worker_id: Worker ID to terminate
            force: If True, force cleanup even with uncommitted changes
            commit_message: If provided, commit work before cleanup
        """
        agent = self.state_manager.get_agent(worker_id)
        if not agent:
            logger.warning(f"Worker {worker_id} not found")
            return
        
        workspace = Path(agent.workspace)
        
        # Optionally commit work before cleanup
        if commit_message:
            self.workspace_manager.commit_work(workspace, commit_message)
        
        # Clean up workspace (handles worktree removal)
        self.workspace_manager.cleanup_workspace(workspace)
        
        # Remove from state
        self.state_manager.remove_agent(worker_id)
        
        logger.info(f"Killed worker {worker_id}")
    
    def list_workers(self, project: Optional[str] = None) -> List[AgentState]:
        """List all workers, optionally filtered by project."""
        workers = self.state_manager.list_agents(agent_type=AgentType.WORKER.value)
        
        if project:
            workers = [w for w in workers if w.project == project]
        
        return workers
    
    def get_worker(self, worker_id: str) -> Optional[AgentState]:
        """Get a worker by ID."""
        agent = self.state_manager.get_agent(worker_id)
        if agent and agent.type == AgentType.WORKER:
            return agent
        return None
    
    def update_worker_status(self, worker_id: str, status: AgentStatus):
        """Update a worker's status."""
        agent = self.get_worker(worker_id)
        if not agent:
            return
        
        agent.status = status
        agent.last_heartbeat = datetime.utcnow()
        
        self.state_manager.add_agent(agent)
        
        logger.info(f"Updated worker {worker_id} status to {status.value}")
    
    def update_heartbeat(self, worker_id: str):
        """Update worker's heartbeat timestamp."""
        self.state_manager.update_agent_heartbeat(worker_id)
    
    def create_manager(self) -> AgentState:
        """Create the manager agent."""
        workspace = self.workspace_manager.create_manager_workspace()
        
        agent = AgentState(
            id="manager",
            type=AgentType.MANAGER,
            status=AgentStatus.IDLE,
            workspace=str(workspace),
            mailbox_path=str(workspace / "mailbox")
        )
        
        self.state_manager.add_agent(agent)
        
        logger.info("Created manager agent")
        
        return agent
    
    def get_manager(self) -> Optional[AgentState]:
        """Get the manager agent."""
        return self.state_manager.get_agent("manager")
    
    def get_work_status(self, worker_id: str) -> Optional[str]:
        """Get git status for a worker's worktree."""
        agent = self.get_worker(worker_id)
        if not agent:
            return None
        
        workspace = Path(agent.workspace)
        return self.workspace_manager.get_work_status(workspace)
    
    def commit_worker_work(self, worker_id: str, message: str) -> bool:
        """Commit changes in a worker's worktree."""
        agent = self.get_worker(worker_id)
        if not agent:
            return False
        
        workspace = Path(agent.workspace)
        return self.workspace_manager.commit_work(workspace, message)
    
    def get_worktree_path(self, worker_id: str) -> Optional[Path]:
        """Get the worktree path for a worker."""
        agent = self.get_worker(worker_id)
        if not agent:
            return None
        
        workspace = Path(agent.workspace)
        return self.workspace_manager.get_worktree_path(workspace)
