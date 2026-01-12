"""Tests for mailbox system."""

import pytest
from pathlib import Path
from sgt.storage.mailbox import Mailbox, send_message


def test_send_message(tmp_path):
    """Test sending a message."""
    mailbox = Mailbox(tmp_path)
    
    message = mailbox.send(
        from_agent="worker-1",
        to_agent="manager",
        subject="Test",
        body="Hello"
    )
    
    assert message.id.startswith("msg-")
    assert message.from_agent == "worker-1"
    assert message.to_agent == "manager"
    assert message.subject == "Test"


def test_read_all(tmp_path):
    """Test reading all messages."""
    mailbox = Mailbox(tmp_path)
    
    mailbox.send("worker-1", "manager", "Test 1", "Body 1")
    mailbox.send("worker-2", "manager", "Test 2", "Body 2")
    
    messages = mailbox.read_all(mark_as_read=False)
    assert len(messages) == 2


def test_read_and_archive(tmp_path):
    """Test reading messages moves them to archive."""
    mailbox = Mailbox(tmp_path)
    
    mailbox.send("worker-1", "manager", "Test", "Body")
    
    assert mailbox.count_unread() == 1
    
    messages = mailbox.read_all(mark_as_read=True)
    assert len(messages) == 1
    
    assert mailbox.count_unread() == 0
    assert (tmp_path / "archive").exists()


def test_peek(tmp_path):
    """Test peeking at messages without marking as read."""
    mailbox = Mailbox(tmp_path)
    
    mailbox.send("worker-1", "manager", "Test", "Body")
    
    messages = mailbox.peek()
    assert len(messages) == 1
    assert mailbox.count_unread() == 1
