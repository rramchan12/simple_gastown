"""Worker agent implementation."""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple

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
            
            # 5. Commit any generated files to the worktree branch
            self._commit_generated_files(task)
            
            # 6. Mark task complete
            self.task_manager.complete_task(task.id, result)
            
            # 7. Send completion message to manager
            self._send_completion_message(task.id, result)
            
            # 8. Update state to completed
            self._update_state("completed", task_id=task.id, result=result)
            
            # 9. Clear hook
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
            Summary result with any generated files written to workspace
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
            
            llm_response = str(response)
            
            # Log usage if available
            if response.usage:
                self.logger.info(
                    f"LLM usage - Model: {response.model}, "
                    f"Tokens: {response.usage.get('total_tokens', 'N/A')}"
                )
            
            # Extract code blocks and write to workspace
            written_files = self._write_code_files(llm_response, task.title)
            
            if written_files:
                self.logger.info(f"Wrote {len(written_files)} file(s): {', '.join(written_files)}")
            
            # Create summary result (not the full LLM response)
            result = self._create_result_summary(llm_response, written_files)
            
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
        
        # Get repository context from worktree
        repo_context = self._get_repository_context()
        
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
{repo_context}

## Your Mission

Complete this task thoroughly. Provide working code if applicable, and explain your solution clearly.

