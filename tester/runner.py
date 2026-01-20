"""
Test Runner - Core execution engine for the tester module.
"""
import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Optional, Union

from .config import TestConfig, LLMConfig


class TestRunner:
    """
    Executes test generation tasks using Simple Gas Town agents.
    
    The runner:
    1. Loads configuration from external files
    2. Sets up the Gas Town workspace
    3. Spawns workers with git worktrees for isolation
    4. Runs tasks through LLM-powered agents
    5. Collects and reports results
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self._llm_provider: Optional[str] = None
        self._llm_model: Optional[str] = None
        self._use_llm: bool = False
        
    @classmethod
    def from_config(cls, path: Union[str, Path]) -> "TestRunner":
        """Create a runner from a configuration file."""
        path = Path(path)
        
        if path.suffix in ('.yaml', '.yml'):
            config = TestConfig.from_yaml(path)
        elif path.suffix == '.json':
            config = TestConfig.from_json(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        
        return cls(config)
    
    def _detect_llm(self) -> None:
        """Detect available LLM provider from environment or config."""
        # Use explicit config if provided
        if self.config.llm.provider:
            self._llm_provider = self.config.llm.provider
            self._llm_model = self.config.llm.model
            self._use_llm = True
            return
        
        # Auto-detect from environment
        if os.environ.get('GITHUB_TOKEN'):
            self._llm_provider = 'github'
            self._llm_model = self.config.llm.model or 'gpt-4o-mini'
            self._use_llm = True
        elif os.environ.get('OPENAI_API_KEY'):
            self._llm_provider = 'openai'
            self._llm_model = self.config.llm.model or 'gpt-4o-mini'
            self._use_llm = True
        elif os.environ.get('ANTHROPIC_API_KEY'):
            self._llm_provider = 'anthropic'
            self._llm_model = self.config.llm.model or 'claude-3-haiku-20240307'
            self._use_llm = True
        else:
            self._use_llm = False
    
    def _cleanup_workspace(self) -> None:
        """Clean up previous workspace if it exists."""
        town_root = self.config.town_root
        repo_path = self.config.repo_path
        
        if not town_root.exists():
            return
        
        # Prune any orphaned worktrees first
        if repo_path.exists():
            try:
                import subprocess
                subprocess.run(
                    "git worktree prune",
                    shell=True,
                    cwd=repo_path,
                    capture_output=True
                )
            except Exception:
                pass
        
        # Retry cleanup for Windows file locks
        for _ in range(3):
            try:
                shutil.rmtree(town_root, ignore_errors=False)
                break
            except Exception:
                time.sleep(0.5)
                shutil.rmtree(town_root, ignore_errors=True)
    
    def _setup_workspace(self) -> tuple:
        """Set up the Gas Town workspace. Returns (workspace_manager, state_manager, agent_manager)."""
        from sgt.core.workspace import WorkspaceManager
        from sgt.core.agent_manager import AgentManager
        from sgt.storage.state import StateManager
        
        town_root = self.config.town_root
        
        # Create directory structure
        town_root.mkdir(parents=True, exist_ok=True)
        (town_root / ".gastown").mkdir(exist_ok=True)
        (town_root / "state").mkdir(exist_ok=True)
        (town_root / "projects").mkdir(exist_ok=True)
        
        # Initialize managers
        workspace_manager = WorkspaceManager(town_root)
        workspace_manager.create_manager_workspace()
        
        state_manager = StateManager(town_root)
        agent_manager = AgentManager(town_root)
        agent_manager.create_manager()
        
        return workspace_manager, state_manager, agent_manager
    
    def _setup_project(self) -> Path:
        """Create project directory structure. Returns project path."""
        project_path = self.config.town_root / "projects" / self.config.name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / ".tasks").mkdir(exist_ok=True)
        (project_path / "settings").mkdir(exist_ok=True)
        return project_path
    
    async def run(self, verbose: bool = True) -> dict:
        """
        Run the test generation workflow.
        
        Args:
            verbose: Print progress messages
            
        Returns:
            Dictionary with run results
        """
        from sgt.core.task_manager import TaskManager
        from sgt.core.convoy_manager import ConvoyManager
        from sgt.agents.worker import run_worker
        from sgt.git.worktree import WorktreeManager
        
        results = {
            "tasks": [],
            "completed": 0,
            "failed": 0,
            "worktrees": []
        }
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {errors}")
        
        # Detect LLM
        self._detect_llm()
        
        if verbose:
            print("=" * 60)
            print(f"🧪 Test Runner: {self.config.name}")
            print("=" * 60)
            
            if self._use_llm:
                print(f"✅ LLM: {self._llm_provider} / {self._llm_model}")
            else:
                print("⚠️  No LLM available - running in simulation mode")
            
            print(f"📂 Repository: {self.config.repo_path}")
            print(f"📁 Town root: {self.config.town_root}")
            print()
        
        # Cleanup if requested
        if self.config.cleanup_on_start:
            if verbose:
                print("🗑️  Cleaning up previous workspace...")
            self._cleanup_workspace()
        
        # Setup workspace
        if verbose:
            print("📁 Setting up workspace...")
        _, state_manager, agent_manager = self._setup_workspace()
        project_path = self._setup_project()
        
        # Create tasks
        tm = TaskManager(project_path)
        cm = ConvoyManager(state_manager, tm)
        
        if verbose:
            print("\n📋 Creating tasks...")
        
        task_ids = []
        for task_config in self.config.tasks:
            task = tm.create_task(
                title=task_config.title,
                description=task_config.description,
                priority=task_config.priority
            )
            task_ids.append(task.id)
            if verbose:
                print(f"   ✓ {task.title}")
        
        # Create convoy
        convoy = cm.create_convoy(
            name=self.config.convoy_name,
            task_ids=task_ids
        )
        
        if verbose:
            print(f"\n🚚 Created convoy: {convoy.name} ({convoy.id})")
            print("\n" + "=" * 60)
            print("🏃 Running Workers...")
            print("=" * 60)
        
        # Run workers
        tasks = tm.list_tasks()
        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"\n[{i}/{len(tasks)}] 🔧 {task.title}")
                print("-" * 50)
            
            # Spawn worker
            if self.config.use_worktrees:
                worker = agent_manager.spawn_worker(
                    project=self.config.name,
                    task_id=task.id,
                    repo_path=self.config.repo_path,
                    use_worktree=True
                )
                worktree_path = agent_manager.get_worktree_path(worker.id)
                if worktree_path:
                    results["worktrees"].append({
                        "worker": worker.id,
                        "path": str(worktree_path),
                        "branch": f"worker-{worker.id}"
                    })
                    if verbose:
                        print(f"   Worktree: {worktree_path}")
            else:
                worker = agent_manager.spawn_worker(
                    project=self.config.name,
                    task_id=task.id
                )
            
            if verbose:
                print(f"   Worker: {worker.id[-12:]}")
            
            # Assign and run task
            tm.assign_task(task.id, worker.id)
            workspace = Path(worker.workspace)
            
            await run_worker(
                worker.id, 
                workspace, 
                self.config.town_root, 
                self.config.name,
                use_llm=self._use_llm,
                llm_provider=self._llm_provider,
                llm_model=self._llm_model
            )
            
            # Collect result
            completed_task = tm.get_task(task.id)
            task_result = {
                "id": task.id,
                "title": task.title,
                "status": completed_task.status if completed_task else "unknown",
                "result": completed_task.result if completed_task else None
            }
            results["tasks"].append(task_result)
            
            if completed_task and completed_task.status == "completed":
                results["completed"] += 1
                if verbose and completed_task.result:
                    preview = completed_task.result[:200] + "..." if len(completed_task.result) > 200 else completed_task.result
                    print(f"   📄 Result: {preview[:100]}...")
            else:
                results["failed"] += 1
            
            # Cleanup worker
            agent_manager.kill_worker(worker.id)
        
        # Report worktree status
        if self.config.use_worktrees and verbose:
            print("\n" + "=" * 60)
            print("🌳 Git Worktree Status")
            print("=" * 60)
            
            wt_mgr = WorktreeManager(self.config.repo_path)
            worktrees = wt_mgr.list_worktrees()
            
            for wt in worktrees:
                branch = wt.get("branch", "detached")
                path = wt.get("path", "unknown")
                print(f"   📂 {path}")
                print(f"      Branch: {branch}")
        
        # Summary
        if verbose:
            print("\n" + "=" * 60)
            print("📊 SUMMARY")
            print("=" * 60)
            print(f"✅ Completed: {results['completed']}/{len(tasks)} tasks")
            print(f"❌ Failed: {results['failed']}/{len(tasks)} tasks")
            print(f"\n📁 Artifacts: {self.config.town_root}")
            print(f"📋 Tasks: {project_path / '.tasks' / 'tasks.json'}")
        
        return results
    
    def generate_readme(self) -> str:
        """Generate a CLI validation README for the workspace."""
        town_root = self.config.town_root
        project_name = self.config.name
        repo_path = self.config.repo_path
        
        return f'''# {self.config.convoy_name} - CLI Validation Guide

## Overview
This workspace was created by the Simple Gas Town Test Runner.

## Quick Validation Commands

### List Projects
```bash
cd {town_root}
sgt project list
```

### List Tasks
```bash
sgt task list --project {project_name}
```

### View Task Details
```bash
sgt task show <task-id> --project {project_name}
```

### View Convoy Status
```bash
sgt convoy list
```

### Check Git Worktrees
```bash
cd {repo_path}
git worktree list
git branch -a
```

## Directory Structure
```
{town_root.name}/
├── .gastown/
├── state/
├── manager/
└── projects/
    └── {project_name}/
        ├── .tasks/
        │   └── tasks.json
        └── workers/
```

## Extracting Results

```python
from pathlib import Path
from sgt.core.task_manager import TaskManager

tm = TaskManager(Path('{town_root}/projects/{project_name}'))
for task in tm.list_tasks():
    print(f"=== {{task.title}} ===")
    print(task.result)
```
'''
    
    def save_readme(self, path: Optional[Path] = None) -> Path:
        """Save the README to the workspace."""
        if path is None:
            path = self.config.town_root / "README.md"
        
        path.write_text(self.generate_readme(), encoding='utf-8')
        return path
