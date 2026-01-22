# Simple Gas Town System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SIMPLE GAS TOWN                                   │
│                   Multi-Agent Task Orchestration                         │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                            CLI LAYER                                      │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │
│  │  init  │  │  task  │  │ worker │  │ convoy │  │ assign │            │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         CORE BUSINESS LOGIC                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ TaskManager  │  │AgentManager  │  │ConvoyManager │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│         ↓                  ↓                  ↓                           │
│  ┌──────────────────────────────────────────────────┐                   │
│  │           WorkspaceManager                        │                   │
│  └──────────────────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                                     │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐                        │
│  │   State   │    │  Mailbox  │    │   Hooks   │                        │
│  │ (agents,  │    │ (messages)│    │  (work    │                        │
│  │  convoys) │    │           │    │assignment)│                        │
│  └───────────┘    └───────────┘    └───────────┘                        │
│       ↓                 ↓                 ↓                               │
│  ┌───────────────────────────────────────────────┐                      │
│  │           JSON Files on Disk                   │                      │
│  └───────────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         GIT LAYER (Phase 2)                               │
│  ┌────────────────────────────────────────────────┐                      │
│  │             WorktreeManager                     │                      │
│  │  • Create worktree per worker                  │                      │
│  │  • Isolated branch per task                    │                      │
│  │  • Commit generated code                       │                      │
│  │  • Cleanup on worker kill                      │                      │
│  └────────────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         LLM LAYER (Phase 3)                               │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐                     │
│  │   GitHub   │    │   OpenAI   │    │ Anthropic  │                     │
│  │   Models   │    │    API     │    │    API     │                     │
│  └────────────┘    └────────────┘    └────────────┘                     │
│        ↓                  ↓                 ↓                            │
│  ┌───────────────────────────────────────────────┐                      │
│  │  Auto-detect from: GITHUB_TOKEN, OPENAI_API_KEY│                      │
│  └───────────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         AGENT LAYER                                       │
│  ┌────────────────┐              ┌────────────────┐                      │
│  │    Manager     │              │    Worker      │                      │
│  │  (persistent)  │ ◄─messages─► │  (ephemeral)   │                      │
│  │                │              │                │                      │
│  │ • Create tasks │              │ • Read hook    │                      │
│  │ • Spawn workers│              │ • Call LLM     │                      │
│  │ • Track convoy │              │ • Extract code │                      │
│  │                │              │ • Write files  │                      │
│  │                │              │ • Git commit   │                      │
│  │                │              │ • Self-destruct│                      │
│  └────────────────┘              └────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                            DATA FLOW
═══════════════════════════════════════════════════════════════════════════

1. USER → CLI
   │
   ├─► sgt task create "Fix bug"
   │   └─► TaskManager.create_task()
   │       └─► tasks.json (persisted)
   │
   ├─► sgt assign task-123
   │   └─► AgentManager.spawn_worker()
   │       ├─► Create workspace
   │       ├─► Write hook.json
   │       ├─► Send mailbox message
   │       └─► agents.json (persisted)
   │
   └─► sgt worker run worker-456
       └─► Worker.run()
           ├─► Read hook.json
           ├─► Load task from tasks.json
           ├─► Execute (simulate in Phase 1)
           ├─► Update tasks.json
           ├─► Send completion to mailbox
           └─► Self-destruct

═══════════════════════════════════════════════════════════════════════════
                          FILE STRUCTURE
═══════════════════════════════════════════════════════════════════════════

~/gastown/
│
├── .gastown/
│   └── config.json              # Global configuration
│
├── state/
│   ├── agents.json              # All active agents
│   └── convoys.json             # Active convoys
│
├── manager/
│   ├── INSTRUCTIONS.md          # Manager system prompt
│   └── mailbox/                 # Manager's inbox
│       └── *.json               # Messages
│
└── projects/
    └── my-app/
        ├── .tasks/
        │   └── tasks.json       # All tasks for project
        │
        └── workers/             # Active worker workspaces
            └── worker-001/
                ├── INSTRUCTIONS.md   # Worker instructions
                ├── hook.json         # Current assignment
                ├── state.json        # Worker state
                ├── mailbox/          # Worker inbox
                │   └── *.json
                └── worktree/         # Git worktree (isolated branch)
                    └── *.py          # Generated code files

═══════════════════════════════════════════════════════════════════════════
                       PROJECT SCAFFOLDING
═══════════════════════════════════════════════════════════════════════════

test_generator_town/              # POC: Generate tests for repos
├── __init__.py
├── __main__.py                   # CLI entry point
├── config.py                     # Configuration models
├── runner.py                     # Execution engine
└── configs/
    └── project.yaml              # Target repo configuration

town_scaffolding/                 # Template for new projects
├── __init__.py
├── __main__.py
├── config.py
├── runner.py
└── configs/
    └── project.yaml

═══════════════════════════════════════════════════════════════════════════
                        MESSAGE FLOW
═══════════════════════════════════════════════════════════════════════════

Manager                           Worker
   │                                 │
   │  1. Spawn worker                │
   ├──────────────────────────────► │
   │  (create workspace + hook)      │
   │                                 │
   │  2. Work assignment message     │
   ├─────────mailbox────────────►   │
   │                                 │
   │                                 │ 3. Execute task
   │                                 ├────────────►
   │                                 │
   │  4. Completion message          │
   │ ◄────────mailbox───────────────┤
   │                                 │
   │                                 │ 5. Self-destruct
   │                                 └────────────►
   │
   ▼

═══════════════════════════════════════════════════════════════════════════
                        STATE TRANSITIONS
═══════════════════════════════════════════════════════════════════════════

Task:
  open → in_progress → completed
                   └→ failed

Worker:
  idle → running → completed
                └→ failed

Convoy:
  active → completed

═══════════════════════════════════════════════════════════════════════════
                      CLI COMMAND OVERVIEW
═══════════════════════════════════════════════════════════════════════════

Initialization:
  sgt init <path>                  # Create new town
  sgt project add <name>           # Add project
  sgt status                       # Show system status

Task Management:
  sgt task create <title>          # Create task
  sgt task list --project <name>   # List tasks
  sgt task show <task-id>          # Show task details
  sgt task update <task-id>        # Update task status

Worker Management:
  sgt worker spawn <task-id>       # Spawn worker
  sgt worker list                  # List workers
  sgt worker run <worker-id>       # Run worker
  sgt worker kill <worker-id>      # Kill worker
  sgt worker logs <worker-id>      # View worker logs

Convoy (Batch) Management:
  sgt convoy create <name> <tasks> # Create convoy
  sgt convoy list                  # List convoys
  sgt convoy status <convoy-id>    # Show progress

Combined Operations:
  sgt assign <task-id>             # Spawn + assign + hook

═══════════════════════════════════════════════════════════════════════════
