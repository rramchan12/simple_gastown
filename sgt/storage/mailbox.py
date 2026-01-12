"""Mailbox system for agent communication."""

import json
from pathlib import Path
from typing import List
from datetime import datetime

from sgt.models import Message
from sgt.utils.ids import generate_message_id
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class Mailbox:
    """Manages message passing between agents."""
    
    def __init__(self, mailbox_path: Path):
        self.path = Path(mailbox_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = self.path / "archive"
        self.archive_path.mkdir(exist_ok=True)
    
    def send(self, from_agent: str, to_agent: str, subject: str, 
             body: str, metadata: dict = None) -> Message:
        """Send a message to this mailbox."""
        message = Message(
            id=generate_message_id(),
            **{"from": from_agent, "to": to_agent},
            subject=subject,
            body=body,
            sent_at=datetime.utcnow(),
            read=False,
            metadata=metadata or {}
        )
        
        msg_file = self.path / f"{message.id}.json"
        with open(msg_file, 'w') as f:
            json.dump(message.model_dump(mode='json'), f, indent=2)
        
        logger.info(f"Message {message.id} sent from {from_agent} to {to_agent}")
        
        return message
    
    def read_all(self, mark_as_read: bool = True) -> List[Message]:
        """Read all unread messages."""
        messages = []
        
        for msg_file in sorted(self.path.glob("*.json")):
            try:
                with open(msg_file) as f:
                    data = json.load(f)
                    message = Message(**data)
                    messages.append(message)
                
                # Archive the message if requested
                if mark_as_read:
                    archive_file = self.archive_path / msg_file.name
                    msg_file.rename(archive_file)
            except Exception as e:
                logger.error(f"Error reading message {msg_file}: {e}")
        
        return sorted(messages, key=lambda m: m.sent_at)
    
    def peek(self) -> List[Message]:
        """Read messages without marking as read."""
        return self.read_all(mark_as_read=False)
    
    def count_unread(self) -> int:
        """Count unread messages."""
        return len(list(self.path.glob("*.json")))
    
    def clear(self):
        """Clear all messages (move to archive)."""
        for msg_file in self.path.glob("*.json"):
            archive_file = self.archive_path / msg_file.name
            msg_file.rename(archive_file)
        
        logger.info(f"Cleared mailbox at {self.path}")


def send_message(from_agent: str, to_mailbox: Path, subject: str, 
                body: str, metadata: dict = None) -> Message:
    """Helper function to send a message to any mailbox."""
    mailbox = Mailbox(to_mailbox)
    return mailbox.send(from_agent, "recipient", subject, body, metadata)
