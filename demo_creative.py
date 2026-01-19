#!/usr/bin/env python
"""Creative Work Demo - Content Generation Project

This demo shows how Simple Gas Town can orchestrate creative tasks like:
- Blog post writing
- Documentation creation
- Marketing copy generation
- Tutorial creation
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

sys.path.insert(0, str(Path(__file__).parent))

from sgt.core.agent_manager import AgentManager
from sgt.core.task_manager import TaskManager
from sgt.core.convoy_manager import ConvoyManager
from sgt.core.workspace import WorkspaceManager
from sgt.storage.state import StateManager
from sgt.agents.worker import run_worker
from sgt.models import TaskPriority

console = Console()


async def main():
    """Run a creative work demo - Blog Content Creation."""
    
    console.print("\n[bold magenta]🎨 Simple Gas Town - Creative Work Demo[/bold magenta]\n")
    console.print("[dim]Orchestrating AI content creation with multiple workers[/dim]\n")
    
    # Setup
    town_root = Path("./creative-town").resolve()
    if town_root.exists():
        import shutil
        shutil.rmtree(town_root)
    
    # 1. Initialize
    console.print("[bold]Step 1: Setting up Creative Studio...[/bold]")
    town_root.mkdir(parents=True)
    (town_root / ".gastown").mkdir()
    (town_root / "state").mkdir()
    (town_root / "projects").mkdir()
    
    workspace_manager = WorkspaceManager(town_root)
    workspace_manager.create_manager_workspace()
    
    state_manager = StateManager(town_root)
    agent_manager = AgentManager(town_root)
    agent_manager.create_manager()
    
    console.print("[green]✓[/green] Creative studio initialized\n")
    
    # 2. Create project
    console.print("[bold]Step 2: Creating 'Tech Blog' project...[/bold]")
    project_name = "tech-blog"
    project_path = town_root / "projects" / project_name
    project_path.mkdir(parents=True)
    (project_path / ".tasks").mkdir()
    
    task_manager = TaskManager(project_path)
    console.print("[green]✓[/green] Project created\n")
    
    # 3. Define creative tasks
    console.print("[bold]Step 3: Defining creative tasks...[/bold]\n")
    
    creative_tasks = [
        {
            "title": "Write blog post: 'Getting Started with Python Async'",
            "description": """Write a beginner-friendly blog post (800-1000 words) covering:
            - What is async/await in Python
            - Why use async programming
            - Basic examples with asyncio
            - Common pitfalls
            - When to use vs when not to use
            
            Tone: Friendly, educational, with code examples
            Target audience: Intermediate Python developers""",
            "priority": TaskPriority.HIGH
        },
        {
            "title": "Create tutorial: 'Building a CLI with Click'",
            "description": """Create a step-by-step tutorial covering:
            - Installing Click
            - Basic command structure
            - Adding options and arguments
            - Subcommands and groups
            - Error handling
            - Complete working example
            
            Include: Code snippets, explanations, best practices
            Format: Markdown with code blocks""",
            "priority": TaskPriority.HIGH
        },
        {
            "title": "Write README for 'simple-gastown' project",
            "description": """Write a comprehensive README.md including:
            - Project overview and value proposition
            - Key features with emojis
            - Quick start guide
            - Installation instructions
            - Basic usage examples
            - Architecture diagram (ASCII art)
            - Contributing guidelines
            - License
            
            Tone: Professional, exciting, clear
            Target: Open source contributors and users""",
            "priority": TaskPriority.HIGH
        },
        {
            "title": "Generate marketing copy for landing page",
            "description": """Create compelling landing page copy:
            - Hero headline (attention-grabbing)
            - Subheading (value proposition)
            - 3 key benefits (with icons/emojis)
            - Feature highlights (bullet points)
            - Call-to-action text
            - Social proof section
            
            Tone: Exciting, benefit-focused, conversion-optimized
            Target: Developers looking for task orchestration""",
            "priority": TaskPriority.NORMAL
        },
        {
            "title": "Create API documentation",
            "description": """Write API documentation for task management:
            - Overview of the API
            - Authentication (if any)
            - Endpoints:
              * POST /tasks - Create task
              * GET /tasks - List tasks
              * GET /tasks/:id - Get task details
              * PUT /tasks/:id - Update task
            - Request/response examples
            - Error codes and handling
            
            Format: Clear, structured, with examples""",
            "priority": TaskPriority.NORMAL
        },
        {
            "title": "Write social media posts for launch",
            "description": """Create social media content for project launch:
            - 5 Twitter/X posts (280 chars each)
            - 2 LinkedIn posts (longer form)
            - 3 Reddit post titles + descriptions
            - Key hashtags
            
            Focus: Features, benefits, call-to-action
            Include: Emojis, engagement hooks""",
            "priority": TaskPriority.LOW
        }
    ]
    
    tasks = []
    for task_def in creative_tasks:
        task = task_manager.create_task(
            title=task_def["title"],
            description=task_def["description"],
            priority=task_def["priority"]
        )
        tasks.append(task)
        console.print(f"[cyan]📝[/cyan] {task.title}")
    
    console.print(f"\n[green]✓[/green] Created {len(tasks)} creative tasks\n")
    
    # 4. Create convoy
    console.print("[bold]Step 4: Organizing into 'Content Launch Campaign' convoy...[/bold]")
    convoy_manager = ConvoyManager(state_manager, task_manager)
    convoy = convoy_manager.create_convoy(
        name="Content Launch Campaign",
        task_ids=[t.id for t in tasks]
    )
    console.print(f"[green]✓[/green] Convoy created with {len(tasks)} tasks\n")
    
    # 5. Show what would happen with LLM workers
    console.print("[bold]Step 5: Simulating content creation workflow...[/bold]\n")
    
    console.print(Panel(
        """[yellow]⚡ Phase 1 Note:[/yellow]

