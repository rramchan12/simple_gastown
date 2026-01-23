"""Workspace management."""

from pathlib import Path
from typing import Optional
import shutil
import json

from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkspaceManager:
    """Manages agent workspaces."""
    
    def __init__(self, town_root: Path):
        self.town_root = Path(town_root)
    
    def create_worker_workspace(
        self, 
        project: str, 
        worker_id: str,
        repo_path: Optional[Path] = None,
        use_worktree: bool = False
    ) -> Path:
        """Create a workspace for a worker.
        
        Args:
            project: Project name
            worker_id: Worker ID
            repo_path: Optional path to git repository for worktree creation
            use_worktree: If True and repo_path provided, create a git worktree
            
        Returns:
            Path to the created workspace
        """
        workspace = self.town_root / "projects" / project / "workers" / worker_id
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Create mailbox
        mailbox = workspace / "mailbox"
        mailbox.mkdir(exist_ok=True)
        
        # Create state file placeholder
        state_file = workspace / "state.json"
        if not state_file.exists():
            with open(state_file, 'w') as f:
                json.dump({"status": "initializing"}, f)
        
        # Create git worktree if requested
        worktree_path = None
        if use_worktree and repo_path:
            worktree_path = self._create_worktree(workspace, repo_path, worker_id)
        
        logger.info(f"Created workspace for {worker_id} at {workspace}")
        
        return workspace
    
    def _create_worktree(self, workspace: Path, repo_path: Path, worker_id: str) -> Optional[Path]:
        """Create a git worktree in the workspace.
        
        Args:
            workspace: Worker's workspace directory
            repo_path: Path to the main git repository
            worker_id: Worker ID (used for branch name)
            
        Returns:
            Path to the worktree or None if creation failed
        """
        from sgt.git.worktree import WorktreeManager
        
        wt_mgr = WorktreeManager(repo_path)
        
        if not wt_mgr.is_git_repo():
            logger.warning(f"Not a git repository: {repo_path}")
            return None
        
        # Create worktree in workspace with worker's branch
        branch_name = f"worker-{worker_id}"
        worktree_path = workspace / repo_path.name
        
        if wt_mgr.create_worktree(worktree_path, branch_name, create_branch=True):
            # Store worktree info in workspace
            self._write_worktree_info(workspace, repo_path, worktree_path, branch_name)
            logger.info(f"Created worktree at {worktree_path} on branch {branch_name}")
            return worktree_path
        else:
            logger.error(f"Failed to create worktree for {worker_id}")
            return None
    
    def _write_worktree_info(self, workspace: Path, repo_path: Path, 
                            worktree_path: Path, branch: str):
        """Store worktree information in workspace."""
        info = {
            "repo_path": str(repo_path),
            "worktree_path": str(worktree_path),
            "branch": branch
        }
        info_file = workspace / "worktree.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
    
    def _read_worktree_info(self, workspace: Path) -> Optional[dict]:
        """Read worktree information from workspace."""
        info_file = workspace / "worktree.json"
        if info_file.exists():
            with open(info_file) as f:
                return json.load(f)
        return None
    
    def get_worktree_path(self, workspace: Path) -> Optional[Path]:
        """Get the worktree path for a workspace."""
        info = self._read_worktree_info(workspace)
        if info and "worktree_path" in info:
            return Path(info["worktree_path"])
        return None
    
    def commit_work(self, workspace: Path, message: str) -> bool:
        """Commit changes in a worker's worktree.
        
        Args:
            workspace: Worker's workspace directory
            message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        info = self._read_worktree_info(workspace)
        if not info:
            return False
        
        from sgt.git.worktree import WorktreeManager
        
        repo_path = Path(info["repo_path"])
        worktree_path = Path(info["worktree_path"])
        
        wt_mgr = WorktreeManager(repo_path)
        return wt_mgr.commit_changes(message, path=worktree_path)
    
    def get_work_status(self, workspace: Path) -> Optional[str]:
        """Get git status for a worker's worktree.
        
        Args:
            workspace: Worker's workspace directory
            
        Returns:
            Git status output or None if no worktree
        """
        info = self._read_worktree_info(workspace)
        if not info:
            return None
        
        from sgt.git.worktree import WorktreeManager
        
        repo_path = Path(info["repo_path"])
        worktree_path = Path(info["worktree_path"])
        
        wt_mgr = WorktreeManager(repo_path)
        return wt_mgr.get_status(path=worktree_path)
        
        logger.info(f"Created workspace for {worker_id} at {workspace}")
        
        return workspace
    
    def create_manager_workspace(self) -> Path:
        """Create the manager workspace."""
        workspace = self.town_root / "manager"
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Create mailbox
        mailbox = workspace / "mailbox"
        mailbox.mkdir(exist_ok=True)
        
        # Create INSTRUCTIONS.md
        instructions_file = workspace / "INSTRUCTIONS.md"
        if not instructions_file.exists():
            self._write_manager_instructions(instructions_file)
        
        logger.info(f"Created manager workspace at {workspace}")
        
        return workspace
    
    def cleanup_workspace(self, workspace: Path, preserve_worktree: bool = False):
        """Clean up a workspace directory.
        
        Args:
            workspace: Path to the workspace directory
            preserve_worktree: If True, keep the git worktree (only remove workspace metadata)
        """
        # First, remove any git worktree (unless preserving)
        info = self._read_worktree_info(workspace)
        if info and not preserve_worktree:
            from sgt.git.worktree import WorktreeManager
            
            repo_path = Path(info["repo_path"])
            worktree_path = Path(info["worktree_path"])
            
            wt_mgr = WorktreeManager(repo_path)
            wt_mgr.remove_worktree(worktree_path, force=True)
        
        # Then remove the workspace directory
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
            logger.info(f"Cleaned up workspace at {workspace}")
    
    def _write_manager_instructions(self, instructions_file: Path):
        """Write manager instructions."""
        content = """# Manager Agent Instructions

