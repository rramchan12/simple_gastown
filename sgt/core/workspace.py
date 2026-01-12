"""Workspace management."""

from pathlib import Path
from typing import Optional
import shutil

from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class WorkspaceManager:
    """Manages agent workspaces."""
    
    def __init__(self, town_root: Path):
        self.town_root = Path(town_root)
    
    def create_worker_workspace(self, project: str, worker_id: str) -> Path:
        """Create a workspace for a worker."""
        workspace = self.town_root / "projects" / project / "workers" / worker_id
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Create mailbox
        mailbox = workspace / "mailbox"
        mailbox.mkdir(exist_ok=True)
        
        # Create state file placeholder
        state_file = workspace / "state.json"
        if not state_file.exists():
            import json
            with open(state_file, 'w') as f:
                json.dump({"status": "initializing"}, f)
        
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
    
    def cleanup_workspace(self, workspace: Path):
        """Clean up a workspace directory."""
        if workspace.exists():
            shutil.rmtree(workspace)
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