In the current Phase 1, workers simulate work. Each task would take 2 seconds.

[green]🚀 In Phase 3 (with LLM integration):[/green]

Each worker would:
1. Read the creative brief from their hook
2. Call OpenAI/Claude/GitHub Copilot with the description
3. Generate actual content (blog posts, docs, etc.)
4. Save the content to files in their workspace
5. Report the completed content back

[cyan]💡 Parallel Execution:[/cyan]
All 6 content pieces could be generated simultaneously by different workers!

[magenta]⏱️ Time Savings:[/magenta]
Instead of writing 6 pieces sequentially (hours), 
AI workers complete them in parallel (~2-3 minutes total)""",
        title="[bold]How It Would Work[/bold]",
        border_style="magenta"
    ))
    
    # Check for LLM availability
    import os
    use_llm = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    llm_provider = None
    if os.environ.get("GITHUB_TOKEN"):
        llm_provider = "github"
        console.print("[green]✓ GitHub Models API detected - using real LLM![/green]\n")
    elif os.environ.get("OPENAI_API_KEY"):
        llm_provider = "openai"
        console.print("[green]✓ OpenAI API detected - using real LLM![/green]\n")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        llm_provider = "anthropic"
        console.print("[green]✓ Anthropic API detected - using real LLM![/green]\n")
    else:
        console.print("[yellow]⚠ No LLM API key found - using simulation mode[/yellow]\n")
    
    console.print("\n[bold]Running first 3 tasks as demonstration...[/bold]\n")
    
    # Execute first 3 tasks as demo
    for task in tasks[:3]:
        console.print(f"[cyan]🤖 Processing:[/cyan] {task.title}")
        
        # Spawn worker
        worker = agent_manager.spawn_worker(project_name, task.id, priority=task.priority)
        console.print(f"  [dim]Worker {worker.id[-12:]} spawned[/dim]")
        
        # Assign
        task_manager.assign_task(task.id, worker.id)
        
        # Run worker with LLM if available
        workspace = Path(worker.workspace)
        await run_worker(
            worker.id, workspace, town_root, project_name,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model="gpt-4o-mini" if llm_provider == "github" else None
        )
        
        # Show simulated output
        completed_task = task_manager.get_task(task.id)
        console.print(f"  [green]✓ Completed:[/green] {completed_task.result[:80]}...")
        
        # In Phase 3, you'd see actual content here:
        if "blog post" in task.title.lower():
            console.print(f"  [dim]📄 Output: blog-post-python-async.md (1,200 words)[/dim]")
        elif "tutorial" in task.title.lower():
            console.print(f"  [dim]📄 Output: tutorial-cli-click.md (2,500 words)[/dim]")
        elif "README" in task.title.lower():
            console.print(f"  [dim]📄 Output: README.md (comprehensive, 150 lines)[/dim]")
        
        console.print()
        
        # Cleanup
        agent_manager.kill_worker(worker.id)
    
    # 6. Show convoy progress
    console.print("[bold]Step 6: Campaign Progress...[/bold]\n")
    progress = convoy_manager.get_convoy_progress(convoy.id)
    
    console.print(Panel(
        f"""[cyan]Content Launch Campaign[/cyan]

