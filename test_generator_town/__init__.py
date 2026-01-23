"""
Test Generator Town
===================
Generates tests for repositories using Simple Gas Town agents.

Usage:
    python -m test_generator_town configs/gastown_playground.yaml
"""

from .runner import Runner
from .config import ProjectConfig, TaskConfig

__all__ = ["Runner", "ProjectConfig", "TaskConfig"]
