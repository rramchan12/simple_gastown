# Simple Gas Town

A simplified multi-agent task orchestration system inspired by Gas Town. Vibe Code Alert!

## Overview

Simple Gas Town enables persistent, observable multi-agent coordination through:

- File-based persistence - All state survives crashes and restarts
- Isolated workspaces - Each agent works independently
- Mailbox communication - Agents pass messages via JSON files
- LLM-ready - Designed for AI-powered task execution
- Propulsion Principle - Workers execute immediately when assigned work

## Features

### Phase 1 ✅ - Core Foundation
- Task creation, listing, and management
- Worker lifecycle management (spawn, run, kill)
- Mailbox-based message passing
- Hook-based work assignment
- Convoy (batch) tracking
- JSON file state persistence
- Rich CLI with beautiful output

### Phase 2 ✅ - Git Integration
- Git worktree per worker (isolated branches)
- Generated code committed to worker branches
- Automatic worktree cleanup

### Phase 3 ✅ - LLM Integration
- GitHub Models / OpenAI / Anthropic support
- Real task execution with AI
- Code extraction from LLM responses
- Auto-detection from environment tokens

### Phase 4 (Planned) - Supervision
- Health monitoring
- Automatic recovery
- Timeout handling

## Proof of Concept: Test Generator Town

A working POC that generates tests for external repositories:

```bash
# Configure your target repo
edit test_generator_town/configs/project.yaml

# Run
python -m test_generator_town configs/project.yaml
```

See [test_generator_town/README.md](test_generator_town/README.md) for details.

## Quick Start

### Installation

```bash
# Clone or download
cd simple_gastown

# Install dependencies
pip install -e .

# Verify installation
sgt --version
```

### Basic Usage

```bash
# 1. Initialize a new town
sgt init ~/my-gastown
cd ~/my-gastown

# 2. Add a project
sgt project add my-app

# 3. Create a task
sgt task create "Fix parser bug" \
    --description "Null pointer on line 42" \
    --priority high \
    --project my-app

# 4. Assign work (spawns worker automatically)
sgt assign task-20260112100000-abc12345 --project my-app

# 5. Run the worker (Phase 1 - manual execution)
sgt worker run worker-20260112100100-xyz67890

# 6. Check results
sgt task show task-20260112100000-abc12345 --project my-app
```

### Run the Demo

```bash
python demo.py
```

The demo creates a complete example with:
- Town initialization
- Project creation
- 3 tasks grouped into a convoy
- Automatic worker spawning and execution
- Progress tracking and completion

Demo completes in approximately 6 seconds.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Detailed getting started guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[BUILD_SUMMARY.md](BUILD_SUMMARY.md)** - What was built and how
- **[sgastown_schematic.md](sgastown_schematic.md)** - Original design specification

## Architecture

```
┌─────────┐
│   CLI   │  ← Rich, beautiful command-line interface
└────┬────┘
     │
┌────▼────────────┐
│  Core Managers  │  ← Task, Agent, Convoy, Workspace
└────┬────────────┘
     │
┌────▼─────┐
│ Storage  │  ← State, Mailbox, Hooks (JSON files)
└────┬─────┘
     │
┌────▼──────┐
│  Agents   │  ← Manager (persistent), Worker (ephemeral)
└───────────┘
```

### Key Entities

- **Manager** - Human-controlled coordinator (persistent)
- **Worker** - Autonomous task executor (ephemeral, self-destructs when done)
- **Tasks** - Units of work tracked in JSON files
- **Convoys** - Batches of related tasks tracked together
- **Mailboxes** - Message passing between agents
- **Hooks** - Work assignments for workers

## CLI Commands

### Initialization
```bash
sgt init <path>                     # Create new town
sgt project add <name>              # Add project
sgt status                          # Show system status
```

### Task Management
```bash
sgt task create <title> --project <name>
sgt task list --project <name>
sgt task show <task-id> --project <name>
```

### Worker Management
```bash
sgt worker spawn <task-id> --project <name>
sgt worker list
sgt worker run <worker-id>
sgt worker kill <worker-id>
sgt worker logs <worker-id>
```

### Convoy Management
```bash
sgt convoy create <name> <task-ids...> --project <name>
sgt convoy list
sgt convoy status <convoy-id> --project <name>
```

### Combined Operations
```bash
sgt assign <task-id> --project <name>  # Spawn + assign + hook
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=sgt tests/
```

## Project Structure

```
simple_gastown/
├── sgt/                        # Main package
│   ├── cli/                   # CLI commands
│   ├── core/                  # Business logic
│   ├── agents/                # Agent implementations
│   ├── storage/               # Persistence layer
│   ├── git/                   # Git worktree management
│   ├── llm/                   # LLM provider integration
│   └── utils/                 # Utilities
│
├── test_generator_town/       # POC: Test generation for external repos
│   ├── configs/project.yaml  # Configuration
│   ├── runner.py              # Execution engine
│   └── README.md
│
├── town_scaffolding/          # Template for new projects
│   ├── configs/project.yaml
│   └── README.md
│
├── tests/                     # Unit tests
├── pyproject.toml            # Project config
└── requirements.txt          # Dependencies
```

## Technology Stack

- **Python 3.9+** - Modern Python with type hints
- **Click** - Command-line interface framework
- **Rich** - Beautiful terminal output
- **Pydantic** - Data validation and settings management
- **asyncio** - Async/await for future LLM integration
- **JSON** - Simple, readable file storage

## Design Philosophy

1. **Persistence First** - Everything survives crashes
2. **Observable** - All state is visible and inspectable
3. **Propulsion** - Workers execute immediately when assigned
4. **Isolation** - Each worker has its own workspace
5. **Self-Management** - Workers self-destruct when done
6. **Simplicity** - JSON files, no databases

## Comparison with Original Gas Town

| Feature | Simple Gas Town | Full Gas Town |
|---------|----------------|---------------|
| Language | Python | Go |
| Lines of Code | ~2,500 | ~50,000 |
| Storage | JSON files | Git-backed SQLite |
| Agents | 2 types | 6+ types |
| LLM Support | OpenAI/Claude | Claude Code CLI |
| Complexity | Simple | Production-grade |

Simple Gas Town captures the core concepts while remaining easy to understand and extend.

## Contributing

This is a learning/demonstration project. Feel free to:
- Fork and experiment
- Implement Phase 2 (Git integration)
- Add Phase 3 (LLM integration)
- Create new agent types
- Improve the CLI

## License

MIT License - See LICENSE file for details

## Support

Check the [QUICKSTART.md](QUICKSTART.md) for detailed usage or see [sgastown_schematic.md](sgastown_schematic.md) for design details.

Inspired by the original [Gas Town](https://github.com/codelion/gastown) project.
