# System Architecture

## Overview

The NinjaSquad is a multi-agent collaborative system where AI agents work together to build a project application. The system is designed around asynchronous collaboration with periodic synchronization.

## 🚨 CRITICAL: Workflow Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROJECT INITIALIZATION FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PHASE 1: Nova (PM) Initializes Project                                    │
│   ══════════════════════════════════════                                    │
│   1. Nova completes onboarding                                              │
│   2. Nova interviews Human (stakeholders) via Slack                          │
│   3. Nova writes PRD document → agent-docs/PRD.md                           │
│   4. Nova creates GitHub Issues for all tasks                               │
│   5. Nova assigns issues to appropriate agents                              │
│                                                                              │
│   PHASE 2: Other Agents Start Work                                          │
│   ════════════════════════════════════                                      │
│   • Pixel, Bolt, Scout WAIT for:                                            │
│     - PRD document to exist (agent-docs/PRD.md)                             │
│     - GitHub Issues assigned to them                                        │
│   • Only then do they begin their work                                      │
│                                                                              │
│   WAKE UP INSTRUCTION                                                        │
│   ═══════════════════                                                        │
│   When any agent receives "WAKE UP" instruction:                            │
│   → Run: python orchestrator.py                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Startup Sequence

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    NOVA     │     │    PIXEL    │     │    BOLT     │     │    SCOUT    │
│     PM      │     │     UX      │     │     Dev     │     │     QA      │
├─────────────┤     ├─────────────┤     ├─────────────┤     ├─────────────┤
│ 1. Onboard  │     │ 1. Onboard  │     │ 1. Onboard  │     │ 1. Onboard  │
│ 2. Interview│     │ 2. Wait for │     │ 2. Wait for │     │ 2. Wait for │
│    Human    │     │    PRD +    │     │    PRD +    │     │    PRD +    │
│ 3. Write PRD│     │    Issues   │     │    Issues   │     │    Issues   │
│ 4. Create   │────▶│ 3. Check    │────▶│ 3. Check    │────▶│ 3. Check    │
│    Issues   │     │    assigned │     │    assigned │     │    assigned │
│ 5. Run      │     │    tasks    │     │    tasks    │     │    tasks    │
│ orchestrator│     │ 4. Run      │     │ 4. Run      │     │ 4. Run      │
│             │     │ orchestrator│     │ orchestrator│     │ orchestrator│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## Core Components

### 1. Agent Layer

Four specialized agents, each with distinct responsibilities:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          AGENT LAYER                                    │
├─────────────┬─────────────┬─────────────┬─────────────────────────────┤
│    NOVA     │    PIXEL    │    BOLT     │         SCOUT               │
│     PM      │     UX      │     Dev     │          QA                 │
├─────────────┼─────────────┼─────────────┼─────────────────────────────┤
│ • Planning  │ • Wireframes│ • Frontend  │ • Test Plans                │
│ • PRD       │ • Mockups   │ • Backend   │ • Bug Reports               │
│ • Issues    │ • UX Flows  │ • APIs      │ • Validation                │
│ • Reviews   │ • Assets    │ • Deploy    │ • Regression                │
│ • Coord.    │             │             │                             │
└─────────────┴─────────────┴─────────────┴─────────────────────────────┘
```

### 2. Communication Layer

All inter-agent and human-agent communication flows through Slack using the `slack_interface.py` CLI tool:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SLACK: #your-channel                              │
│                                                                      │
│  Message Types:                                                      │
│  • @nova - PM directives, task assignments                          │
│  • @pixel - Design updates, mockup shares                           │
│  • @bolt - Code updates, technical questions                        │
│  • @scout - Test results, bug reports                               │
│  • @stakeholders - Human direction, feedback, approvals             │
│                                                                      │
│  Threads: Used for focused discussions on specific topics           │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Persistence Layer

#### GitHub Repository
- Source code
- Issues and project tracking (PRIMARY TASK SOURCE)
- Pull requests and code reviews
- Documentation
- PRD document (agent-docs/PRD.md)

#### Memory Files
- Agent-specific context persistence
- Work history and decisions
- Cross-session continuity

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                               │
├────────────────────────────────┬────────────────────────────────────┤
│         GITHUB                 │            MEMORY FILES            │
├────────────────────────────────┼────────────────────────────────────┤
│ • Code commits                 │ • nova_memory.md                   │
│ • Issues/PRs (TASK SOURCE)     │ • pixel_memory.md                  │
│ • Reviews/Comments             │ • bolt_memory.md                   │
│ • PRD.md (Requirements)        │ • scout_memory.md                  │
└────────────────────────────────┴────────────────────────────────────┘
```

