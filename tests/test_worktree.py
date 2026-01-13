"""Tests for git worktree management."""

import pytest
import subprocess
import tempfile
from pathlib import Path

from sgt.git.worktree import WorktreeManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def git_repo(temp_dir):
    """Create a temporary git repository."""
    repo_path = temp_dir / "test-repo"
    repo_path.mkdir()
    
    # Initialize repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_path, capture_output=True
    )
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path, capture_output=True
    )
    
    return repo_path


class TestWorktreeManager:
    """Tests for WorktreeManager."""
    
    def test_is_git_repo_true(self, git_repo):
        """Test detecting a git repository."""
        mgr = WorktreeManager(git_repo)
        assert mgr.is_git_repo() is True
    
    def test_is_git_repo_false(self, temp_dir):
        """Test detecting a non-git directory."""
        mgr = WorktreeManager(temp_dir)
        assert mgr.is_git_repo() is False
    
    def test_init_repo(self, temp_dir):
        """Test initializing a git repository."""
        repo_path = temp_dir / "new-repo"
        repo_path.mkdir()
        
        mgr = WorktreeManager(repo_path)
        assert mgr.is_git_repo() is False
        
        success = mgr.init_repo()
        assert success is True
        assert mgr.is_git_repo() is True
    
    def test_create_branch(self, git_repo):
        """Test creating a branch."""
        mgr = WorktreeManager(git_repo)
        
        success = mgr.create_branch("test-branch")
        assert success is True
        
        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", "test-branch"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "test-branch" in result.stdout
    
    def test_create_branch_already_exists(self, git_repo):
        """Test creating a branch that already exists."""
        mgr = WorktreeManager(git_repo)
        
        # Create branch first time
        mgr.create_branch("existing-branch")
        
        # Should succeed even if already exists
        success = mgr.create_branch("existing-branch")
        assert success is True
    
    def test_create_worktree(self, git_repo, temp_dir):
        """Test creating a worktree."""
        mgr = WorktreeManager(git_repo)
        
        worktree_path = temp_dir / "worktree-test"
        success = mgr.create_worktree(worktree_path, "feature-1")
        
        assert success is True
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()
    
    def test_list_worktrees(self, git_repo, temp_dir):
        """Test listing worktrees."""
        mgr = WorktreeManager(git_repo)
        
        # Create a worktree
        worktree_path = temp_dir / "worktree-list"
        mgr.create_worktree(worktree_path, "list-test")
        
        worktrees = mgr.list_worktrees()
        
        # Should have at least 2 (main repo + our worktree)
        assert len(worktrees) >= 2
        
        paths = [wt.get("path") for wt in worktrees]
        assert str(worktree_path) in paths
    
    def test_remove_worktree(self, git_repo, temp_dir):
        """Test removing a worktree."""
        mgr = WorktreeManager(git_repo)
        
        worktree_path = temp_dir / "worktree-remove"
        mgr.create_worktree(worktree_path, "remove-test")
        
        assert worktree_path.exists()
        
        success = mgr.remove_worktree(worktree_path)
        assert success is True
        assert not worktree_path.exists()
    
    def test_get_current_branch(self, git_repo):
        """Test getting current branch."""
        mgr = WorktreeManager(git_repo)
        branch = mgr.get_current_branch()
        
        # Should be main or master
        assert branch in ["main", "master"]
    
    def test_commit_changes(self, git_repo):
        """Test committing changes."""
        mgr = WorktreeManager(git_repo)
        
        # Make a change
        (git_repo / "test.txt").write_text("test content")
        
        success = mgr.commit_changes(git_repo, "Test commit")
        assert success is True
        
        # Verify commit
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "Test commit" in result.stdout
    
    def test_commit_no_changes(self, git_repo):
        """Test committing with no changes."""
        mgr = WorktreeManager(git_repo)
        
        # Should succeed with no changes
        success = mgr.commit_changes(git_repo, "No changes")
        assert success is True
    
    def test_get_status_clean(self, git_repo):
        """Test getting status of clean repo."""
        mgr = WorktreeManager(git_repo)
        status = mgr.get_status(git_repo)
        
        assert status.strip() == ""
    
    def test_get_status_modified(self, git_repo):
        """Test getting status with modifications."""
        mgr = WorktreeManager(git_repo)
        
        # Make a change
        (git_repo / "new-file.txt").write_text("new content")
        
        status = mgr.get_status(git_repo)
        assert "new-file.txt" in status
    
    def test_has_uncommitted_changes(self, git_repo):
        """Test checking for uncommitted changes."""
        mgr = WorktreeManager(git_repo)
        
        # Clean state
        assert mgr.has_uncommitted_changes(git_repo) is False
        
        # Add a file
        (git_repo / "change.txt").write_text("change")
        assert mgr.has_uncommitted_changes(git_repo) is True
    
    def test_delete_branch(self, git_repo):
        """Test deleting a branch."""
        mgr = WorktreeManager(git_repo)
        
        # Create a branch
        mgr.create_branch("delete-me")
        
        # Delete it
        success = mgr.delete_branch("delete-me")
        assert success is True
        
        # Verify deleted
        result = subprocess.run(
            ["git", "branch", "--list", "delete-me"],
            cwd=git_repo, capture_output=True, text=True
        )
        assert "delete-me" not in result.stdout
    
    def test_worktree_isolation(self, git_repo, temp_dir):
        """Test that changes in worktree don't affect main repo."""
        mgr = WorktreeManager(git_repo)
        
        worktree_path = temp_dir / "isolated-worktree"
        mgr.create_worktree(worktree_path, "isolated-branch")
        
        # Make changes in worktree
        (worktree_path / "worktree-only.txt").write_text("worktree content")
        mgr.commit_changes(worktree_path, "Worktree commit")
        
        # Main repo should not have the file
        assert not (git_repo / "worktree-only.txt").exists()
        
        # But worktree should
        assert (worktree_path / "worktree-only.txt").exists()
