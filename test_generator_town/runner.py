"""
Runner for Test Generator Town.
"""
import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Optional, Union

from .config import ProjectConfig, LLMConfig


class Runner:
    """Executes test generation tasks using Simple Gas Town agents."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self._llm_provider: Optional[str] = None
        self._llm_model: Optional[str] = None
        self._use_llm: bool = False
        
    @classmethod
    def from_config(cls, path: Union[str, Path]) -> "Runner":
        path = Path(path)
        if path.suffix in ('.yaml', '.yml'):
            config = ProjectConfig.from_yaml(path)
        elif path.suffix == '.json':
            config = ProjectConfig.from_json(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        return cls(config)
    
    def _detect_llm(self) -> None:
        if self.config.llm.provider:
            self._llm_provider = self.config.llm.provider
            self._llm_model = self.config.llm.model
            self._use_llm = True
            return
        
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
        town_root = self.config.town_root
        repo_path = self.config.repo_path
        
        if not town_root.exists():
            return
        
        if repo_path.exists():
            try:
                import subprocess
                subprocess.run("git worktree prune", shell=True, cwd=repo_path, capture_output=True)
            except Exception:
                pass
        
        for _ in range(3):
            try:
                shutil.rmtree(town_root, ignore_errors=False)
                break
            except Exception:
                time.sleep(0.5)
                shutil.rmtree(town_root, ignore_errors=True)
    
    def _setup_workspace(self) -> tuple:
        from sgt.core.workspace import WorkspaceManager
        from sgt.core.agent_manager import AgentManager
        from sgt.storage.state import StateManager
        
        town_root = self.config.town_root
        town_root.mkdir(parents=True, exist_ok=True)
        (town_root / ".gastown").mkdir(exist_ok=True)
        (town_root / "state").mkdir(exist_ok=True)
        (town_root / "projects").mkdir(exist_ok=True)
        
        workspace_manager = WorkspaceManager(town_root)
        workspace_manager.create_manager_workspace()
        
        state_manager = StateManager(town_root)
        agent_manager = AgentManager(town_root)
        agent_manager.create_manager()
        
        return workspace_manager, state_manager, agent_manager
    
    def _setup_project(self) -> Path:
        project_path = self.config.town_root / "projects" / self.config.name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / ".tasks").mkdir(exist_ok=True)
        (project_path / "settings").mkdir(exist_ok=True)
        return project_path
    
    async def run(self, verbose: bool = True) -> dict:
        from sgt.core.task_manager import TaskManager
        from sgt.core.convoy_manager import ConvoyManager
        from sgt.agents.worker import run_worker
        from sgt.git.worktree import WorktreeManager
        
        results = {"tasks": [], "completed": 0, "failed": 0, "worktrees": []}
        
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {errors}")
        
        self._detect_llm()
        
        if verbose:
            print("=" * 60)
            print(f"🧪 Test Generator Town: {self.config.name}")
            print("=" * 60)
            
            if self._use_llm:
                print(f"✅ LLM: {self._llm_provider} / {self._llm_model}")
            else:
                print("⚠️  No LLM available - running in simulation mode")
            
            print(f"📂 Target Repository: {self.config.repo_path}")
            print(f"📁 Workspace: {self.config.town_root}")
            print()
        
        if self.config.cleanup_on_start:
            if verbose:
                print("🗑️  Cleaning up previous workspace...")
            self._cleanup_workspace()
        
        if verbose:
            print("📁 Setting up workspace...")
        _, state_manager, agent_manager = self._setup_workspace()
        project_path = self._setup_project()
        
        tm = TaskManager(project_path)
        cm = ConvoyManager(state_manager, tm)
        
        if verbose:
            print("\n📋 Creating test generation tasks...")
        
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
        
        convoy = cm.create_convoy(name=self.config.convoy_name, task_ids=task_ids)
        
        if verbose:
            print(f"\n🚚 Created convoy: {convoy.name} ({convoy.id})")
            print("\n" + "=" * 60)
            print("🏃 Running Test Generation Workers...")
            print("=" * 60)
        
        tasks = tm.list_tasks()
        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"\n[{i}/{len(tasks)}] 🔧 {task.title}")
                print("-" * 50)
            
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
                worker = agent_manager.spawn_worker(project=self.config.name, task_id=task.id)
            
            if verbose:
                print(f"   Worker: {worker.id[-12:]}")
            
            tm.assign_task(task.id, worker.id)
            workspace = Path(worker.workspace)
            
            await run_worker(
                worker.id, workspace, self.config.town_root, self.config.name,
                use_llm=self._use_llm,
                llm_provider=self._llm_provider,
                llm_model=self._llm_model
            )
            
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
            
            # Preserve worktrees if configured (for inspection)
            agent_manager.kill_worker(worker.id, preserve_worktree=self.config.preserve_worktrees)
        
        if self.config.use_worktrees and verbose:
            print("\n" + "=" * 60)
            print("🌳 Git Branches with Generated Tests")
            print("=" * 60)
            
            wt_mgr = WorktreeManager(self.config.repo_path)
            worktrees = wt_mgr.list_worktrees()
            
            for wt in worktrees:
                branch = wt.get("branch", "detached")
                path = wt.get("path", "unknown")
                print(f"   📂 {path}")
                print(f"      Branch: {branch}")
        
        if verbose:
            print("\n" + "=" * 60)
            print("📊 SUMMARY")
            print("=" * 60)
            print(f"✅ Completed: {results['completed']}/{len(tasks)} tasks")
            print(f"❌ Failed: {results['failed']}/{len(tasks)} tasks")
            print(f"\n📁 Workspace: {self.config.town_root}")
            print(f"📋 Tasks: {project_path / '.tasks' / 'tasks.json'}")
            
            if results["worktrees"]:
                print(f"\n🌿 To see generated tests:")
                print(f"   cd {self.config.repo_path}")
                print(f"   git branch -a | grep worker")
        
        return results
    
    def generate_readme(self) -> str:
        return f'''# {self.config.convoy_name} - Results

## Overview
Tests generated by Test Generator Town for: `{self.config.repo_path}`

## View Generated Tests

```bash
cd {self.config.repo_path}
git branch -a | grep worker
git show <branch>:<filename>
```

## Merge Tests to Main

```bash
cd {self.config.repo_path}
git checkout main
git merge <worker-branch> --no-ff -m "Add generated tests"
```
'''
    
    def save_readme(self, path: Optional[Path] = None) -> Path:
        if path is None:
            path = self.config.town_root / "README.md"
        path.write_text(self.generate_readme(), encoding='utf-8')
        return path
