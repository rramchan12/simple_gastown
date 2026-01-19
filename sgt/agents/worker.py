"""Worker agent implementation."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from sgt.agents.base import BaseAgent
from sgt.models import Task, AgentStatus
from sgt.storage.hooks import HookManager
from sgt.core.task_manager import TaskManager
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)

# Default system prompt for workers
DEFAULT_WORKER_SYSTEM_PROMPT = """You are a skilled software developer working as an autonomous worker agent in Simple Gas Town.

Your job is to complete programming tasks assigned to you. You work methodically and produce high-quality code.

## Guidelines

1. **Understand First**: Read the task description carefully before starting
2. **Plan Your Approach**: Break down complex tasks into smaller steps
3. **Write Clean Code**: Follow best practices for the language/framework
4. **Be Thorough**: Complete the entire task, not just parts of it
5. **Explain Your Work**: Provide a clear summary of what you did

## Output Format

Provide your response in this format:

### Analysis
Brief analysis of the task requirements.

### Implementation
The code or solution you created. Use proper code blocks with language tags.

### Summary
What you accomplished and any notes for the user.

Remember: Your output will be stored as the task result. Be concise but complete."""


class Worker(BaseAgent):
    """Worker agent that executes tasks."""
    
    def __init__(
        self, 
        worker_id: str, 
        workspace: Path, 
        town_root: Path, 
        project: str,
        use_llm: bool = True,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        heartbeat_interval: int = 30,
    ):
        super().__init__(worker_id, workspace)
        self.town_root = Path(town_root)
        self.project = project
        self.hook_manager = HookManager(workspace)
        self.state_file = workspace / "state.json"
        
        # LLM configuration
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self._llm_client = None
        
        # Heartbeat configuration
        self.heartbeat_interval = heartbeat_interval
        self._heartbeat_task = None
        self._stop_heartbeat = False
        
        # Task manager for the project
        project_path = town_root / "projects" / project
        self.task_manager = TaskManager(project_path)
    
    async def run(self):
        """Main worker loop."""
        try:
            self.logger.info(f"Worker {self.id} starting")
            
            # Start heartbeat
            self._start_heartbeat()
            
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
            
            # 3. Update state to running and send heartbeat
            self._update_state("running", task_id=task.id)
            self._send_heartbeat()
            
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
        finally:
            # Stop heartbeat
            self._stop_heartbeat_loop()
    
    async def execute_task(self, task: Task) -> str:
        """Execute the assigned task.
        
        Uses LLM if available and enabled, otherwise falls back to simulation.
        """
        self.logger.info(f"Executing task: {task.title}")
        self.logger.info(f"Description: {task.description}")
        
        # Try to use LLM if enabled
        if self.use_llm:
            try:
                result = await self._execute_with_llm(task)
                self.logger.info("Task execution complete (LLM)")
                return result
            except Exception as e:
                self.logger.warning(f"LLM execution failed: {e}, falling back to simulation")
        
        # Fallback: Simulate work
        self.logger.info("Using simulation mode")
        await asyncio.sleep(2)  # Simulate processing time
        
        result = f"Task '{task.title}' completed (simulated).\n"
        result += f"Description: {task.description}\n"
        result += f"Priority: {task.priority.value}\n"
        result += "Status: Work completed successfully in simulation mode."
        
        self.logger.info("Task execution complete (simulated)")
        return result
    
    async def _execute_with_llm(self, task: Task) -> str:
        """Execute task using LLM integration.
        
        Args:
            task: The task to execute
            
        Returns:
            LLM-generated result
        """
        from sgt.llm.factory import create_llm_client, auto_detect_provider
        
        # Determine provider
        provider = self.llm_provider
        if not provider:
            provider = auto_detect_provider()
            if not provider:
                raise ValueError("No LLM provider configured or detected")
        
        self.logger.info(f"Using LLM provider: {provider}")
        
        # Create client
        client_kwargs = {}
        if self.llm_model:
            client_kwargs["model"] = self.llm_model
        
        client = create_llm_client(provider=provider, **client_kwargs)
        
        try:
            # Build prompts
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_task_prompt(task)
            
            self.logger.info("Sending task to LLM...")
            
            # Get completion
            response = await client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            
            result = str(response)
            
            # Log usage if available
            if response.usage:
                self.logger.info(
                    f"LLM usage - Model: {response.model}, "
                    f"Tokens: {response.usage.get('total_tokens', 'N/A')}"
                )
            
            return result
            
        finally:
            await client.close()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the worker.
        
        Checks for INSTRUCTIONS.md in workspace, falls back to default.
        """
        instructions_file = self.workspace / "INSTRUCTIONS.md"
        
        if instructions_file.exists():
            try:
                return instructions_file.read_text()
            except Exception:
                pass
        
        return DEFAULT_WORKER_SYSTEM_PROMPT
    
    def _build_task_prompt(self, task: Task) -> str:
        """Build the user prompt for the LLM with task details."""
        # Load hook for any additional instructions
        hook = self.hook_manager.read_hook()
        extra_instructions = ""
        if hook and hook.instructions:
            extra_instructions = f"\n\n## Additional Instructions\n{hook.instructions}"
        
        prompt = f"""## Task Assignment

**Task ID:** {task.id}
**Title:** {task.title}
**Priority:** {task.priority.value}

## Description

{task.description}

## Context

- **Project:** {self.project}
- **Workspace:** {self.workspace}
- **Worker ID:** {self.id}
{extra_instructions}

## Your Mission

Complete this task thoroughly. Provide working code if applicable, and explain your solution clearly.

Begin now."""
        return prompt
    
    def _build_prompt(self, task: Task) -> str:
        """Build an LLM prompt for the task (legacy method)."""
        return self._build_task_prompt(task)
    
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
    
    # Heartbeat methods
    
    def _start_heartbeat(self):
        """Start the heartbeat background task."""
        self._stop_heartbeat = False
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.logger.debug("Heartbeat started")
    
    def _stop_heartbeat_loop(self):
        """Stop the heartbeat background task."""
        self._stop_heartbeat = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                # We don't await here since this is called from finally
                pass
            except:
                pass
        self.logger.debug("Heartbeat stopped")
    
    async def _heartbeat_loop(self):
        """Background task that sends periodic heartbeats."""
        try:
            while not self._stop_heartbeat:
                await asyncio.sleep(self.heartbeat_interval)
                if not self._stop_heartbeat:
                    self._send_heartbeat()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}")
    
    def _send_heartbeat(self):
        """Send a heartbeat to update last_heartbeat timestamp."""
        try:
            from sgt.storage.state import StateManager
            
            state_manager = StateManager(self.town_root)
            state_manager.update_agent_heartbeat(self.id)
            
            self.logger.debug(f"Heartbeat sent for worker {self.id}")
        except Exception as e:
            self.logger.warning(f"Failed to send heartbeat: {e}")


async def run_worker(
    worker_id: str, 
    workspace: Path, 
    town_root: Path, 
    project: str,
    use_llm: bool = True,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
):
    """Helper function to run a worker."""
    worker = Worker(
        worker_id, 
        workspace, 
        town_root, 
        project,
        use_llm=use_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    await worker.run()