### 4. Orchestration Layer

The orchestrator manages the agent lifecycle:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                    │
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  Scheduler  │───▶│ Sync Manager│───▶│   Agents    │             │
│  │  (Hourly)   │    │             │    │             │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                      │
│  Responsibilities:                                                   │
│  • Trigger hourly syncs                                             │
│  • Coordinate agent wake-up sequence                                │
│  • Manage sync meeting flow                                         │
│  • Handle failures and retries                                      │
│                                                                      │
│  NOTE: Monitor process only runs for Nova (PM)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Project Initialization Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PROJECT INITIALIZATION                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Human (stakeholders)                                                 │
│       │                                                               │
│       │ "WAKE UP Nova"                                               │
│       ▼                                                               │
│  ┌─────────┐                                                         │
│  │  NOVA   │──── 1. Complete onboarding                              │
│  │   PM    │──── 2. Interview Human via Slack                        │
│  └────┬────┘──── 3. Write PRD (agent-docs/PRD.md)                    │
│       │     ──── 4. Create GitHub Issues                             │
│       │     ──── 5. Assign issues to agents                          │
│       │     ──── 6. Run orchestrator                                 │
│       │                                                               │
│       ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    GitHub Issues Created                      │    │
│  │  • Design tasks → assigned to @pixel                         │    │
│  │  • Dev tasks → assigned to @bolt                             │    │
│  │  • QA tasks → assigned to @scout                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                               │
│       ▼                                                               │
│  Human: "WAKE UP Pixel/Bolt/Scout"                                   │
│       │                                                               │
│       ▼                                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                              │
│  │  PIXEL  │  │  BOLT   │  │  SCOUT  │                              │
│  │   UX    │  │   Dev   │  │   QA    │                              │
│  └────┬────┘  └────┬────┘  └────┬────┘                              │
│       │            │            │                                     │
│       └────────────┴────────────┘                                    │
│                    │                                                  │
│                    ▼                                                  │
│       Check PRD + GitHub Issues → Start Work                         │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Hourly Sync Cycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  WAKE UP │────▶│   SYNC   │────▶│   WORK   │────▶│  COMMIT  │
│          │     │ MEETING  │     │  PHASE   │     │ & MEMORY │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │
     ▼                ▼                ▼                ▼
 Orchestrator    Slack Channel    Independent      GitHub +
triggers all    #your-channel    task execution   Memory files
agents          Nova leads
```

### Detailed Sync Flow

```
Time: T+0 (Sync Start)
├── Orchestrator triggers sync
├── All agents wake up
├── Agents read their memory files
└── Agents join #your-channel

Time: T+1 (Standup)
├── Nova posts sync agenda
├── Each agent reports:
│   ├── What they completed
│   ├── What they're working on
│   └── Any blockers
└── Nova assigns/clarifies tasks

Time: T+2 to T+55 (Work Phase)
├── Agents work independently
├── Async communication in Slack as needed
├── Code commits to GitHub
└── Design uploads, test runs, etc.

