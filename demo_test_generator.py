#!/usr/bin/env python3
"""
Demo: Test Suite Generator
==========================
Uses Simple Gas Town to generate pytest tests for Python code.

Workers:
  1. analyzer - Analyzes code structure and identifies testable functions
  2. test-writer - Writes pytest test cases for basic operations
  3. test-writer - Writes pytest test cases for advanced functions
  4. docs-writer - Creates test documentation

Run with: python demo_test_generator.py
Requires: GITHUB_TOKEN environment variable set
"""

import asyncio
from pathlib import Path
import shutil
from sgt.core.workspace import WorkspaceManager
from sgt.core.task_manager import TaskManager
from sgt.core.convoy_manager import ConvoyManager
from sgt.core.agent_manager import AgentManager
from sgt.storage.state import StateManager
from sgt.agents.worker import run_worker

# Sample code to test - a simple calculator module
SAMPLE_CODE = '''
"""calculator.py - A simple calculator module for demonstration."""

def add(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b

def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the result."""
    return a - b

def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b

def divide(a: float, b: float) -> float:
    """Divide a by b. Raises ValueError if b is zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def power(base: float, exponent: int) -> float:
    """Raise base to the power of exponent."""
    return base ** exponent

def factorial(n: int) -> int:
    """Calculate factorial of n. Raises ValueError for negative numbers."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def is_even(n: int) -> bool:
    """Check if a number is even."""
    return n % 2 == 0

def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number. n must be non-negative."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''

def main():
    asyncio.run(async_main())


async def async_main():
    print("=" * 60)
    print("🧪 Simple Gas Town: Test Suite Generator Demo")
    print("=" * 60)
    
    # Check for LLM availability
    import os
    llm_available = any([
        os.environ.get('GITHUB_TOKEN'),
        os.environ.get('OPENAI_API_KEY'),
        os.environ.get('ANTHROPIC_API_KEY')
    ])
    
    if llm_available:
        print("✅ LLM API key found - will generate real tests!")
        use_llm = True
        # Detect which provider
        if os.environ.get('GITHUB_TOKEN'):
            llm_provider = 'github'
            llm_model = 'gpt-4o-mini'
        elif os.environ.get('OPENAI_API_KEY'):
            llm_provider = 'openai'
            llm_model = 'gpt-4o-mini'
        else:
            llm_provider = 'anthropic'
            llm_model = 'claude-3-haiku-20240307'
        print(f"   Using: {llm_provider} / {llm_model}")
    else:
        print("⚠️  No LLM API key found - running in simulation mode")
        print("   Set GITHUB_TOKEN, OPENAI_API_KEY, or ANTHROPIC_API_KEY")
        use_llm = False
        llm_provider = None
        llm_model = None
    
    print()
    
    # Setup workspace
    town_root = Path("./test-generator-town").resolve()
    if town_root.exists():
        print("🗑️  Cleaning up previous workspace...")
        shutil.rmtree(town_root)
    
    print("📁 Creating workspace: test-generator-town")
    
    # Initialize town structure
    town_root.mkdir(parents=True)
    (town_root / ".gastown").mkdir()
    (town_root / "state").mkdir()
    (town_root / "projects").mkdir()
    
    workspace_manager = WorkspaceManager(town_root)
    workspace_manager.create_manager_workspace()
    
    state_manager = StateManager(town_root)
    agent_manager = AgentManager(town_root)
    agent_manager.create_manager()
    
    # Create project
    project_name = "test-gen"
    project_path = town_root / "projects" / project_name
    project_path.mkdir(parents=True)
    (project_path / ".tasks").mkdir()
    
    # Save sample code to workspace
    code_dir = project_path / "src"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "calculator.py").write_text(SAMPLE_CODE)
    print(f"📝 Created sample code: {code_dir / 'calculator.py'}")
    
    # Create task manager
    tm = TaskManager(project_path)
    cm = ConvoyManager(state_manager, tm)
    
    # Define tasks for test generation
    tasks_data = [
        {
            "title": "Analyze calculator.py for testable functions",
            "description": f"""Analyze the following Python code and identify all testable functions.
            
For each function, document:
- Function name and signature
- What the function does
- Input parameters and types
- Return type
- Edge cases to test (especially error conditions)
- Suggested test scenarios

CODE TO ANALYZE:
```python
{SAMPLE_CODE}
```

Output a structured analysis that a test writer can use to create comprehensive tests.""",
            "priority": "high"
        },
        {
            "title": "Write pytest tests for basic operations",
            "description": f"""Write pytest test cases for the basic calculator operations: add, subtract, multiply, divide.

The code being tested:
```python
{SAMPLE_CODE}
```

Requirements:
- Use pytest style (def test_xxx)
- Include docstrings explaining each test
- Test normal cases with various inputs
- Test edge cases (zero, negative numbers, floats)
- Test the divide by zero error case
- Use pytest.raises for exception testing
- Include parametrized tests where appropriate

Output complete, runnable pytest code.""",
            "priority": "high"
        },
        {
            "title": "Write pytest tests for advanced functions",
            "description": f"""Write pytest test cases for the advanced functions: power, factorial, is_even, fibonacci.

The code being tested:
```python
{SAMPLE_CODE}
```

Requirements:
- Use pytest style (def test_xxx)
- Include docstrings for each test
- Test normal cases
- Test edge cases:
  * factorial(0), factorial(1), negative input
  * fibonacci(0), fibonacci(1), negative input
  * power with negative exponents
  * is_even with negative numbers
- Use pytest.raises for ValueError cases
- Use @pytest.mark.parametrize for multiple test values

Output complete, runnable pytest code.""",
            "priority": "high"
        },
        {
            "title": "Create test documentation and conftest.py",
            "description": """Create supporting test infrastructure:

1. A conftest.py file with:
   - Useful fixtures (if any make sense for calculator tests)
   - pytest configuration
   - Any shared test utilities

2. A README for the tests directory explaining:
   - How to run the tests
   - Test organization
   - Coverage expectations
   - How to add new tests

Keep it practical and focused on the calculator module.""",
            "priority": "normal"
        }
    ]
    
    # Create tasks
    print("\n📋 Creating test generation tasks...")
    task_ids = []
    for task_data in tasks_data:
        task = tm.create_task(
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data["priority"]
        )
        task_ids.append(task.id)
        print(f"   ✓ {task.title}")
    
    # Create convoy
    convoy = cm.create_convoy(
        name="Test Suite Generation",
        task_ids=task_ids
    )
    print(f"\n🚚 Created convoy: {convoy.name} ({convoy.id})")
    
    # Run workers
    print("\n" + "=" * 60)
    print("🏃 Running Workers...")
    print("=" * 60)
    
    tasks = tm.list_tasks()
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] 🔧 Worker processing: {task.title}")
        print("-" * 50)
        
        # Spawn worker
        worker = agent_manager.spawn_worker(project_name, task.id)
        print(f"   Worker {worker.id[-12:]} spawned")
        
        # Assign task
        tm.assign_task(task.id, worker.id)
        
        # Run worker with LLM
        workspace = Path(worker.workspace)
        await run_worker(
            worker.id, workspace, town_root, project_name,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        # Show preview of result
        completed_task = tm.get_task(task.id)
        if completed_task and completed_task.result:
            preview = completed_task.result[:300] + "..." if len(completed_task.result) > 300 else completed_task.result
            print(f"📄 Result preview:\n{preview}")
        
        # Cleanup worker
        agent_manager.kill_worker(worker.id)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    completed = sum(1 for t in tm.list_tasks() if t.status == "completed")
    print(f"✅ Completed: {completed}/{len(tasks)} tasks")
    
    print(f"\n📁 Results saved to:")
    print(f"   {project_path / '.tasks' / 'tasks.json'}")
    
    print(f"\n📝 Sample code location:")
    print(f"   {code_dir / 'calculator.py'}")
    
    # Show how to extract test code
    print("\n💡 To extract the generated tests, you can run:")
    print("""
    from pathlib import Path
    from sgt.core.task_manager import TaskManager
    
    tm = TaskManager(Path('./test-generator-town/projects/test-gen'))
    for task in tm.list_tasks():
        if 'pytest' in task.title.lower():
            print(f"=== {task.title} ===")
            print(task.result)
    """)
    
    print("\n🎉 Demo complete!")

if __name__ == "__main__":
    main()
