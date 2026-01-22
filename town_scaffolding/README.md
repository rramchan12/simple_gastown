# Town Scaffolding

A reusable template for building task-based agents with Simple Gas Town.

## Quick Start

1. **Copy this folder** to create a new project:
   ```bash
   cp -r town_scaffolding my_new_project
   ```

2. **Edit the configuration** in `configs/project.yaml`:
   - Set `name` to your project identifier
   - Set `repo_path` to your git repository
   - Define your `tasks`

3. **Run the project**:
   ```bash
   python -m my_new_project configs/project.yaml
   ```

## Configuration

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Unique project identifier |
| `repo_path` | Path to the git repository |
| `tasks` | List of tasks to execute |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `town_root` | `./workspace` | Where to create workspace |
| `convoy_name` | `Task Batch` | Name for the task group |
| `use_worktrees` | `true` | Use git worktrees for isolation |
| `cleanup_on_start` | `true` | Clean previous workspace |
| `llm` | auto-detect | LLM provider configuration |

### Task Structure

```yaml
tasks:
  - title: "Short title"
    description: |
      Detailed description for the agent.
    priority: normal  # high, normal, or low
    tags:
      - category
```

### LLM Auto-Detection

Auto-detects from environment variables:
- `GITHUB_TOKEN` → GitHub Models
- `OPENAI_API_KEY` → OpenAI
- `ANTHROPIC_API_KEY` → Anthropic

Or specify explicitly in config:
```yaml
llm:
  provider: github
  model: gpt-4o-mini
```

## CLI Usage

```bash
python -m town_scaffolding config.yaml           # Run
python -m town_scaffolding config.yaml --quiet   # Less output
python -m town_scaffolding config.yaml --no-cleanup  # Keep workspace
```

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports |
| `__main__.py` | CLI entry point |
| `config.py` | Configuration models |
| `runner.py` | Core execution engine |
| `configs/project.yaml` | Configuration template |
