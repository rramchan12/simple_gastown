"""Process management utilities."""

import subprocess
import sys
import signal
from pathlib import Path
from typing import Optional, List


def spawn_background_process(
    command: List[str],
    cwd: Optional[Path] = None,
    env: Optional[dict] = None
) -> subprocess.Popen:
    """Spawn a background process that continues running."""
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True  # Detach from parent
    )


def kill_process(pid: int) -> None:
    """Kill a process by PID."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            subprocess.run(["kill", "-9", str(pid)], check=False)
    except Exception:
        pass


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        else:
            subprocess.run(["kill", "-0", str(pid)], check=True)
            return True
    except (subprocess.CalledProcessError, Exception):
        return False
