# Test Generator Demo - CLI Validation Guide

## Overview
This directory contains the Gas Town workspace created by `demo_test_generator.py`.
Use the `sgt` CLI commands below to inspect the generated artifacts.

## Quick Validation Commands

### 1. List Projects
```bash
cd Q:\workspace\simple_gastown\test-generator-town
sgt project list
```

### 2. List Tasks
```bash
sgt task list --project test-gen
```

### 3. View Task Details
```bash
# Get task IDs from the list above, then:
sgt task show <task-id> --project test-gen
```

### 4. View Convoy Status
```bash
sgt convoy list
sgt convoy show <convoy-id>
```

### 5. Check Git Worktrees
```bash
cd Q:\workspace\simple_gastown\test-generator-town\calculator-repo
git worktree list
git branch -a
```

## Directory Structure
```
test-generator-town/
├── .gastown/           # Gas Town configuration
├── state/              # Agent and convoy state
│   ├── agents.json
│   └── convoys.json
├── manager/            # Manager agent workspace
│   └── mailbox/
├── projects/
│   └── test-gen/       # Our test generation project
│       ├── .tasks/
│       │   └── tasks.json    # All task definitions & results
│       ├── settings/
│       └── workers/          # Worker workspaces (with worktrees)
└── calculator-repo/    # Source git repository
    ├── src/
    │   └── calculator.py
    ├── tests/
    └── pyproject.toml
```

## Extracting Generated Tests

### Using Python
```python
from pathlib import Path
from sgt.core.task_manager import TaskManager

tm = TaskManager(Path('./test-generator-town/projects/test-gen'))
for task in tm.list_tasks():
    if 'pytest' in task.title.lower():
        print(f"=== {task.title} ===")
        print(task.result)
```

### Using CLI + jq (if installed)
```bash
cat test-generator-town/projects/test-gen/.tasks/tasks.json | jq '.tasks[] | select(.title | contains("pytest")) | .result'
```

## Re-running the Demo
```bash
python demo_test_generator.py
```

Note: This will clean up and recreate the entire workspace.

## LLM Configuration
The demo auto-detects LLM providers in this order:
1. `GITHUB_TOKEN` → GitHub Models (gpt-4o-mini)
2. `OPENAI_API_KEY` → OpenAI (gpt-4o-mini)
3. `ANTHROPIC_API_KEY` → Anthropic (claude-3-haiku)

If no API key is found, runs in simulation mode.
