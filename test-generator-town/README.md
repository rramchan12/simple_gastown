# Test Suite Generation - CLI Validation Guide

## Overview
This workspace was created by the Simple Gas Town Test Runner.

## Quick Validation Commands

### List Projects
```bash
cd Q:\workspace\simple_gastown\test-generator-town
sgt project list
```

### List Tasks
```bash
sgt task list --project test-gen
```

### View Task Details
```bash
sgt task show <task-id> --project test-gen
```

### View Convoy Status
```bash
sgt convoy list
```

### Check Git Worktrees
```bash
cd Q:\workspace\simple_gastown\tester\sample-repos\calculator
git worktree list
git branch -a
```

## Directory Structure
```
test-generator-town/
├── .gastown/
├── state/
├── manager/
└── projects/
    └── test-gen/
        ├── .tasks/
        │   └── tasks.json
        └── workers/
```

## Extracting Results

```python
from pathlib import Path
from sgt.core.task_manager import TaskManager

tm = TaskManager(Path('Q:\workspace\simple_gastown\test-generator-town/projects/test-gen'))
for task in tm.list_tasks():
    print(f"=== {task.title} ===")
    print(task.result)
```
