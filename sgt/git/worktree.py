"""Git worktree management for isolated worker workspaces."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional


class WorktreeManager:
    """Manages git worktrees for worker isolation."""
    
    def __init__(self, repo_path: Path):
        """Initialize with path to the main git repository.
        
        Args:
            repo_path: Path to the main git repository
        """
        self.repo_path = Path(repo_path).resolve()
    
    def _run_git(self, *args, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command.
        
        Args:
            *args: Git command arguments
            cwd: Working directory (defaults to repo_path)
            check: Whether to raise on non-zero exit
            
        Returns:
            CompletedProcess result
        """
        cmd = ["git"] + list(args)
        return subprocess.run(
            cmd,
            cwd=cwd or self.repo_path,
            capture_output=True,
            text=True,
            check=check
        )
    
    def is_git_repo(self) -> bool:
        """Check if repo_path is a valid git repository."""
        try:
            result = self._run_git("rev-parse", "--git-dir", check=False)
            return result.returncode == 0
        except Exception:
            return False
    
    def init_repo(self) -> bool:
        """Initialize a new git repository.
        
        Returns:
            True if successful
        """
        try:
            self.repo_path.mkdir(parents=True, exist_ok=True)
            self._run_git("init")
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_branch(self, branch_name: str, start_point: str = "HEAD") -> bool:
        """Create a new branch.
        
        Args:
            branch_name: Name for the new branch
            start_point: Starting point for the branch
            
        Returns:
            True if successful
        """
        try:
            self._run_git("branch", branch_name, start_point)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_worktree(self, path: Path, branch: str, create_branch: bool = True) -> bool:
        """Create a new worktree for isolated work.
        
        Args:
            path: Path where the worktree should be created
            branch: Branch name for the worktree
            create_branch: If True, create a new branch; if False, use existing
            
        Returns:
            True if successful
        """
        try:
            path = Path(path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if create_branch:
                # Create new branch and worktree together
                self._run_git("worktree", "add", "-b", branch, str(path))
            else:
                # Use existing branch
                self._run_git("worktree", "add", str(path), branch)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def remove_worktree(self, path: Path, force: bool = False) -> bool:
        """Remove a worktree.
        
        Args:
            path: Path to the worktree
            force: If True, force removal even with uncommitted changes
            
        Returns:
            True if successful
        """
        try:
            path = Path(path).resolve()
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(str(path))
            self._run_git(*args, check=False)
            
            # Clean up any leftover directory
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
            
            # Prune stale worktree entries
            self._run_git("worktree", "prune", check=False)
            return True
        except Exception:
            return False
    
    def list_worktrees(self) -> list[dict]:
        """List all worktrees for the repository.
        
        Returns:
            List of worktree info dicts with 'path', 'commit', 'branch' keys
        """
        try:
            result = self._run_git("worktree", "list", "--porcelain")
            worktrees = []
            current = {}
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    if current:
                        worktrees.append(current)
                        current = {}
                elif line.startswith("worktree "):
                    current["path"] = line[9:]
                elif line.startswith("HEAD "):
                    current["commit"] = line[5:]
                elif line.startswith("branch "):
                    # Extract branch name from refs/heads/...
                    branch_ref = line[7:]
                    if branch_ref.startswith("refs/heads/"):
                        current["branch"] = branch_ref[11:]
                    else:
                        current["branch"] = branch_ref
                elif line == "detached":
                    current["detached"] = True
            
            if current:
                worktrees.append(current)
            
            return worktrees
        except subprocess.CalledProcessError:
            return []
    
    def commit_changes(self, message: str, path: Optional[Path] = None, add_all: bool = True) -> bool:
        """Commit changes in a worktree.
        
        Args:
            message: Commit message
            path: Path to worktree (defaults to main repo)
            add_all: If True, stage all changes before committing
            
        Returns:
            True if successful
        """
        try:
            cwd = Path(path) if path else self.repo_path
            
            if add_all:
                self._run_git("add", "-A", cwd=cwd)
            
            # Check if there are changes to commit
            result = self._run_git("status", "--porcelain", cwd=cwd)
            if not result.stdout.strip():
                return True  # Nothing to commit, but not an error
            
            self._run_git("commit", "-m", message, cwd=cwd)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_current_branch(self, path: Optional[Path] = None) -> Optional[str]:
        """Get the current branch name.
        
        Args:
            path: Path to worktree (defaults to main repo)
            
        Returns:
            Branch name or None if detached/error
        """
        try:
            cwd = Path(path) if path else self.repo_path
            result = self._run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
            branch = result.stdout.strip()
            return branch if branch != "HEAD" else None
        except subprocess.CalledProcessError:
            return None
    
    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a branch.
        
        Args:
            branch_name: Name of branch to delete
            force: If True, force deletion even if not merged
            
        Returns:
            True if successful
        """
        try:
            flag = "-D" if force else "-d"
            self._run_git("branch", flag, branch_name)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_diff(self, path: Optional[Path] = None, staged: bool = False) -> str:
        """Get diff of changes.
        
        Args:
            path: Path to worktree (defaults to main repo)
            staged: If True, show staged changes; if False, show unstaged
            
        Returns:
            Diff output as string
        """
        try:
            cwd = Path(path) if path else self.repo_path
            args = ["diff"]
            if staged:
                args.append("--staged")
            result = self._run_git(*args, cwd=cwd)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def get_status(self, path: Optional[Path] = None, short: bool = True) -> str:
        """Get git status.
        
        Args:
            path: Path to worktree (defaults to main repo)
            short: If True, use short format
            
        Returns:
            Status output as string
        """
        try:
            cwd = Path(path) if path else self.repo_path
            args = ["status"]
            if short:
                args.append("--short")
            result = self._run_git(*args, cwd=cwd)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
    
    def has_uncommitted_changes(self, path: Optional[Path] = None) -> bool:
        """Check if there are uncommitted changes.
        
        Args:
            path: Path to worktree (defaults to main repo)
            
        Returns:
            True if there are uncommitted changes
        """
        status = self.get_status(path, short=True)
        return bool(status.strip())
