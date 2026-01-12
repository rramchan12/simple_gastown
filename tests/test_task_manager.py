"""Tests for task manager."""

import pytest
from pathlib import Path
from sgt.core.task_manager import TaskManager
from sgt.models import TaskStatus, TaskPriority


def test_create_task(tmp_path):
    """Test creating a task."""
    tm = TaskManager(tmp_path)
    task = tm.create_task("Test task", "Test description")
    
    assert task.id.startswith("task-")
    assert task.status == TaskStatus.OPEN
    assert task.title == "Test task"
    assert task.description == "Test description"


def test_get_task(tmp_path):
    """Test retrieving a task."""
    tm = TaskManager(tmp_path)
    task = tm.create_task("Test", "Desc")
    
    retrieved = tm.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.title == "Test"


def test_assign_task(tmp_path):
    """Test assigning a task to a worker."""
    tm = TaskManager(tmp_path)
    task = tm.create_task("Test", "Desc")
    
    tm.assign_task(task.id, "worker-001")
    
    updated = tm.get_task(task.id)
    assert updated.assignee == "worker-001"
    assert updated.status == TaskStatus.IN_PROGRESS


def test_complete_task(tmp_path):
    """Test completing a task."""
    tm = TaskManager(tmp_path)
    task = tm.create_task("Test", "Desc")
    
    tm.complete_task(task.id, "Task completed successfully")
    
    updated = tm.get_task(task.id)
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result == "Task completed successfully"
    assert updated.completed_at is not None


def test_list_tasks(tmp_path):
    """Test listing tasks."""
    tm = TaskManager(tmp_path)
    
    task1 = tm.create_task("Task 1", "Desc 1")
    task2 = tm.create_task("Task 2", "Desc 2")
    tm.complete_task(task2.id, "Done")
    
    all_tasks = tm.list_tasks()
    assert len(all_tasks) == 2
    
    open_tasks = tm.list_tasks(status=TaskStatus.OPEN)
    assert len(open_tasks) == 1
    assert open_tasks[0].id == task1.id
    
    completed_tasks = tm.list_tasks(status=TaskStatus.COMPLETED)
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == task2.id