Begin now."""
        return prompt
    
    def _get_repository_context(self, max_files: int = 20, max_file_size: int = 8000) -> str:
        """Extract repository context from the worktree for LLM prompt.
        
        Args:
            max_files: Maximum number of files to include
            max_file_size: Maximum size per file in characters
            
        Returns:
            Formatted string with repository structure and key file contents
        """
        worktree_dir = self._find_worktree_dir()
        if not worktree_dir:
            self.logger.warning("No worktree found - LLM will have no repository context")
            return ""
        
        self.logger.info(f"Extracting repository context from {worktree_dir}")
        
        context_parts = ["\n## Repository Contents\n"]
        
        # Find all Python files (excluding __pycache__, .git, etc.)
        python_files = []
        exclude_dirs = {'__pycache__', '.git', '.tox', '.pytest_cache', 'node_modules', 
                       '.eggs', '*.egg-info', 'venv', '.venv', 'env', 'build', 'dist'}
        
        for py_file in worktree_dir.rglob("*.py"):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            python_files.append(py_file)
        
        if not python_files:
            self.logger.warning(f"No Python files found in {worktree_dir}")
            return ""
        
        # Sort by path for consistent ordering
        python_files.sort(key=lambda p: str(p))
        
        # Build file tree
        context_parts.append("### File Structure\n```")
        for py_file in python_files[:max_files * 2]:  # Show more in tree
            rel_path = py_file.relative_to(worktree_dir)
            context_parts.append(str(rel_path))
        if len(python_files) > max_files * 2:
            context_parts.append(f"... and {len(python_files) - max_files * 2} more files")
        context_parts.append("```\n")
        
        # Include file contents for key files
        context_parts.append("### Source Code\n")
        
        files_included = 0
        for py_file in python_files:
            if files_included >= max_files:
                break
            
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Skip very small files (likely __init__.py with just imports)
                if len(content.strip()) < 50:
                    continue
                
                # Truncate large files
                if len(content) > max_file_size:
                    content = content[:max_file_size] + "\n# ... (truncated)"
                
                rel_path = py_file.relative_to(worktree_dir)
                context_parts.append(f"#### {rel_path}\n```python\n{content}\n```\n")
                files_included += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to read {py_file}: {e}")
        
        self.logger.info(f"Included {files_included} files in repository context")
        return '\n'.join(context_parts)
    
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
    
    def _commit_generated_files(self, task: Task) -> None:
        """Commit any generated files to the git worktree branch.
        
        This ensures generated code persists even after worker cleanup.
        """
        import subprocess
        
        # Find the worktree directory
        worktree_dir = self._find_worktree_dir()
        
        if not worktree_dir:
            self.logger.debug("No git worktree found, skipping commit")
            return
        
        try:
            # Check if there are any changes to commit
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=worktree_dir,
                capture_output=True,
                text=True
            )
            
            if not status_result.stdout.strip():
                self.logger.debug("No changes to commit")
                return
            
            # Add all new/modified files
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=worktree_dir,
                capture_output=True,
                check=True
            )
            
            # Commit with task info
            commit_msg = f"[{task.id}] {task.title}\n\nGenerated by worker {self.id}"
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=worktree_dir,
                capture_output=True,
                check=True
            )
            
            self.logger.info(f"Committed generated files to worktree branch")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to commit generated files: {e}")
        except Exception as e:
            self.logger.warning(f"Error committing files: {e}")
    
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
    
    def _extract_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Extract code blocks from markdown-formatted text.
        
        Returns:
            List of (language, code) tuples
        """
        # Match ```language\ncode\n``` blocks
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return [(lang or 'text', code.strip()) for lang, code in matches]
    
    def _infer_filename(self, task_title: str, language: str, code: str) -> Optional[str]:
        """Infer a filename from task title, language, and code content.
        
        Returns:
            Suggested filename or None if can't determine
        """
        # Common language to extension mapping
        ext_map = {
            'python': '.py',
            'py': '.py',
            'javascript': '.js',
            'js': '.js',
            'typescript': '.ts',
            'ts': '.ts',
            'json': '.json',
            'yaml': '.yaml',
            'yml': '.yaml',
            'markdown': '.md',
            'md': '.md',
            'bash': '.sh',
            'shell': '.sh',
        }
        
        ext = ext_map.get(language.lower(), '')
        if not ext:
            return None
        
        # Try to infer name from task title
        title_lower = task_title.lower()
        
        # Check for pytest/test patterns
        if 'test' in title_lower and ext == '.py':
            # Extract what's being tested
            if 'basic' in title_lower or 'arithmetic' in title_lower:
                return 'test_arithmetic.py'
            elif 'advanced' in title_lower:
                return 'test_advanced.py'
            elif 'conftest' in title_lower:
                return 'conftest.py'
            else:
                # Generic test file
                words = re.findall(r'\b\w+\b', title_lower)
                # Remove common words
                skip = {'write', 'test', 'pytest', 'tests', 'for', 'the', 'create', 'add'}
                words = [w for w in words if w not in skip]
                if words:
                    return f"test_{words[0]}.py"
                return 'test_generated.py'
        
        # Check for conftest
        if 'conftest' in title_lower:
            return 'conftest.py'
        
        # Check for README
        if 'readme' in title_lower or 'documentation' in title_lower:
            return 'README.md'
        
        # Check code for class/function names
        if ext == '.py':
            # Look for class TestXxx
            class_match = re.search(r'class\s+(Test\w+)', code)
            if class_match:
                class_name = class_match.group(1)
                # TestArithmetic -> test_arithmetic.py
                name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
                return f"{name}.py"
            
            # Look for def test_xxx
            func_match = re.search(r'def\s+(test_\w+)', code)
            if func_match:
                func_name = func_match.group(1)
                # test_add -> test_functions.py (group by first word after test_)
                parts = func_name.split('_')
                if len(parts) > 1:
                    return f"test_{parts[1]}.py"
        
        return None
    
    def _find_worktree_dir(self) -> Optional[Path]:
        """Find the git worktree directory within the workspace.
        
        Returns:
            Path to worktree directory, or None if not found
        """
        # Check subdirectories for git worktree
        for subdir in self.workspace.iterdir():
            if subdir.is_dir() and (subdir / '.git').exists():
                return subdir
        
        # Check if workspace itself is a worktree
        if (self.workspace / '.git').exists():
            return self.workspace
        
        return None
    
    def _write_code_files(self, text: str, task_title: str) -> List[str]:
        """Extract code blocks and write them to workspace.
        
        Returns:
            List of written filenames
        """
        code_blocks = self._extract_code_blocks(text)
        written_files = []
        used_names = set()
        
        # Find the worktree directory (where files should go)
        worktree_dir = self._find_worktree_dir()
        output_dir = worktree_dir if worktree_dir else self.workspace
        
        for language, code in code_blocks:
            # Skip non-code blocks
            if language.lower() in ('text', 'bash', 'shell', 'output', 'console'):
                continue
            
            # Skip very short code (likely examples, not full files)
            if len(code.strip().split('\n')) < 5:
                continue
            
            filename = self._infer_filename(task_title, language, code)
            if not filename:
                continue
            
            # Handle duplicate names
            base_name = filename
            counter = 1
            while filename in used_names:
                name, ext = os.path.splitext(base_name)
                filename = f"{name}_{counter}{ext}"
                counter += 1
            used_names.add(filename)
            
            # Write to worktree (or workspace if no worktree)
            file_path = output_dir / filename
            try:
                file_path.write_text(code, encoding='utf-8')
                written_files.append(filename)
                self.logger.info(f"Wrote {filename} ({len(code)} bytes)")
            except Exception as e:
                self.logger.error(f"Failed to write {filename}: {e}")
        
        return written_files
    
    def _create_result_summary(self, llm_response: str, written_files: List[str]) -> str:
        """Create a summary result including written files.
        
        Returns:
            Summary string for the result field
        """
        summary_parts = []
        
        if written_files:
            summary_parts.append("## Generated Files\n")
            for f in written_files:
                summary_parts.append(f"- `{f}`")
            summary_parts.append("")
        
        # Extract any summary section from LLM response
        summary_match = re.search(r'###?\s*(?:Summary|Result)[^\n]*\n(.*?)(?=###|\Z)', 
                                   llm_response, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary_parts.append("## Summary\n")
            summary_parts.append(summary_match.group(1).strip())
        else:
            # Just include first few lines as summary
            lines = llm_response.strip().split('\n')[:10]
            summary_parts.append("## Summary\n")
            summary_parts.append('\n'.join(lines))
            if len(llm_response.strip().split('\n')) > 10:
                summary_parts.append("\n...(truncated)")
        
        return '\n'.join(summary_parts)


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
