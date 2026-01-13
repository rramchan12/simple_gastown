"""Demo script showing git worktree integration (Phase 2)."""

import subprocess
import tempfile
import shutil
import os
import sys
import time
import gc
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def run_cmd(cmd: str, cwd: Path = None, capture: bool = True) -> str:
    """Run a shell command."""
    result = subprocess.run(
        cmd, 
        shell=True, 
        cwd=cwd, 
        capture_output=capture, 
        text=True
    )
    return result.stdout + result.stderr


def cleanup_git_locks(path: Path):
    """Clean up git lock files that may prevent deletion."""
    for lock_file in path.rglob("*.lock"):
        try:
            lock_file.unlink()
        except:
            pass


def main():
    print("=" * 60)
    print("Simple Gas Town - Phase 2: Git Worktree Demo")
    print("=" * 60)
    
    # Use absolute paths for the demo
    script_dir = Path(__file__).parent.resolve()
    demo_dir = script_dir / "demo-phase2-temp"
    if demo_dir.exists():
        shutil.rmtree(demo_dir, ignore_errors=True)
    
    demo_dir.mkdir(exist_ok=True)
    town_root = demo_dir / "demo-town"
    project_repo = demo_dir / "my-project"
    
    try:
        # Step 1: Create a sample project repository
        print("\n[1] Creating sample project repository...")
        project_repo.mkdir()
        run_cmd("git init", project_repo)
        run_cmd('git config user.email "demo@example.com"', project_repo)
        run_cmd('git config user.name "Demo User"', project_repo)
        
        # Add some files
        (project_repo / "main.py").write_text('''"""Main application module."""

def hello():
    """Print hello message."""
    print("Hello, World!")


def add(a, b):
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    hello()
''')
        (project_repo / "README.md").write_text("# My Project\n\nA sample project for demo.")
        
        run_cmd("git add .", project_repo)
        run_cmd('git commit -m "Initial commit"', project_repo)
        print(f"   Created repo at: {project_repo}")
        
        # Step 2: Initialize Gas Town
        print("\n[2] Initializing Gas Town...")
        from sgt.cli.init import init
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(init, [str(town_root)])
        print(f"   {result.output.strip()}")
        
        # Change to town directory for subsequent commands
        os.chdir(town_root)
        
        # Step 3: Add project
        print("\n[3] Adding project...")
        from sgt.cli.init import project
        result = runner.invoke(project, ["add", "my-app"])
        print(f"   {result.output.strip()}")
        
        # Step 4: Create tasks
        print("\n[4] Creating tasks...")
        from sgt.cli.task import task
        
        tasks_to_create = [
            ("Add error handling", "Add try-except blocks to main functions"),
            ("Write unit tests", "Create test cases for add function"),
            ("Update documentation", "Add docstrings and update README"),
        ]
        
        from sgt.core.task_manager import TaskManager
        task_mgr = TaskManager(town_root / "projects" / "my-app")
        
        created_tasks = []
        for title, desc in tasks_to_create:
            t = task_mgr.create_task(title, desc)
            created_tasks.append(t)
            print(f"   Created: {t.id[:20]}... - {title}")
        
        # Step 5: Assign first task with worktree
        print("\n[5] Assigning task with git worktree...")
        from sgt.core.agent_manager import AgentManager
        
        agent_mgr = AgentManager(town_root)
        task_to_assign = created_tasks[0]
        
        worker = agent_mgr.spawn_worker(
            project="my-app",
            task_id=task_to_assign.id,
            instructions="Add error handling to all functions",
            repo_path=project_repo,
            use_worktree=True
        )
        
        print(f"   Spawned worker: {worker.id}")
        print(f"   Workspace: {worker.workspace}")
        
        # Get worktree info
        worktree_path = agent_mgr.get_worktree_path(worker.id)
        print(f"   Worktree: {worktree_path}")
        print(f"   Branch: worker-{worker.id}")
        
        # Step 6: Show git worktrees
        print("\n[6] Git worktrees for project:")
        from sgt.git.worktree import WorktreeManager
        wt_mgr = WorktreeManager(project_repo)
        worktrees = wt_mgr.list_worktrees()
        
        for wt in worktrees:
            branch = wt.get("branch", "detached")
            print(f"   {wt.get('path')}")
            print(f"      Branch: {branch}")
        
        # Step 7: Simulate work in worktree
        print("\n[7] Simulating work in worktree...")
        if worktree_path and worktree_path.exists():
            main_py = worktree_path / "main.py"
            if main_py.exists():
                # Modify the file
                new_content = '''"""Main application module."""


def hello():
    """Print hello message."""
    try:
        print("Hello, World!")
    except Exception as e:
        print(f"Error in hello: {e}")


def add(a, b):
    """Add two numbers."""
    try:
        return a + b
    except TypeError as e:
        print(f"Error: Invalid types - {e}")
        return None


if __name__ == "__main__":
    hello()
'''
                main_py.write_text(new_content)
                print(f"   Modified: main.py")
        
        # Step 8: Check git status
        print("\n[8] Git status in worktree:")
        status = agent_mgr.get_work_status(worker.id)
        if status:
            for line in status.strip().split('\n'):
                print(f"   {line}")
        else:
            print("   No changes")
        
        # Step 9: Commit changes
        print("\n[9] Committing changes...")
        success = agent_mgr.commit_worker_work(
            worker.id, 
            "Add error handling to hello and add functions"
        )
        print(f"   Commit successful: {success}")
        
        # Step 10: Show branches in main repo
        print("\n[10] Branches in main repository:")
        output = run_cmd("git branch -a", project_repo)
        for line in output.strip().split('\n'):
            print(f"   {line}")
        
        # Step 11: Show commit log on worker branch
        print("\n[11] Commit log on worker branch:")
        if worktree_path:
            output = run_cmd("git log --oneline -3", worktree_path)
            for line in output.strip().split('\n'):
                print(f"   {line}")
        
        # Step 12: Verify isolation
        print("\n[12] Verifying isolation (main repo unchanged):")
        main_content = (project_repo / "main.py").read_text()
        if "try:" not in main_content:
            print("   Main repo is unchanged (no try/except)")
        else:
            print("   Warning: Main repo was modified")
        
        worktree_content = (worktree_path / "main.py").read_text()
        if "try:" in worktree_content:
            print("   Worktree has error handling (try/except present)")
        
        # Step 13: Spawn second worker
        print("\n[13] Spawning second worker for parallel work...")
        task2 = created_tasks[1]
        worker2 = agent_mgr.spawn_worker(
            project="my-app",
            task_id=task2.id,
            instructions="Write unit tests",
            repo_path=project_repo,
            use_worktree=True
        )
        print(f"   Spawned worker: {worker2.id}")
        
        worktree_path2 = agent_mgr.get_worktree_path(worker2.id)
        print(f"   Worktree: {worktree_path2}")
        
        # Step 14: Show all worktrees now
        print("\n[14] All worktrees:")
        worktrees = wt_mgr.list_worktrees()
        for wt in worktrees:
            branch = wt.get("branch", "detached")
            print(f"   {branch}: {wt.get('path')}")
        
        # Step 15: Clean up worker
        print("\n[15] Cleaning up first worker...")
        agent_mgr.kill_worker(worker.id, force=True)
        print(f"   Killed worker: {worker.id}")
        
        # Show remaining worktrees
        print("\n   Remaining worktrees:")
        worktrees = wt_mgr.list_worktrees()
        for wt in worktrees:
            branch = wt.get("branch", "detached")
            print(f"   {branch}: {wt.get('path')}")
        
        print("\n" + "=" * 60)
        print("Phase 2 Demo Complete")
        print("=" * 60)
        print("\nFeatures Demonstrated:")
        print("  - Git repository detection")
        print("  - Worktree creation per worker")
        print("  - Isolated branches (worker-<id>)")
        print("  - Making changes in isolated workspace")
        print("  - Committing work from worktree")
        print("  - Multiple workers with parallel worktrees")
        print("  - Worktree cleanup on worker termination")
        print("  - Main repo remains unchanged")
        
    finally:
        # Cleanup - return to original directory first
        os.chdir(Path(__file__).parent)
        
        # Give git a moment to release locks
        time.sleep(0.5)
        gc.collect()
        
        # Remove worktrees first if they exist
        if project_repo.exists():
            run_cmd("git worktree prune", project_repo)
        
        # Cleanup demo directory
        if demo_dir.exists():
            cleanup_git_locks(demo_dir)
            shutil.rmtree(demo_dir, ignore_errors=True)
            print(f"\nCleaned up: {demo_dir}")


if __name__ == "__main__":
    main()
