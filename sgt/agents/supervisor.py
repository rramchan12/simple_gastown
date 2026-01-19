"""Supervisor agent for monitoring workers and system health."""

import asyncio
import json
import signal
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from sgt.agents.base import BaseAgent
from sgt.models import AgentState, AgentType, AgentStatus
from sgt.storage.state import StateManager
from sgt.storage.mailbox import send_message
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SupervisorConfig:
    """Configuration for the supervisor."""
    check_interval: int = 30  # Seconds between health checks
    worker_timeout: int = 300  # Seconds before a worker is considered stuck
    nudge_interval: int = 60  # Seconds between nudges to stuck workers
    max_nudges: int = 3  # Max nudges before marking worker as failed
    heartbeat_grace: int = 60  # Grace period for heartbeat checks
    auto_restart: bool = False  # Whether to auto-restart failed workers
    

@dataclass
class WorkerHealth:
    """Health status for a worker."""
    worker_id: str
    status: AgentStatus
    task_id: Optional[str]
    last_heartbeat: datetime
    seconds_since_heartbeat: float
    nudge_count: int = 0
    is_stuck: bool = False
    is_healthy: bool = True
    message: str = ""


class Supervisor(BaseAgent):
    """Supervisor agent that monitors workers and system health."""
    
    def __init__(self, town_root: Path, config: Optional[SupervisorConfig] = None):
        workspace = Path(town_root) / "supervisor"
        workspace.mkdir(parents=True, exist_ok=True)
        
        super().__init__("supervisor", workspace)
        
        self.town_root = Path(town_root)
        self.config = config or SupervisorConfig()
        self.state_manager = StateManager(town_root)
        
        # Track worker nudge counts
        self._nudge_counts: Dict[str, int] = {}
        self._last_nudge_times: Dict[str, datetime] = {}
        
        # Running state
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # PID file for daemon mode
        self.pid_file = workspace / "supervisor.pid"
        self.state_file = workspace / "state.json"
    
    async def run(self):
        """Main supervisor loop."""
        self.logger.info("Supervisor starting...")
        self._running = True
        self._save_state("running")
        
        # Write PID file
        self._write_pid()
        
        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Perform health check
                    await self._health_check()
                    
                    # Wait for next check or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.config.check_interval
                        )
                    except asyncio.TimeoutError:
                        pass  # Normal timeout, continue loop
                        
                except Exception as e:
                    self.logger.error(f"Error in supervisor loop: {e}")
                    await asyncio.sleep(5)  # Brief pause on error
                    
        finally:
            self._cleanup()
    
    async def stop(self):
        """Signal the supervisor to stop."""
        self.logger.info("Supervisor stopping...")
        self._running = False
        self._shutdown_event.set()
    
    async def _health_check(self):
        """Perform a health check on all workers."""
        self.logger.debug("Performing health check...")
        
        workers = self.state_manager.list_agents(agent_type=AgentType.WORKER.value)
        
        if not workers:
            self.logger.debug("No active workers")
            return
        
        now = datetime.utcnow()
        
        for worker in workers:
            health = self._assess_worker_health(worker, now)
            
            if not health.is_healthy:
                self.logger.warning(
                    f"Worker {worker.id} unhealthy: {health.message}"
                )
                
                if health.is_stuck:
                    await self._handle_stuck_worker(worker, health)
    
    def _assess_worker_health(self, worker: AgentState, now: datetime) -> WorkerHealth:
        """Assess the health of a worker."""
        # Calculate time since last heartbeat
        last_heartbeat = worker.last_heartbeat
        if isinstance(last_heartbeat, str):
            last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00').replace('+00:00', ''))
        
        seconds_since = (now - last_heartbeat).total_seconds()
        
        # Get nudge count
        nudge_count = self._nudge_counts.get(worker.id, 0)
        
        # Assess health
        is_stuck = False
        is_healthy = True
        message = "OK"
        
        # Check if worker is running but not sending heartbeats
        if worker.status == AgentStatus.RUNNING:
            if seconds_since > self.config.worker_timeout:
                is_stuck = True
                is_healthy = False
                message = f"No heartbeat for {int(seconds_since)}s (timeout: {self.config.worker_timeout}s)"
            elif seconds_since > self.config.heartbeat_grace:
                is_healthy = False
                message = f"Heartbeat delayed: {int(seconds_since)}s"
        
        # Check for failed status
        elif worker.status == AgentStatus.FAILED:
            is_healthy = False
            message = "Worker in FAILED state"
        
        return WorkerHealth(
            worker_id=worker.id,
            status=worker.status,
            task_id=worker.task_id,
            last_heartbeat=last_heartbeat,
            seconds_since_heartbeat=seconds_since,
            nudge_count=nudge_count,
            is_stuck=is_stuck,
            is_healthy=is_healthy,
            message=message,
        )
    
    async def _handle_stuck_worker(self, worker: AgentState, health: WorkerHealth):
        """Handle a stuck worker by nudging or marking as failed."""
        nudge_count = self._nudge_counts.get(worker.id, 0)
        last_nudge = self._last_nudge_times.get(worker.id)
        now = datetime.utcnow()
        
        # Check if enough time has passed since last nudge
        if last_nudge:
            time_since_nudge = (now - last_nudge).total_seconds()
            if time_since_nudge < self.config.nudge_interval:
                return  # Too soon to nudge again
        
        if nudge_count >= self.config.max_nudges:
            # Max nudges reached, mark as failed
            self.logger.error(
                f"Worker {worker.id} unresponsive after {nudge_count} nudges, marking as failed"
            )
            await self._mark_worker_failed(worker)
            
            # Clean up tracking
            self._nudge_counts.pop(worker.id, None)
            self._last_nudge_times.pop(worker.id, None)
        else:
            # Send nudge
            await self._nudge_worker(worker)
            
            # Update tracking
            self._nudge_counts[worker.id] = nudge_count + 1
            self._last_nudge_times[worker.id] = now
    
    async def _nudge_worker(self, worker: AgentState):
        """Send a nudge message to a stuck worker."""
        self.logger.info(f"Nudging worker {worker.id}")
        
        nudge_count = self._nudge_counts.get(worker.id, 0) + 1
        
        # Send nudge via mailbox
        mailbox_path = Path(worker.mailbox_path)
        send_message(
            from_agent="supervisor",
            to_mailbox=mailbox_path,
            subject="Health Check - Nudge",
            body=f"You haven't reported progress recently. Please update your status. (Nudge #{nudge_count})",
            metadata={
                "type": "nudge",
                "nudge_count": nudge_count,
                "task_id": worker.task_id,
            }
        )
        
        # Also notify manager
        manager_mailbox = self.town_root / "manager" / "mailbox"
        if manager_mailbox.exists():
            send_message(
                from_agent="supervisor",
                to_mailbox=manager_mailbox,
                subject="Worker Nudged",
                body=f"Worker {worker.id} appears stuck on task {worker.task_id}. Sent nudge #{nudge_count}.",
                metadata={
                    "worker_id": worker.id,
                    "task_id": worker.task_id,
                    "nudge_count": nudge_count,
                }
            )
    
    async def _mark_worker_failed(self, worker: AgentState):
        """Mark a worker as failed."""
        self.logger.error(f"Marking worker {worker.id} as failed")
        
        # Update worker status
        worker.status = AgentStatus.FAILED
        self.state_manager.add_agent(worker)
        
        # Notify manager
        manager_mailbox = self.town_root / "manager" / "mailbox"
        if manager_mailbox.exists():
            send_message(
                from_agent="supervisor",
                to_mailbox=manager_mailbox,
                subject="Worker Failed",
                body=f"Worker {worker.id} has been marked as FAILED after being unresponsive. Task {worker.task_id} may need reassignment.",
                metadata={
                    "worker_id": worker.id,
                    "task_id": worker.task_id,
                    "reason": "unresponsive",
                }
            )
        
        # Auto-restart if configured
        if self.config.auto_restart and worker.task_id:
            self.logger.info(f"Auto-restart enabled, would restart worker for task {worker.task_id}")
            # TODO: Implement auto-restart via AgentManager
    
    def get_all_worker_health(self) -> List[WorkerHealth]:
        """Get health status for all workers."""
        workers = self.state_manager.list_agents(agent_type=AgentType.WORKER.value)
        now = datetime.utcnow()
        
        return [self._assess_worker_health(w, now) for w in workers]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of system health."""
        workers = self.state_manager.list_agents(agent_type=AgentType.WORKER.value)
        now = datetime.utcnow()
        
        total = len(workers)
        healthy = 0
        stuck = 0
        failed = 0
        
        for worker in workers:
            health = self._assess_worker_health(worker, now)
            if health.is_healthy:
                healthy += 1
            elif health.is_stuck:
                stuck += 1
            if worker.status == AgentStatus.FAILED:
                failed += 1
        
        return {
            "total_workers": total,
            "healthy": healthy,
            "stuck": stuck,
            "failed": failed,
            "check_interval": self.config.check_interval,
            "worker_timeout": self.config.worker_timeout,
            "running": self._running,
        }
    
    def _save_state(self, status: str):
        """Save supervisor state to file."""
        state = {
            "status": status,
            "started_at": datetime.utcnow().isoformat(),
            "pid": os.getpid(),
            "config": {
                "check_interval": self.config.check_interval,
                "worker_timeout": self.config.worker_timeout,
                "nudge_interval": self.config.nudge_interval,
                "max_nudges": self.config.max_nudges,
            }
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _write_pid(self):
        """Write PID file."""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def _cleanup(self):
        """Clean up on shutdown."""
        self._running = False
        self._save_state("stopped")
        
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        self.logger.info("Supervisor stopped")
    
    @classmethod
    def is_running(cls, town_root: Path) -> bool:
        """Check if a supervisor is already running."""
        pid_file = Path(town_root) / "supervisor" / "supervisor.pid"
        
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            
            # Check if process is still running
            # On Windows, this raises an exception if process doesn't exist
            # On Unix, we send signal 0 to check
            if os.name == 'nt':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError, OSError):
            return False
    
    @classmethod
    def get_running_pid(cls, town_root: Path) -> Optional[int]:
        """Get the PID of the running supervisor, if any."""
        pid_file = Path(town_root) / "supervisor" / "supervisor.pid"
        
        if not pid_file.exists():
            return None
        
        try:
            with open(pid_file) as f:
                return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            return None


async def run_supervisor(town_root: Path, config: Optional[SupervisorConfig] = None):
    """Helper function to run the supervisor."""
    supervisor = Supervisor(town_root, config)
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(supervisor.stop())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    await supervisor.run()