You are the Manager agent in Simple Gas Town.

## Your Role

You coordinate work across the system by:
1. Creating tasks based on requirements
2. Spawning workers to execute tasks
3. Monitoring worker progress
4. Tracking task completion

## Available Operations

- Create tasks with clear descriptions
- Assign tasks to workers
- Check worker status and logs
- Review completed work
- Organize tasks into convoys (batches)

## Working with Workers

When you assign work:
1. Workers are spawned automatically
2. They receive their assignment via mailbox
3. They work independently in isolated workspaces
4. They report completion and self-terminate
5. You receive completion notifications

## Your Workspace

- Location: manager/
- Mailbox: manager/mailbox/
- All communication happens via JSON messages

Stay organized and track all work carefully.
"""
        with open(instructions_file, 'w') as f:
            f.write(content)
    
    def write_worker_instructions(self, workspace: Path, task_id: str, 
                                 project: str):
        """Write worker instructions."""
        instructions_file = workspace / "INSTRUCTIONS.md"
        
        content = f"""# Worker Agent Instructions

You are an autonomous worker agent in Simple Gas Town.

## Your Assignment

- Task ID: {task_id}
- Project: {project}
- Workspace: {workspace}

## Your Role

Execute the task assigned to you:
1. Read your task assignment from hook.json
2. Understand the requirements fully
3. Complete the task correctly and thoroughly
4. Report your results
5. Self-terminate when done

## Task Execution Process

1. **Understand** - Read the task description and requirements
2. **Plan** - Break down the work into steps
3. **Implement** - Make necessary changes (Phase 1: simulate)
4. **Verify** - Check that your work is correct
5. **Document** - Write a clear summary of what you did

## Important Rules

- Work ONLY in your workspace directory
- Do NOT modify files outside your workspace
- Do NOT start other workers or agents
- Complete your task fully before reporting
- If blocked, report the blocker in your results

## On Completion

When finished:
1. Write a clear result summary
2. Mark the task as complete
3. Send completion message to manager
4. Exit (self-destruct)

Your work is permanent. Execute with care and precision.
"""
        with open(instructions_file, 'w') as f:
            f.write(content)