Time: T+55 (Wrap Up)
├── Agents summarize work
├── Update memory files
├── Post summary to Slack
└── Agents go idle until next sync
```

## Integration Points

### Tools Available

All agents have access to the following tools:

| Tool | Available To | Capabilities |
|------|--------------|--------------|
| **slack_interface.py** | All agents | Send/read messages, list channels/users, manage communication |
| **tavily_client.py** | All agents | Web research — search, extract, crawl, map, deep research via Tavily MCP |
| **utils/ library** | All agents | AI model access — chat, image generation, video generation, embeddings |
| **Image Generation** | Pixel (primary) | Generate UI mockups, wireframes, design concepts |
| **Internet Search** | All agents | Web search for research, documentation, best practices |
| **GitHub CLI** | All agents | Code commits, issues, PRs, reviews |

### AI Models & Utility Library

All agents have access to AI models through the NinjaTech LiteLLM gateway via a ready-to-use Python utility library:

```
utils/
├── __init__.py          # Package init with quick-start docs
├── litellm_client.py    # Core config, auth, model aliases
├── chat.py              # Chat completions (text generation)
├── images.py            # Image generation (gemini-image, gpt-image)
├── video.py             # Video generation (sora, sora-pro)
└── embeddings.py        # Text embeddings (embed-small, embed-large)
```

#### Quick Import Reference

```python
from utils.chat import chat, chat_json, chat_stream     # Text generation
from utils.images import generate_image, generate_images  # Image generation
from utils.video import generate_video                     # Video generation
from utils.embeddings import embed, cosine_similarity      # Embeddings
from tavily_client import Tavily                           # Web research
```

#### Model Recommendations

| Task | Recommended Model | Notes |
|------|-------------------|-------|
| Complex reasoning | `claude-opus` | Highest quality |
| General tasks | `claude-sonnet` | Best balance of quality/speed |
| Quick responses | `claude-haiku` | Fastest |
| Image generation | `gemini-image` | ✅ Most reliable — use as default |
| Video generation | `sora` | ~90s generation, max 8s video |
| Embeddings | `embed-small` | 1536 dimensions |

⚠️ **Important:** `gpt-image` has intermittent gateway errors. Always prefer `gemini-image` and use `gpt-image` only as a fallback.

📖 **Full details:** [MODELS.md](MODELS.md) (complete model catalog) and [LITELLM_GUIDE.md](LITELLM_GUIDE.md) (usage guide with code examples, error handling, and patterns for building custom utilities).

### Slack Interface Usage

The `slack_interface.py` CLI tool provides all Slack communication capabilities:

```bash
# Read messages from default channel
python slack_interface.py read
python slack_interface.py read -l 50  # Last 50 messages

# Send messages as an agent
python slack_interface.py say "Sprint planning at 2pm"

# Configuration
python slack_interface.py config --set-channel "#your-channel"
python slack_interface.py config --set-agent nova

# Other operations
python slack_interface.py channels    # List channels
python slack_interface.py users       # List users
python slack_interface.py history "#channel"  # Get specific channel history
```

See [SLACK_INTERFACE.md](SLACK_INTERFACE.md) for complete documentation.

### Deployment & Networking

Services running inside the sandbox are exposed to the internet via an external reverse proxy. Each port gets a unique public HTTPS URL based on the sandbox metadata in `/dev/shm/sandbox_metadata.json`.

Key topics covered:
- **Public URL pattern** for any port
- **CORS configuration** for frontend ↔ backend communication
- **Next.js / Express** proxy settings
- **Reserved ports** to avoid conflicts
- **Automatic URL conversion** in Slack messages (`0.0.0.0:<port>` → public URL)

See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete deployment and networking guide.

### GitHub Integration (via CLI)

```bash
# Key capabilities via GitHub CLI
gh issue create --title "Bug: ..." --body "..."
gh issue list --assignee @me
gh pr create --title "Feature: ..." --body "..."
gh pr review --approve
git commit -m "feat: ..."
git push origin main
```

## Running the Orchestrator

### When to Run

**Run the orchestrator after completing onboarding:**

```bash
python orchestrator.py
```

### What It Does

| Agent | Processes Started |
|-------|-------------------|
| Nova | Work + Monitor (both processes) |
| Pixel | Work only |
| Bolt | Work only |
| Scout | Work only |

**Note:** The monitor process (Slack watcher) only runs for Nova because Nova is the PM who needs to respond to team mentions and coordinate.

### Command Options

```bash
python orchestrator.py                    # Run work + monitor (Nova) or work only (others)
python orchestrator.py --task "Do X"      # Run single task
python orchestrator.py --list             # List all agents
python orchestrator.py --test             # Run capability tests
```

## Security Considerations

1. **Token Management**: All API tokens stored securely in `/dev/shm/mcp-token`
2. **Least Privilege**: Each agent has only necessary permissions
3. **Audit Trail**: All actions logged in Slack and GitHub
4. **Human Override**: Humans can intervene at any point via Slack

## Scalability

The system is designed to be extensible:
- New agents can be added by implementing `BaseAgent`
- Additional integrations (Jira, Figma, etc.) can be added
- Multiple projects can run in parallel with separate channels
