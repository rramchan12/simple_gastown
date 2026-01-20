"""
Simple Gas Town Test Runner Module
===================================
A configurable test generation framework using multi-agent orchestration.

Usage:
    from tester import TestRunner
    runner = TestRunner.from_config("path/to/config.yaml")
    await runner.run()
"""

from .runner import TestRunner
from .config import TestConfig, TaskConfig

__all__ = ["TestRunner", "TestConfig", "TaskConfig"]
