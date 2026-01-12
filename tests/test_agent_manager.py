"""Tests for agent manager."""

import pytest
from pathlib import Path
from sgt.core.agent_manager import AgentManager
from sgt.models import AgentType, AgentStatus


def test_spawn_worker(tmp_path):
    """Test spawning a worker."""
    am = AgentManager(tmp_path)
    
    worker = am.spawn_worker("test-project", "task-123")
    
    assert worker.id.startswith("worker-")
    assert worker.type == AgentType.WORKER
    assert worker.project == "test-project"
    assert worker.task_id == "task-123"
    assert Path(worker.workspace).exists()
    assert Path(worker.mailbox_path).exists()


def test_list_workers(tmp_path):
    """Test listing workers."""
    am = AgentManager(tmp_path)
    
    worker1 = am.spawn_worker("proj1", "task-1")
    worker2 = am.spawn_worker("proj2", "task-2")
    
    workers = am.list_workers()
    assert len(workers) == 2
    
    proj1_workers = am.list_workers(project="proj1")
    assert len(proj1_workers) == 1
    assert proj1_workers[0].id == worker1.id


def test_kill_worker(tmp_path):
    """Test killing a worker."""
    am = AgentManager(tmp_path)
    
    worker = am.spawn_worker("test-project", "task-123")
    workspace = Path(worker.workspace)
    
    assert workspace.exists()
    
    am.kill_worker(worker.id)
    
    assert not workspace.exists()
    assert am.get_worker(worker.id) is None


def test_create_manager(tmp_path):
    """Test creating the manager agent."""
    am = AgentManager(tmp_path)
    
    manager = am.create_manager()
    
    assert manager.id == "manager"
    assert manager.type == AgentType.MANAGER
    assert Path(manager.workspace).exists()
    assert Path(manager.mailbox_path).exists()
