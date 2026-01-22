"""
Test Generator Town
====================
A proof-of-concept for generating tests for external repositories.

Usage:
    python -m test_generator_town configs/project.yaml
"""

from .runner import Runner
from .config import ProjectConfig, TaskConfig

__all__ = ["Runner", "ProjectConfig", "TaskConfig"]
