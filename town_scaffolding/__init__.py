"""
Simple Gas Town Scaffolding
============================
A reusable template for building task-based agents with Simple Gas Town.

Copy this folder to start a new project, then customize:
1. Edit configs/project.yaml with your repository and tasks
2. Run: python -m your_project_name configs/project.yaml

Usage:
    from town_scaffolding import Runner
    runner = Runner.from_config("path/to/config.yaml")
    await runner.run()
"""

from .runner import Runner
from .config import ProjectConfig, TaskConfig

__all__ = ["Runner", "ProjectConfig", "TaskConfig"]
