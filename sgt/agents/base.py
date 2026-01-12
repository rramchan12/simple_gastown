"""Base agent class."""

from abc import ABC, abstractmethod
from pathlib import Path

from sgt.storage.mailbox import Mailbox
from sgt.utils.logger import setup_logger


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, agent_id: str, workspace: Path):
        self.id = agent_id
        self.workspace = Path(workspace)
        self.mailbox = Mailbox(self.workspace / "mailbox")
        self.logger = setup_logger(f"agent.{agent_id}")
    
    @abstractmethod
    async def run(self):
        """Main agent loop - must be implemented by subclasses."""
        pass
    
    def check_mailbox(self):
        """Check for new messages."""
        messages = self.mailbox.read_all()
        self.logger.info(f"Received {len(messages)} messages")
        return messages
    
    def send_message(self, to_mailbox: Path, subject: str, body: str, metadata: dict = None):
        """Send a message to another agent."""
        from sgt.storage.mailbox import send_message
        return send_message(self.id, to_mailbox, subject, body, metadata)
