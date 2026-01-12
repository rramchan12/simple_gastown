"""Data models for Simple Gas Town."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enum."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority enum."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Task(BaseModel):
    """Represents a unit of work."""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.OPEN
    priority: TaskPriority = TaskPriority.NORMAL
    project: str
    assignee: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    convoy_id: Optional[str] = None


class ConvoyStatus(str, Enum):
    """Convoy status enum."""
    ACTIVE = "active"
    COMPLETED = "completed"


class Convoy(BaseModel):
    """Represents a batch of related tasks."""
    id: str
    name: str
    status: ConvoyStatus = ConvoyStatus.ACTIVE
    tasks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    notify: List[str] = Field(default_factory=list)


class AgentType(str, Enum):
    """Agent type enum."""
    MANAGER = "manager"
    WORKER = "worker"
    SUPERVISOR = "supervisor"


class AgentStatus(str, Enum):
    """Agent status enum."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(BaseModel):
    """Represents an agent's current state."""
    id: str
    type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    project: Optional[str] = None
    task_id: Optional[str] = None
    workspace: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    mailbox_path: str


class Message(BaseModel):
    """Represents a message between agents."""
    id: str
    from_agent: str = Field(alias="from")
    to_agent: str = Field(alias="to")
    subject: str
    body: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class Hook(BaseModel):
    """Represents a work assignment."""
    task_id: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: str
    instructions: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL


class TownConfig(BaseModel):
    """Global town configuration."""
    town_root: str
    default_llm: str = "openai"
    openai_model: str = "gpt-4"
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    worker_timeout: int = 3600  # seconds
    heartbeat_interval: int = 30  # seconds
