# Test Generator Town

Proof of concept for generating tests for external repositories using Simple Gas Town agents.

## Quick Start

1. **Clone your target repository** somewhere on disk

2. **Update the configuration** in `configs/project.yaml`:
   ```yaml
   repo_path: "C:/path/to/your/repo"
   ```

3. **Set your LLM token** (one of):
   ```bash
   export GITHUB_TOKEN=your_token
   # or
   export OPENAI_API_KEY=your_key
   ```

4. **Run**:
   ```bash
   python -m test_generator_town configs/project.yaml
   ```

## How It Works

1. Workers are spawned with isolated git worktrees
2. Each worker gets a test generation task
3. LLM generates test code based on the repository
4. Generated tests are committed to worker branches
5. You can review and merge the branches you want

## After Running

View generated test branches:
```bash
cd /path/to/your/repo
git branch -a | grep worker
```

View generated files:
```bash
git show worker-xxx:test_file.py
```

Merge tests to main:
```bash
git checkout main
git merge worker-xxx --no-ff -m "Add generated tests"
```

## Configuration

| Field | Description |
|-------|-------------|
| `repo_path` | Path to target git repository |
| `town_root` | Workspace directory (default: `./workspace`) |
| `tasks` | List of test generation tasks |

## CLI Options

```bash
python -m test_generator_town config.yaml           # Run
python -m test_generator_town config.yaml --quiet   # Less output
python -m test_generator_town config.yaml --no-cleanup  # Keep workspace
```
