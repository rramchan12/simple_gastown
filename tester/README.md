# Tester Module

A configurable test generation framework using Simple Gas Town multi-agent orchestration.

## Quick Start

### 1. Setup sample repository

```bash
python tester/setup_samples.py
```

### 2. Run the test generator

```bash
python -m tester tester/configs/calculator_tests.yaml
```

Or programmatically:

```python
import asyncio
from tester import TestRunner

runner = TestRunner.from_config("tester/configs/calculator_tests.yaml")
results = asyncio.run(runner.run())
```

## Configuration

Configuration files can be YAML or JSON. See `tester/configs/calculator_tests.yaml` for a complete example.

### Required Fields

```yaml
name: my-project           # Project name
repo_path: ./path/to/repo  # Git repository to test
town_root: ./output-town   # Where to create Gas Town workspace
tasks:                     # List of task definitions
  - title: "Task 1"
    description: "What to do"
```

### Optional Fields

```yaml
use_worktrees: true        # Use git worktrees for isolation (default: true)
convoy_name: "My Convoy"   # Name for the task convoy
cleanup_on_start: true     # Remove previous workspace (default: true)

llm:
  provider: github         # github, openai, anthropic (auto-detects if omitted)
  model: gpt-4o-mini       # Model to use
  temperature: 0.7
  max_tokens: 4096
```

## Task Definition

Each task requires:

- `title` - Short description shown in CLI
- `description` - Full instructions for the LLM worker

Optional:

- `priority` - high, normal, low (default: normal)
- `tags` - List of tags for filtering

## CLI Usage

```bash
# Run with verbose output (default)
python -m tester config.yaml

# Quiet mode
python -m tester config.yaml --quiet

# Skip README generation
python -m tester config.yaml --no-readme

# Keep previous workspace
python -m tester config.yaml --no-cleanup
```

## Validating Results

After running, use the `sgt` CLI to inspect results:

```bash
cd <town_root>
sgt project list
sgt task list --project <name>
sgt task show <task-id> --project <name>
sgt convoy list
```

## Directory Structure

```
tester/
├── __init__.py          # Module exports
├── __main__.py          # CLI entry point
├── config.py            # Configuration models
├── runner.py            # Test runner engine
├── setup_samples.py     # Sample repo setup
├── configs/
│   └── calculator_tests.yaml
└── sample-repos/
    └── calculator/      # Sample git repository
```
