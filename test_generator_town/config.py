"""
Configuration models for Test Generator Town.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import yaml
import json


@dataclass
class TaskConfig:
    """Configuration for a test generation task."""
    title: str
    description: str
    priority: str = "normal"
    tags: List[str] = field(default_factory=list)


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class ProjectConfig:
    """Main configuration for test generation."""
    name: str
    repo_path: Path
    town_root: Path
    tasks: List[TaskConfig]
    
    llm: LLMConfig = field(default_factory=LLMConfig)
    use_worktrees: bool = True
    preserve_worktrees: bool = True  # Keep worktrees after task completion for inspection
    convoy_name: str = "Test Generation"
    cleanup_on_start: bool = True
    
    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectConfig":
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data, path.parent)
    
    @classmethod
    def from_json(cls, path: Path) -> "ProjectConfig":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls._from_dict(data, path.parent)
    
    @classmethod
    def _from_dict(cls, data: dict, base_path: Path) -> "ProjectConfig":
        repo_path = Path(data["repo_path"])
        if not repo_path.is_absolute():
            repo_path = (base_path / repo_path).resolve()
        
        town_root = Path(data.get("town_root", "./workspace"))
        if not town_root.is_absolute():
            town_root = (base_path / town_root).resolve()
        
        tasks = []
        for task_data in data.get("tasks", []):
            tasks.append(TaskConfig(
                title=task_data["title"],
                description=task_data["description"],
                priority=task_data.get("priority", "normal"),
                tags=task_data.get("tags", [])
            ))
        
        llm_data = data.get("llm", {})
        llm = LLMConfig(
            provider=llm_data.get("provider"),
            model=llm_data.get("model"),
            temperature=llm_data.get("temperature", 0.7),
            max_tokens=llm_data.get("max_tokens", 4096)
        )
        
        return cls(
            name=data["name"],
            repo_path=repo_path,
            town_root=town_root,
            tasks=tasks,
            llm=llm,
            use_worktrees=data.get("use_worktrees", True),
            preserve_worktrees=data.get("preserve_worktrees", True),
            convoy_name=data.get("convoy_name", "Test Generation"),
            cleanup_on_start=data.get("cleanup_on_start", True)
        )
    
    def validate(self) -> List[str]:
        errors = []
        if not self.repo_path.exists():
            errors.append(f"Repository path does not exist: {self.repo_path}")
        elif not (self.repo_path / ".git").exists():
            errors.append(f"Not a git repository: {self.repo_path}")
        if not self.tasks:
            errors.append("No tasks defined in configuration")
        return errors
