# Quick Start Guide

This guide will walk you through using Simple Gas Town for the first time.

## Installation

```bash
cd q:\workspace\simple_gastown
pip install -e .
```

## Initialize a Town

```bash
# Create a new town
sgt init ~/my-gastown

# Add a project
cd ~/my-gastown
sgt project add my-app
```

## Create and Assign Tasks

```bash
# Create a task
sgt task create "Add user authentication" \
    --description "Implement JWT-based auth" \
    --priority high \
    --project my-app

# The output will show the task ID, e.g., task-20260112100000-abc12345

# List tasks
sgt task list --project my-app

# Assign the task (spawns a worker automatically)
sgt assign task-20260112100000-abc12345 --project my-app

# List workers
sgt worker list

# Run the worker (Phase 1 - manual execution)
sgt worker run worker-20260112100100-xyz67890

# Check task status
sgt task show task-20260112100000-abc12345 --project my-app
```

## Working with Convoys

```bash
# Create multiple tasks
sgt task create "Setup database" --priority high --project my-app
sgt task create "Add models" --priority high --project my-app
sgt task create "Create API" --priority normal --project my-app

# Create a convoy
sgt convoy create "Backend Feature" \
    task-001 task-002 task-003 \
    --project my-app

# Check convoy status
sgt convoy status convoy-xyz789 --project my-app

# List all convoys
sgt convoy list
```

## System Status

```bash
# View overall status
sgt status
```

## Example Workflow

Here's a complete example:

```bash
# 1. Initialize
sgt init ~/demo-town
cd ~/demo-town

# 2. Add a project
sgt project add demo-app

# 3. Create a task
sgt task create "Fix parser bug" \
    --description "Null pointer on line 42" \
    --priority high \
    --project demo-app

# 4. Assign and run
sgt assign task-20260112100000-abc12345 --project demo-app
sgt worker run worker-20260112100100-xyz67890

# 5. Check results
sgt task show task-20260112100000-abc12345 --project demo-app
```

## Phase 1 Notes

In Phase 1, workers simulate work with a 2-second delay. To actually execute tasks:

1. The worker reads its assignment from `hook.json`
2. Simulates processing
3. Marks the task complete
4. Self-reports completion

In Phase 3, workers will use LLMs to actually complete the tasks!

## Directory Structure

After initialization, your town will look like:

```
~/my-gastown/
├── .gastown/           # Configuration
├── state/              # Agent state
├── manager/            # Manager workspace
│   └── mailbox/        # Manager's inbox
└── projects/
    └── my-app/         # Your project
        ├── .tasks/     # Task storage
        └── workers/    # Worker workspaces
```

## Troubleshooting

### "Not a Gas Town directory"
Run `sgt init <path>` first to initialize the town.

### "Project not found"
Add the project with `sgt project add <name>`.

### Worker fails to run
Check the worker's state file: `cat workers/<worker-id>/state.json`

## Next Steps

- Phase 2: Git integration for isolated workspaces
- Phase 3: LLM integration for actual task execution
- Phase 4: Supervisor for health monitoring

For more information, see the main README.md or sgastown_schematic.md.
