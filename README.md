# GreenNode AgentBase Skills - User Guide

Setup and usage guide for GreenNode AgentBase skills across **Claude Code**, **Cursor**, and **OpenAI Codex**.

---

## Quick Start

```bash
# Copy skills into your project
cp -r <skills-repo>/.claude/skills/ <your-project>/.claude/skills/

# Launch Claude Code
cd <your-project>
claude

# Then use slash commands or natural language
/agentbase-wizard                    # Guided wizard from A to Z
/agentbase-init my-agent             # Scaffold a new project
/agentbase-deploy                    # Deploy agent
"Create a new agent with LangGraph"  # Claude picks the right skill
```

---

## Setup by Tool

All skills follow the [SKILL.md standard](https://www.mintlify.com/blog/skill-md). Copy them into the correct directory and they're auto-detected.

### Claude Code

```bash
# Project-level
cp -r <skills-repo>/.claude/skills/ <your-project>/.claude/skills/

# Or global (all projects)
cp -r <skills-repo>/.claude/skills/* ~/.claude/skills/
```

```bash
cd <your-project> && claude
```

Use `/skill-name` or natural language — Claude auto-picks the right skill.

### Cursor (v2.4+)

```bash
# Project-level
cp -r <skills-repo>/.claude/skills/ <your-project>/.cursor/skills/

# Or global
cp -r <skills-repo>/.claude/skills/* ~/.cursor/skills/
```

```bash
cd <your-project> && cursor .
```

Type `/` in Agent chat to search skills. For deploy & monitor, open terminal and run `claude`.

### OpenAI Codex

```bash
# Project-level
cp -r <skills-repo>/.claude/skills/ <your-project>/.agents/skills/

# Or global
cp -r <skills-repo>/.claude/skills/* ~/.agents/skills/
```

```bash
export OPENAI_API_KEY="your-key"
cd <your-project> && codex
```

Use `$skill-name` or natural language. For deploy & monitor, switch to Claude Code.

### Tool Comparison

| Feature | Claude Code | Cursor (v2.4+) | Codex |
|---------|:-----------:|:---------------:|:-----:|
| Skills directory | `.claude/skills/` | `.cursor/skills/` | `.agents/skills/` |
| Slash commands | `/skill-name` | `/skill-name` | `$skill-name` |
| Auto API calls | Yes | No | Limited |
| Full deploy pipeline | Yes | No | No |
| Monitoring/Logs | Yes | No | No |
| **Best for** | **Full lifecycle** | **Writing code** | **Writing code** |

> **Recommended workflow:** Write code in **Cursor**, deploy & monitor with **Claude Code**.

---

## Skills Reference

### Lifecycle Overview

```
Scaffold → Configure → Code → Test → Deploy → Monitor → Teardown
```

### All Skills

| # | Command | What it does |
|---|---------|-------------|
| 1 | `/agentbase-wizard` | 9-step guided wizard — start here if you're new |
| 2 | `/agentbase` | Platform reference & information lookup |
| 3 | `/agentbase-init` | Scaffold a new agent project (FastAPI, LangChain, LangGraph) |
| 4 | `/agentbase-identity` | Register/manage agent identity on the platform |
| 5 | `/agentbase-auth` | Store API keys & OAuth2 credentials for external services |
| 6 | `/agentbase-memory` | Manage conversation history & long-term memory stores |
| 7 | `/aip` | Create API keys & browse LLM models on AI Platform |
| 8 | `/agentbase-test` | Validate code, test locally, test in Docker, preflight check |
| 9 | `/agentbase-deploy` | End-to-end deploy: build → push → deploy → verify |
| 10 | `/agentbase-runtime` | CRUD runtimes, endpoints, versions, autoscaling |
| 11 | `/agentbase-observe` | View runtime logs, endpoint logs, CPU/RAM metrics |
| 12 | `/agentbase-status` | Dashboard of all resources (identities, runtimes, memory, etc.) |
| 13 | `/vcr` | Manage Docker repos & robot accounts on vCR registry |
| 14 | `/agentbase-teardown` | Delete all resources for a project (with dry-run) |
| 15 | `/skill-creator` | Create, improve, eval, and benchmark skills |

### Grouped by Stage

```
┌─────────────────────────────────────────────────────────┐
│  GETTING STARTED                                        │
│  /agentbase-wizard ─── Start here (guided A→Z)          │
│  /agentbase ────────── Platform reference                │
├─────────────────────────────────────────────────────────┤
│  BUILD                                                  │
│  /agentbase-init ───── Scaffold project                  │
├─────────────────────────────────────────────────────────┤
│  CONFIGURE                                              │
│  /agentbase-identity ─ Register agent                    │
│  /aip ────────────────  API keys & LLM models            │
│  /agentbase-auth ───── External API credentials          │
│  /agentbase-memory ─── Memory service                    │
├─────────────────────────────────────────────────────────┤
│  TEST & DEPLOY                                          │
│  /agentbase-test ───── Test before deploy                │
│  /agentbase-deploy ─── End-to-end deploy                 │
│  /agentbase-runtime ── Runtime management                │
├─────────────────────────────────────────────────────────┤
│  OPERATE                                                │
│  /agentbase-observe ── Logs & metrics                    │
│  /agentbase-status ─── Dashboard                         │
├─────────────────────────────────────────────────────────┤
│  ADVANCED                                               │
│  /vcr ────────────────  Container Registry               │
│  /agentbase-teardown ─ Delete resources                  │
│  /skill-creator ────── Create/improve skills             │
└─────────────────────────────────────────────────────────┘
```

---

## Practical Examples

### Create a Chatbot from Zero

```bash
/agentbase-init my-chatbot --langgraph      # Scaffold
/aip api-keys create my-chatbot-key         # LLM access
/agentbase-memory create                    # Memory (optional)
/agentbase-test local                       # Test
/agentbase-deploy my-chatbot                # Deploy
/agentbase-observe runtime-logs <id>        # Monitor
```

### First Time? Use the Wizard

```bash
/agentbase-wizard              # Follow 9 steps from setup to deploy
/agentbase-wizard resume       # Come back later and continue
```

### Debug a Failing Agent

```bash
/agentbase-observe runtime-logs <runtime-id>
/agentbase-observe endpoint-logs <runtime-id> <endpoint-id>
/agentbase-observe metrics <runtime-id>
```

### Tear Down a Project

```bash
/agentbase-teardown my-chatbot --dry-run    # Preview first
/agentbase-teardown my-chatbot              # Delete all resources
```

---

## FAQ & Troubleshooting

**Skills not showing up?**
- Verify skills directory exists (`.claude/skills/`, `.cursor/skills/`, or `.agents/skills/`)
- Each skill must have a valid `SKILL.md` with `name` and `description` frontmatter
- Restart the tool

**"401 Unauthorized" error?**
- Check `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` are set
- Verify Service Account has required IAM policies

**"OOMKilled" during deployment?**
- Choose a larger flavor when creating the runtime
- Optimize code to reduce memory usage

**How to resume a session?**
- State is saved in `.agentbase-state.json` — use `/agentbase-wizard resume` or any skill will detect existing state

---

## Important Notes

1. **Verify credentials first** – most errors are caused by missing IAM credentials
2. **Run `/agentbase-test validate`** before deploying
3. **Use `--dry-run`** with teardown to preview before deleting
4. **Never commit `.env` files** – only commit `.env.example`
5. **Use the wizard** (`/agentbase-wizard`) if it's your first time
