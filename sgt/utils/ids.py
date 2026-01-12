"""ID generation utilities."""

import uuid
from datetime import datetime


def generate_task_id() -> str:
    """Generate a unique task ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"task-{timestamp}-{short_uuid}"


def generate_convoy_id() -> str:
    """Generate a unique convoy ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"convoy-{timestamp}-{short_uuid}"


def generate_worker_id() -> str:
    """Generate a unique worker ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"worker-{timestamp}-{short_uuid}"


def generate_message_id() -> str:
    """Generate a unique message ID."""
    return f"msg-{uuid.uuid4()}"
