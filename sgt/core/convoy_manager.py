"""Convoy management for tracking batches of tasks."""

from typing import List, Optional
from datetime import datetime

from sgt.models import Convoy, ConvoyStatus, TaskStatus
from sgt.storage.state import StateManager
from sgt.core.task_manager import TaskManager
from sgt.utils.ids import generate_convoy_id
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConvoyManager:
    """Manages convoys (batches of tasks)."""
    
    def __init__(self, state_manager: StateManager, task_manager: TaskManager):
        self.state_manager = state_manager
        self.task_manager = task_manager
    
    def create_convoy(self, name: str, task_ids: List[str],
                     notify: List[str] = None) -> Convoy:
        """Create a new convoy."""
        convoy = Convoy(
            id=generate_convoy_id(),
            name=name,
            status=ConvoyStatus.ACTIVE,
            tasks=task_ids,
            notify=notify or ["manager"]
        )
        
        # Associate tasks with this convoy
        for task_id in task_ids:
            self.task_manager.set_convoy(task_id, convoy.id)
        
        self.state_manager.add_convoy(convoy)
        
        logger.info(f"Created convoy {convoy.id}: {name} with {len(task_ids)} tasks")
        
        return convoy
    
    def get_convoy(self, convoy_id: str) -> Optional[Convoy]:
        """Get a convoy by ID."""
        return self.state_manager.get_convoy(convoy_id)
    
    def list_convoys(self, status: Optional[ConvoyStatus] = None) -> List[Convoy]:
        """List all convoys, optionally filtered by status."""
        status_str = status.value if status else None
        return self.state_manager.list_convoys(status=status_str)
    
    def check_convoy_completion(self, convoy_id: str) -> bool:
        """Check if all tasks in a convoy are complete."""
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            return False
        
        # Check each task
        for task_id in convoy.tasks:
            task = self.task_manager.get_task(task_id)
            if not task or task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False
        
        return True
    
    def complete_convoy(self, convoy_id: str):
        """Mark a convoy as complete."""
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            return
        
        convoy.status = ConvoyStatus.COMPLETED
        convoy.completed_at = datetime.utcnow()
        
        self.state_manager.update_convoy(convoy)
        
        logger.info(f"Completed convoy {convoy_id}")
        
        # TODO: Send notifications to notify list
    
    def auto_check_convoys(self):
        """Check all active convoys and auto-complete if done."""
        active_convoys = self.list_convoys(status=ConvoyStatus.ACTIVE)
        
        for convoy in active_convoys:
            if self.check_convoy_completion(convoy.id):
                self.complete_convoy(convoy.id)
    
    def get_convoy_progress(self, convoy_id: str) -> dict:
        """Get progress statistics for a convoy."""
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            return {}
        
        total = len(convoy.tasks)
        completed = 0
        failed = 0
        in_progress = 0
        
        for task_id in convoy.tasks:
            task = self.task_manager.get_task(task_id)
            if task:
                if task.status == TaskStatus.COMPLETED:
                    completed += 1
                elif task.status == TaskStatus.FAILED:
                    failed += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    in_progress += 1
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "percent_complete": (completed / total * 100) if total > 0 else 0
        }
