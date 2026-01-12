"""Worker agent implementation."""

import asyncio
import json
from pathlib import Path
from typing import Optional

from sgt.agents.base import BaseAgent
from sgt.models import Task, AgentStatus
from sgt.storage.hooks import HookManager
from sgt.core.task_manager import TaskManager
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class Worker(BaseAgent):
    """Worker agent that executes tasks."""
    
    def __init__(self, worker_id: str, workspace: Path, town_root: Path, project: str):
        super().__init__(worker_id, workspace)
        self.town_root = Path(town_root)
        self.project = project
        self.hook_manager = HookManager(workspace)
        self.state_file = workspace / "state.json"
        
        # Task manager for the project
        project_path = town_root / "projects" / project
        self.task_manager = TaskManager(project_path)
    
    async def run(self):
        """Main worker loop."""
        try:
            self.logger.info(f"Worker {self.id} starting")
            
            # 1. Load hook to get task assignment
            hook = self.hook_manager.read_hook()
            if not hook:
                self.logger.error("No work assignment found")
                self._update_state("failed", error="No hook found")
                return
            
            self.logger.info(f"Received assignment for task {hook.task_id}")
            
            # 2. Load task details
            task = self.task_manager.get_task(hook.task_id)
            if not task:
                self.logger.error(f"Task {hook.task_id} not found")
                self._update_state("failed", error="Task not found")
                return
            
            # 3. Update state to running
            self._update_state("running", task_id=task.id)
            
            # 4. Execute task
            result = await self.execute_task(task)
            
            # 5. Mark task complete
            self.task_manager.complete_task(task.id, result)
            
            # 6. Send completion message to manager
            self._send_completion_message(task.id, result)
            
            # 7. Update state to completed
            self._update_state("completed", task_id=task.id, result=result)
            
            # 8. Clear hook
            self.hook_manager.clear_hook()
            
            self.logger.info(f"Worker {self.id} completed task {task.id}")
            
        except Exception as e:
            self.logger.error(f"Worker {self.id} failed: {e}")
            self._update_state("failed", error=str(e))
            
            # Try to mark task as failed
            if 'task' in locals():
                self.task_manager.fail_task(task.id, str(e))
    
    async def execute_task(self, task: Task) -> str:
        """Execute the assigned task.
        
        Phase 1: Simulate work with a delay.
        Phase 3: Will integrate with LLM.
        """
        self.logger.info(f"Executing task: {task.title}")
        self.logger.info(f"Description: {task.description}")
        
        # Phase 1: Simulate work
        await asyncio.sleep(2)  # Simulate processing time
        
        result = f"Task '{task.title}' completed (simulated).\n"
        result += f"Description: {task.description}\n"
        result += f"Priority: {task.priority.value}\n"
        result += "Status: Work completed successfully in simulation mode."
        
        self.logger.info("Task execution complete")
        
        return result
        
        # Phase 3 will replace the above with:
        # llm_client = LLMClient()
        # prompt = self._build_prompt(task)
        # result = await llm_client.complete(prompt)
        # return result
    
    def _build_prompt(self, task: Task) -> str:
        """Build an LLM prompt for the task (Phase 3)."""
        prompt = f"""You are a worker agent assigned to complete this task:

Title: {task.title}
Description: {task.description}
Priority: {task.priority.value}

Workspace: {self.workspace}
Project: {self.project}

Please complete the task by:
1. Analyzing the requirements
2. Planning your approach
3. Implementing the solution
4. Testing your work
5. Providing a detailed summary

Execute the task now and provide your results.
"""
        return prompt
    
    def _update_state(self, status: str, task_id: Optional[str] = None,
                     result: Optional[str] = None, error: Optional[str] = None):
        """Update worker state file."""
        from datetime import datetime
        
        state = {
            "worker_id": self.id,
            "status": status,
            "task_id": task_id,
            "updated_at": datetime.utcnow().isoformat(),
            "result": result,
            "error": error
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _send_completion_message(self, task_id: str, result: str):
        """Send completion notification to manager."""
        manager_mailbox = self.town_root / "manager" / "mailbox"
        
        self.send_message(
            to_mailbox=manager_mailbox,
            subject="Task Completed",
            body=f"Worker {self.id} completed task {task_id}",
            metadata={
                "task_id": task_id,
                "result": result,
                "worker_id": self.id
            }
        )
        
        self.logger.info(f"Sent completion message for task {task_id}")


async def run_worker(worker_id: str, workspace: Path, town_root: Path, project: str):
    """Helper function to run a worker."""
    worker = Worker(worker_id, workspace, town_root, project)
    await worker.run()
