"""Task management."""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from sgt.models import Task, TaskStatus, TaskPriority
from sgt.utils.ids import generate_task_id
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class TaskManager:
    """Manages tasks for a project."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.tasks_dir = self.project_path / ".tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.tasks_dir / "tasks.json"
        
        # Initialize tasks file if it doesn't exist
        if not self.tasks_file.exists():
            self._write_tasks({"tasks": []})
    
    def _read_tasks(self) -> dict:
        """Read tasks from file."""
        try:
            with open(self.tasks_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"tasks": []}
    
    def _write_tasks(self, data: dict):
        """Write tasks to file atomically."""
        temp_file = self.tasks_file.with_suffix('.tmp')
        
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        temp_file.replace(self.tasks_file)
    
    def create_task(self, title: str, description: str, 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   project: str = None) -> Task:
        """Create a new task."""
        task = Task(
            id=generate_task_id(),
            title=title,
            description=description,
            priority=priority,
            project=project or self.project_path.name,
            status=TaskStatus.OPEN
        )
        
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        tasks.append(task.model_dump(mode='json'))
        data["tasks"] = tasks
        
        self._write_tasks(data)
        
        logger.info(f"Created task {task.id}: {task.title}")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        
        for task_data in tasks:
            if task_data.get("id") == task_id:
                return Task(**task_data)
        
        return None
    
    def list_tasks(self, status: Optional[TaskStatus] = None,
                  assignee: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered."""
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        
        result = []
        for task_data in tasks:
            task = Task(**task_data)
            
            if status is not None and task.status != status:
                continue
            
            if assignee is not None and task.assignee != assignee:
                continue
            
            result.append(task)
        
        return result
    
    def assign_task(self, task_id: str, worker_id: str):
        """Assign a task to a worker."""
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        
        for task_data in tasks:
            if task_data.get("id") == task_id:
                task_data["assignee"] = worker_id
                task_data["status"] = TaskStatus.IN_PROGRESS.value
                task_data["updated_at"] = datetime.utcnow().isoformat()
                break
        
        data["tasks"] = tasks
        self._write_tasks(data)
        
        logger.info(f"Assigned task {task_id} to {worker_id}")
    
    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: Optional[str] = None):
        """Update a task's status."""
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        
        for task_data in tasks:
            if task_data.get("id") == task_id:
                task_data["status"] = status.value
                task_data["updated_at"] = datetime.utcnow().isoformat()
                
                if status == TaskStatus.COMPLETED:
                    task_data["completed_at"] = datetime.utcnow().isoformat()
                    if result:
                        task_data["result"] = result
                
                break
        
        data["tasks"] = tasks
        self._write_tasks(data)
        
        logger.info(f"Updated task {task_id} status to {status.value}")
    
    def complete_task(self, task_id: str, result: str):
        """Mark a task as completed with result."""
        self.update_task_status(task_id, TaskStatus.COMPLETED, result)
    
    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        self.update_task_status(task_id, TaskStatus.FAILED, error)
    
    def set_convoy(self, task_id: str, convoy_id: str):
        """Associate a task with a convoy."""
        data = self._read_tasks()
        tasks = data.get("tasks", [])
        
        for task_data in tasks:
            if task_data.get("id") == task_id:
                task_data["convoy_id"] = convoy_id
                task_data["updated_at"] = datetime.utcnow().isoformat()
                break
        
        data["tasks"] = tasks
        self._write_tasks(data)
        
        logger.info(f"Set task {task_id} convoy to {convoy_id}")
