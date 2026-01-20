#!/usr/bin/env python3
"""
Setup script to initialize the sample calculator repository as a git repo.
Run this once before using the tester module with the calculator config.
"""
import subprocess
from pathlib import Path


def main():
    repo_path = Path(__file__).parent / "sample-repos" / "calculator"
    
    if (repo_path / ".git").exists():
        print(f"✓ Git repo already exists: {repo_path}")
        return
    
    print(f"Initializing git repo: {repo_path}")
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "demo@gastown.local"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Gas Town Demo"], cwd=repo_path, check=True)
    
    # Add and commit
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit: calculator module"], cwd=repo_path, check=True)
    
    print(f"✓ Git repo initialized: {repo_path}")


if __name__ == "__main__":
    main()
