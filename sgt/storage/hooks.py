"""Hook system for work assignments."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from sgt.models import Hook, TaskPriority
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class HookManager:
    """Manages work assignments via hook files."""
    
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.hook_file = self.workspace / "hook.json"
    
    def create_hook(self, task_id: str, assigned_by: str, 
                   instructions: Optional[str] = None,
                   priority: TaskPriority = TaskPriority.NORMAL) -> Hook:
        """Create a work assignment hook."""
        hook = Hook(
            task_id=task_id,
            assigned_at=datetime.utcnow(),
            assigned_by=assigned_by,
            instructions=instructions,
            priority=priority
        )
        
        with open(self.hook_file, 'w') as f:
            json.dump(hook.model_dump(mode='json'), f, indent=2)
        
        logger.info(f"Created hook for task {task_id} in {self.workspace}")
        
        return hook
    
    def read_hook(self) -> Optional[Hook]:
        """Read the current hook."""
        if not self.hook_file.exists():
            return None
        
        try:
            with open(self.hook_file) as f:
                data = json.load(f)
                return Hook(**data)
        except Exception as e:
            logger.error(f"Error reading hook: {e}")
            return None
    
    def clear_hook(self):
        """Clear the hook (task completed)."""
        if self.hook_file.exists():
            self.hook_file.unlink()
            logger.info(f"Cleared hook in {self.workspace}")
    
    def has_hook(self) -> bool:
        """Check if a hook exists."""
        return self.hook_file.exists()