📊 [bold]Progress:[/bold] {progress['completed']}/{progress['total']} tasks completed
✅ Completed: {progress['completed']}
🔵 In Progress: {progress['in_progress']}
⚪ Pending: {progress['pending']}

[green]Progress: {progress['percent_complete']:.0f}%[/green]

[dim]Completed Content:[/dim]
• Blog post: Python Async Guide
• Tutorial: Building CLI with Click
• README: Project documentation

[yellow]Remaining:[/yellow]
• Marketing landing page copy
• API documentation
• Social media content""",
        border_style="cyan"
    ))
    
    # 7. Show sample output
    console.print("\n[bold]Step 7: Sample Generated Content Preview...[/bold]\n")
    
    sample_content = """# Getting Started with Python Async

Are you tired of waiting for slow I/O operations to block your Python applications? 
Async programming with Python's `asyncio` might be exactly what you need!

## What is Async/Await?

Async/await is Python's way of writing asynchronous code that can handle multiple 
operations concurrently without blocking. Instead of waiting for each operation to 
complete before moving to the next, async code can switch between tasks while 
waiting for I/O operations.

## Why Use Async Programming?

**Perfect for:**
- Web scraping multiple URLs
- API calls to multiple services
- Database queries
- File I/O operations
- Network requests

**Key Benefits:**
- 🚀 Better performance for I/O-bound tasks
- 💡 Cleaner code than threading
- 🎯 Efficient resource usage

## Basic Example

```python
import asyncio

async def fetch_data(url):
    # Simulate API call
    await asyncio.sleep(1)
    return f"Data from {url}"

async def main():
    # Run three requests concurrently
    results = await asyncio.gather(
        fetch_data("api.example.com/1"),
        fetch_data("api.example.com/2"),
        fetch_data("api.example.com/3")
    )
    print(results)

# Run the async code
asyncio.run(main())
```

[... rest of blog post would continue ...]"""
    
    console.print(Panel(
        Markdown(sample_content),
        title="[bold]Generated Blog Post (Preview)[/bold]",
        border_style="green"
    ))
    
    # Summary
    console.print("\n[bold green]✨ Creative Work Demo Complete![/bold green]\n")
    
    console.print(Panel(
        """[bold]What This Demo Shows:[/bold]

🎨 [cyan]Content Types:[/cyan]
   • Blog posts and articles
   • Technical tutorials
   • Documentation (README, API docs)
   • Marketing copy
   • Social media content

🤖 [cyan]Workflow Orchestration:[/cyan]
   • Multiple creative tasks in parallel
   • Organized into campaigns (convoys)
   • Each worker gets clear brief
   • Automatic progress tracking
   • Results aggregation

⚡ [cyan]Phase 3 Vision:[/cyan]
   • Workers use LLM to generate actual content
   • 6 pieces of content in ~3 minutes
   • Consistent quality and style
   • Automatic file creation
   • Review and iterate

💡 [cyan]Use Cases:[/cyan]
   • Content marketing campaigns
   • Documentation sprints
   • Multi-language translation
   • Code example generation
   • Educational material creation""",
        border_style="magenta"
    ))
    
    console.print(f"\n[dim]Demo files in: {town_root}[/dim]\n")


if __name__ == "__main__":
    asyncio.run(main())
