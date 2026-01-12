"""State management for agents and system data."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from threading import Lock

from sgt.models import AgentState, Convoy, TownConfig
from sgt.utils.logger import setup_logger

logger = setup_logger(__name__)


class StateManager:
    """Manages persistent state for the system."""
    
    def __init__(self, town_root: Path):
        self.town_root = Path(town_root)
        self.state_dir = self.town_root / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.agents_file = self.state_dir / "agents.json"
        self.convoys_file = self.state_dir / "convoys.json"
        self.config_file = self.town_root / ".gastown" / "config.json"
        
        self._lock = Lock()
        
        # Initialize files if they don't exist
        self._init_state_files()
    
    def _init_state_files(self):
        """Initialize state files with empty data."""
        if not self.agents_file.exists():
            self._write_json(self.agents_file, {"agents": []})
        
        if not self.convoys_file.exists():
            self._write_json(self.convoys_file, {"convoys": []})
    
    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON file safely."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _write_json(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file atomically."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = file_path.with_suffix('.tmp')
        
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        temp_file.replace(file_path)
    
    # Agent state management
    
    def add_agent(self, agent: AgentState):
        """Add or update an agent in state."""
        with self._lock:
            data = self._read_json(self.agents_file)
            agents = data.get("agents", [])
            
            # Remove existing agent with same ID
            agents = [a for a in agents if a.get("id") != agent.id]
            
            # Add new agent
            agents.append(agent.model_dump(mode='json'))
            
            data["agents"] = agents
            self._write_json(self.agents_file, data)
            
            logger.info(f"Added agent {agent.id} to state")
    
    def remove_agent(self, agent_id: str):
        """Remove an agent from state."""
        with self._lock:
            data = self._read_json(self.agents_file)
            agents = data.get("agents", [])
            
            agents = [a for a in agents if a.get("id") != agent_id]
            
            data["agents"] = agents
            self._write_json(self.agents_file, data)
            
            logger.info(f"Removed agent {agent_id} from state")
    
    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Get an agent by ID."""
        data = self._read_json(self.agents_file)
        agents = data.get("agents", [])
        
        for agent_data in agents:
            if agent_data.get("id") == agent_id:
                return AgentState(**agent_data)
        
        return None
    
    def list_agents(self, agent_type: Optional[str] = None) -> List[AgentState]:
        """List all agents, optionally filtered by type."""
        data = self._read_json(self.agents_file)
        agents = data.get("agents", [])
        
        result = []
        for agent_data in agents:
            if agent_type is None or agent_data.get("type") == agent_type:
                result.append(AgentState(**agent_data))
        
        return result
    
    def update_agent_heartbeat(self, agent_id: str):
        """Update agent's last heartbeat timestamp."""
        with self._lock:
            data = self._read_json(self.agents_file)
            agents = data.get("agents", [])
            
            for agent_data in agents:
                if agent_data.get("id") == agent_id:
                    from datetime import datetime
                    agent_data["last_heartbeat"] = datetime.utcnow().isoformat()
                    break
            
            data["agents"] = agents
            self._write_json(self.agents_file, data)
    
    # Convoy state management
    
    def add_convoy(self, convoy: Convoy):
        """Add a convoy to state."""
        with self._lock:
            data = self._read_json(self.convoys_file)
            convoys = data.get("convoys", [])
            
            # Remove existing convoy with same ID
            convoys = [c for c in convoys if c.get("id") != convoy.id]
            
            # Add new convoy
            convoys.append(convoy.model_dump(mode='json'))
            
            data["convoys"] = convoys
            self._write_json(self.convoys_file, data)
            
            logger.info(f"Added convoy {convoy.id} to state")
    
    def get_convoy(self, convoy_id: str) -> Optional[Convoy]:
        """Get a convoy by ID."""
        data = self._read_json(self.convoys_file)
        convoys = data.get("convoys", [])
        
        for convoy_data in convoys:
            if convoy_data.get("id") == convoy_id:
                return Convoy(**convoy_data)
        
        return None
    
    def list_convoys(self, status: Optional[str] = None) -> List[Convoy]:
        """List all convoys, optionally filtered by status."""
        data = self._read_json(self.convoys_file)
        convoys = data.get("convoys", [])
        
        result = []
        for convoy_data in convoys:
            if status is None or convoy_data.get("status") == status:
                result.append(Convoy(**convoy_data))
        
        return result
    
    def update_convoy(self, convoy: Convoy):
        """Update a convoy."""
        self.add_convoy(convoy)
    
    # Configuration management
    
    def load_config(self) -> TownConfig:
        """Load town configuration."""
        if self.config_file.exists():
            data = self._read_json(self.config_file)
            return TownConfig(**data)
        else:
            # Return default config
            return TownConfig(town_root=str(self.town_root))
    
    def save_config(self, config: TownConfig):
        """Save town configuration."""
        self._write_json(self.config_file, config.model_dump(mode='json'))
