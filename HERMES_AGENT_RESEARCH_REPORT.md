# Hermes Agent — Deep Research Report for Jemma Adaptation

**Prepared:** 2026-04-11  
**Purpose:** Evaluate NousResearch Hermes Agent as architectural reference for building Jemma (Gemma 4 local agent)

---

## 1. Repository Identification

| Field | Value |
|-------|-------|
| **URL** | https://github.com/NousResearch/hermes-agent |
| **License** | **MIT** (fully permissive) |
| **Stars** | 56,900+ |
| **Forks** | 7,500+ |
| **Contributors** | 382 |
| **Language** | Python 94%, TeX 2.8%, Shell 0.6% |
| **Latest Release** | v0.8.0 (2026-04-08) |
| **Commits** | 3,848 |
| **Tests** | ~3,000 (pytest) |
| **Tagline** | "The agent that grows with you" |

**Previously known as:** OpenClaw → renamed to Hermes Agent. Migration path exists (`hermes claw migrate`).

---

## 2. License Analysis

### What the MIT License Permits

The MIT license is maximally permissive:

- ✅ **Copy directly** — entire files, modules, or subsystems
- ✅ **Modify and adapt** — change anything for Gemma 4 compatibility
- ✅ **Commercial use** — hackathon submissions, production deployment
- ✅ **Distribute** — share derivative works
- ✅ **Sublicense** — apply any license to your derivative

### Requirements

- Must include the MIT copyright notice and permission notice in copies
- No warranty implied

### Practical Implication for Jemma

**You can legally copy any and all code from Hermes Agent**, as long as you include their copyright notice. For a hackathon, this is ideal — you can fork the entire repo, strip what you don't need, and rebuild around Gemma 4.

---

## 3. Architecture Analysis

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────┐
│                    Entry Points                       │
│  CLI (cli.py)   Gateway (gateway/run.py)   ACP      │
│  Batch Runner   API Server    Python Library         │
└────────┬───────────────┬──────────────┬──────────────┘
         │               │              │
         ▼               ▼              ▼
┌─────────────────────────────────────────────────────┐
│               AIAgent (run_agent.py)                 │
│  ~9,200 lines — the core conversation loop           │
│                                                      │
│  Prompt Builder → Provider Resolution → Tool Dispatch│
│  Context Compression → Session Persistence           │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│         Tool Registry (tools/registry.py)            │
│  47 built-in tools across 15+ toolsets               │
│  Self-registering at import time                     │
└─────────────────────────────────────────────────────┘
```

### 3.2 Key Files

| File | Purpose | Size |
|------|---------|------|
| `run_agent.py` | AIAgent class — core conversation loop | ~9,200 lines |
| `cli.py` | HermesCLI — interactive terminal UI | ~8,500 lines |
| `model_tools.py` | Tool discovery, schema collection, dispatch | Orchestration layer |
| `toolsets.py` | Tool groupings and platform presets | Config |
| `hermes_state.py` | SQLite session/state DB with FTS5 | Persistence |
| `agent/prompt_builder.py` | System prompt assembly | Core |
| `agent/context_compressor.py` | Lossy summarization when approaching limits | Core |
| `tools/registry.py` | Central tool registry | Singleton |
| `cron/jobs.py` | Job model, storage, atomic R/W to jobs.json | Scheduler |
| `cron/scheduler.py` | Scheduler loop — due-job detection, execution | Scheduler |
| `tools/memory_tool.py` | Persistent memory (MEMORY.md, USER.md) | Memory |
| `tools/skill_manager_tool.py` | Agent self-creates skills | Skills |

### 3.3 The Agent Loop

```
User message → AIAgent._run_agent_loop()
  ├── Build system prompt (prompt_builder.py)
  ├── Build API kwargs (model, messages, tools, reasoning config)
  ├── Call LLM (OpenAI-compatible API)
  ├── If tool_calls in response:
  │     ├── Execute each tool via registry dispatch
  │     ├── Add tool results to conversation
  │     └── Loop back to LLM call
  ├── If text response:
  │     ├── Persist session to DB
  │     └── Return final_response
  └── Context compression if approaching token limit
```

Two entry points:
```python
# Simple
response = agent.chat("Fix the bug in main.py")

# Full
result = agent.run_conversation(
    user_message="Fix the bug in main.py",
    system_message=None,           # auto-built if omitted
    conversation_history=None,      # auto-loaded from session
)
```

---

### 3.4 Memory System

**Architecture:** File-based, plain Markdown, with optional pluggable backends.

**Built-in (always active):**

| Store | File | Location | Char Limit | Purpose |
|-------|------|----------|------------|---------|
| memory | `MEMORY.md` | `~/.hermes/memories/` | 2,200 chars (~800 tokens) | Agent's notes — env facts, conventions, lessons |
| user | `USER.md` | `~/.hermes/memories/` | 1,375 chars (~500 tokens) | User profile — preferences, style, role |

**How it works:**
1. At session start, both files are loaded from disk
2. Entries are rendered into the system prompt as a **frozen snapshot** (never mutated mid-session for prefix cache stability)
3. Agent uses `memory` tool with actions: `add`, `replace`, `remove`
4. Writes update disk immediately but don't change the system prompt until next session
5. Entry delimiter: `§` (section sign). Entries can be multiline.
6. `replace`/`remove` use **substring matching** — agent provides a short unique substring to identify the target entry

**Session persistence:** All sessions stored in SQLite (`~/.hermes/state.db`) with FTS5 full-text search. Agent can search past conversations via `session_search` tool.

**Optional pluggable providers (8 available):**
- Honcho (dialectic reasoning, user modeling)
- Mem0 (cloud extraction, semantic search)
- Holographic (local SQLite, entity resolution, trust scoring)
- OpenViking (tiered retrieval)
- RetainDB, Supermemory, ByteRover, Hindsight

Plugin interface: `MemoryProvider` ABC in `agent/memory_provider.py`. Providers implement `initialize()`, `system_prompt_block()`, `prefetch(query)`, `sync_turn(user, asst)`.

**Key insight for Jemma:** The built-in file-based memory (MEMORY.md + USER.md) is dead simple and extremely effective. No vector store, no DB — just curated Markdown files with character limits. This is what you should replicate first.

---

### 3.5 Cron/Scheduling System

**Architecture:** JSON file-based job storage with a 60-second tick loop.

**Key files:**
| File | Purpose |
|------|---------|
| `cron/jobs.py` | Job model, CRUD, atomic read/write to `jobs.json` |
| `cron/scheduler.py` | Scheduler loop — due-job detection, execution, delivery |
| `tools/cronjob_tools.py` | Model-facing `cronjob` tool |

**Storage:** `~/.hermes/cron/jobs.json` (atomic writes via temp file + rename)

**Job structure:**
```json
{
  "id": "job_abc123",
  "name": "Daily briefing",
  "prompt": "Summarize today's AI news",
  "schedule": {"kind": "cron", "value": "0 9 * * *"},
  "skills": ["ai-funding-daily-report"],
  "deliver": "telegram:-1001234567890",
  "repeat": {"times": null, "completed": 0},
  "state": "scheduled",
  "next_run_at": "2026-01-16T09:00:00Z",
  "model": null,
  "provider": null,
  "script": null
}
```

**Schedule formats:** Cron expressions, intervals (`every 2h`), one-shot delays (`30m`), ISO timestamps.

**Execution flow:**
1. Gateway ticks scheduler every 60 seconds
2. File lock prevents duplicate execution
3. Due jobs get fresh AIAgent session (no prior context)
4. Attached skills loaded into the prompt
5. Agent runs, produces output
6. Output delivered to target platform (Telegram, Discord, local file, etc.)
7. Job state updated, next_run computed

**Security:** Prompts are scanned for injection patterns at creation time.

**Key insight for Jemma:** This is a fully self-contained scheduling system with no external dependencies (no celery, no Redis). Just JSON + file locks + a tick loop. Copy directly.

---

### 3.6 Self-Creating Skills System

**Architecture:** Markdown-based procedural memory with progressive disclosure.

**Core concept:** Skills are on-demand knowledge documents in `~/.hermes/skills/`. Each skill is a directory containing `SKILL.md` plus optional supporting files.

**Directory structure:**
```
~/.hermes/skills/
├── my-skill/
│   ├── SKILL.md           # Main instructions (required)
│   ├── references/        # Supporting documentation
│   ├── templates/         # Templates for output
│   ├── scripts/           # Executable helpers
│   └── assets/            # Other files
└── category/
    └── another-skill/
        └── SKILL.md
```

**SKILL.md format (YAML frontmatter + Markdown):**
```markdown
---
name: my-skill
description: Brief description (shown in search results)
version: 1.0.0
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [automation, python]
    category: devops
---

# Skill Title

## When to Use
Trigger conditions.

## Procedure
1. Step one
2. Step two

## Pitfalls
- Known failure modes and fixes

## Verification
How to confirm it worked.
```

**Progressive disclosure (3 tiers):**
1. `skills_list()` → Returns only name + description (minimal tokens)
2. `skill_view(name)` → Full SKILL.md content + linked file list
3. `skill_view(name, file_path)` → Specific linked file (reference, template, script)

**Agent self-creates skills via `skill_manage` tool:**
```python
skill_manage(action="create", name="deploy-staging", content="---\nname: deploy-staging\n...")
skill_manage(action="edit", name="deploy-staging", content="...")
skill_manage(action="patch", name="deploy-staging", old_text="...", new_text="...")
skill_manage(action="delete", name="deploy-staging")
skill_manage(action="write_file", name="deploy-staging", file_path="scripts/deploy.sh", file_content="...")
```

**When skills are created:** The agent creates skills when it figures out a non-trivial multi-step workflow — saving its approach as reusable procedural knowledge.

**Skills Hub:** Can install community skills from GitHub registries, LobeHub, and `.well-known/skills/` endpoints.

**Skills vs Memory:**
| | Skills | Memory |
|---|---|---|
| What | Procedural — how to do things | Factual — what things are |
| When | Loaded on demand | Injected every session |
| Size | Can be large (100s of lines) | Compact (key facts only) |
| Cost | Zero tokens until loaded | Small but constant |

**Key insight for Jemma:** The skill system is essentially "the agent writes its own instruction manual." This is the most impressive feature for demos. The YAML frontmatter + Markdown format is simple to implement and compatible with the agentskills.io standard.

---

### 3.7 Desktop Tool Actions

**47 built-in tools across 15+ toolsets:**

| Toolset | Tools | OS-Level Actions |
|---------|-------|-----------------|
| **terminal** | `terminal`, `process` | Execute any shell command, manage background processes (poll, log, wait, kill, stdin write) |
| **file** | `read_file`, `write_file`, `patch`, `search_files` | Full file system access, ripgrep-backed search, fuzzy-match patching |
| **browser** | 10 tools: navigate, snapshot, click, type, scroll, back, press, get_images, vision, console | Full browser automation via `agent-browser` CLI |
| **code_execution** | `execute_code` | Sandboxed Python with RPC access to other tools |
| **web** | `web_search`, `web_extract` | Web search + page content extraction |
| **vision** | `vision_analyze` | Image analysis via multimodal models |
| **delegation** | `delegate_task` | Spawn independent subagents for parallel work |
| **memory** | `memory` | Persistent cross-session memory |
| **skills** | `skills_list`, `skill_view`, `skill_manage` | Skill CRUD |
| **cronjob** | `cronjob` | Scheduled task management |
| **homeassistant** | `ha_list_entities`, `ha_get_state`, etc. | Smart home control |
| **messaging** | `send_message` | Cross-platform message delivery |

**Terminal backends:** Local, Docker, SSH, Modal, Daytona, Singularity — all abstracted behind a unified interface.

**Security:** `tools/approval.py` implements dangerous command detection. Commands matching patterns like `rm -rf`, `sudo`, etc. require explicit user approval.

---

### 3.8 Function Calling / Tool Use Pipeline

**Registration (import-time):**
```python
# tools/terminal_tool.py (every tool file does this)
from tools.registry import registry

registry.register(
    name="terminal",
    toolset="terminal",
    schema=TERMINAL_SCHEMA,        # OpenAI function-calling format
    handler=_handle_terminal,
    check_fn=check_terminal_requirements,
    emoji="💻",
)
```

**Discovery:** `model_tools.py` imports all tool modules in a fixed order. Each module self-registers.

**Schema collection:** `get_tool_definitions(enabled_toolsets, disabled_toolsets)` filters and returns OpenAI-format tool schemas.

**Dispatch:** `handle_function_call(function_name, function_args, task_id)` → `registry.dispatch(name, args)` → calls the handler.

**Client-side parsers (for open models):** The `environments/tool_call_parsers/` directory contains parsers for models that need client-side tool call extraction:
- `hermes_parser.py`
- `llama_parser.py`
- `qwen_parser.py`, `qwen3_coder_parser.py`
- `deepseek_v3_parser.py`, `deepseek_v3_1_parser.py`
- `mistral_parser.py`
- `kimi_k2_parser.py`

**This is critical for Gemma 4:** You'll need a Gemma 4 parser if the model doesn't use native OpenAI tool_calls format.

---

## 4. Adaptation Feasibility for Jemma

### 4.1 What Can Be Copied Directly (MIT License = Yes to Everything)

| Component | Path | Lines | Effort |
|-----------|------|-------|--------|
| **Memory system** | `tools/memory_tool.py` | ~550 | Copy as-is, works standalone |
| **Cron system** | `cron/jobs.py`, `cron/scheduler.py` | ~960 | Copy as-is, only needs `hermes_constants` path config |
| **Skill manager** | `tools/skill_manager_tool.py` | ~400 | Copy as-is |
| **Skills tool** | `tools/skills_tool.py` | ~1,300 | Copy as-is |
| **Tool registry** | `tools/registry.py` | ~200 | Copy as-is, it's a clean singleton |
| **File tools** | `tools/file_tools.py` | ~835 | Copy as-is |
| **Terminal tool** | `tools/terminal_tool.py` | ~1,800 | Copy, may need to strip remote backends |
| **Approval system** | `tools/approval.py` | ~200 | Copy for safety features |
| **Tool schemas** | All `*_SCHEMA` dicts in tool files | varies | Copy, these are OpenAI function-calling format |

### 4.2 What Needs Adaptation for Gemma 4 via Ollama

1. **Provider resolution** — Replace the multi-provider system with a single Ollama client. The `AIAgent.__init__` takes `model: str` — change default from `"anthropic/claude-opus-4.6"` to your Gemma 4 Ollama endpoint.

2. **API call** — Hermes uses OpenAI-compatible `chat_completions` API. Ollama exposes an OpenAI-compatible endpoint, so this mostly works. The key change is the base URL.

3. **Tool call parsing** — If Gemma 4 returns tool calls in its own format (not OpenAI `tool_calls`), you need a client-side parser. The existing parsers in `environments/tool_call_parsers/` provide a template. Create `gemma4_parser.py`.

4. **Context window management** — Gemma 4 context lengths may differ. The `agent/context_compressor.py` and `agent/model_metadata.py` need Gemma 4's context length.

5. **System prompt** — The prompt in `agent/prompt_builder.py` is optimized for Claude/GPT. Gemma 4 may need different prompting. In particular, the tool-use guidance and memory guidance sections may need rewriting for Gemma's instruction format.

### 4.3 What to Use as Architectural Inspiration

- **The bounded memory design** (char limits, not token limits) — model-independent
- **Progressive disclosure for skills** — minimizes token waste
- **File-based storage everywhere** (JSON for cron, Markdown for memory/skills, SQLite for sessions) — no external dependencies
- **Self-registering tool pattern** — clean, extensible
- **Frozen prompt snapshot** — memory loaded once at session start, writes go to disk but don't change the prompt mid-session (preserves cache)

---

## 5. Key Differences: Hermes Agent → Jemma (Gemma 4)

| Aspect | Hermes Agent | Jemma (Target) |
|--------|-------------|----------------|
| **Default model** | Claude Opus 4.6 / any via OpenRouter | Gemma 4 via Ollama (local) |
| **API protocol** | OpenAI-compatible (chat_completions, anthropic_messages, codex_responses) | OpenAI-compatible via Ollama |
| **Context window** | Managed per-model (100k+ for Claude) | Gemma 4's context (likely 8k-128k depending on variant) |
| **Tool calling** | Native (server-side) for most providers | May need client-side parsing for Gemma 4 |
| **Multi-provider** | 200+ models via OpenRouter, credential pools | Single local Ollama instance |
| **Platform gateway** | 15+ messaging platforms | Not needed for hackathon (CLI-only) |
| **Safety focus** | Command approval, prompt injection scanning | Enhanced: industrial safety, LAN actuation controls |
| **Deployment** | Cloud, VPS, local, Docker, Nix | Local only (RTX 5090) |
| **Codebase size** | ~100k+ lines, 47 tools | Strip to essentials: ~5-10k lines |

---

## 6. Implementation Priority for Hackathon (Maximum Demo Value)

### Tier 1: Must Have (Day 1) — Core agent loop + tools

1. **Agent loop** — Stripped-down version of `AIAgent.run_conversation()` targeting Ollama
2. **Terminal tool** — Execute shell commands (the most impressive demo capability)
3. **File tools** — Read/write/search files (essential for any coding task)
4. **Tool registry** — Copy `tools/registry.py` wholesale
5. **Basic CLI** — Simple REPL, not the full 8,500-line `cli.py`

### Tier 2: High Demo Value (Day 1-2) — Memory + Skills

6. **Persistent memory** — Copy `tools/memory_tool.py`, set up `~/.jemma/memories/`
7. **Skill creation** — Copy `tools/skill_manager_tool.py` + `tools/skills_tool.py`
8. **A few bundled skills** — Create 2-3 demo skills (e.g., "code review", "deploy checker")

### Tier 3: Impressive Differentiator (Day 2) — Scheduling + Safety

9. **Cron system** — Copy `cron/` directory, wire up a simple tick loop
10. **Safety layer** — Implement `tools/approval.py` + your industrial safety extensions
11. **Web search** — Copy `tools/web_tools.py` if you have API keys

### Tier 4: Polish (If Time Permits)

12. **Browser automation** — High complexity, skip unless specifically needed
13. **Subagent delegation** — Impressive but complex
14. **Session search** — Nice to have, requires SQLite FTS5 setup

### Demo Script Suggestion

1. Start Jemma CLI → show it greeting, loading memory from last session
2. Ask it to write a Python script → watch it use terminal + file tools
3. Ask it to "remember that I prefer pytest over unittest" → show memory persistence
4. Ask it to "save what you did as a skill" → demonstrate self-creating skills
5. Create a cron job: "every hour, check if my server is up" → show scheduling
6. Restart Jemma → show it remembers everything from step 3

This demo hits memory, skills, tools, and cron — all the headline features — in under 5 minutes.

---

## 7. Concrete Code Examples

### Minimal Ollama Agent Loop (inspired by Hermes Agent)

```python
import json
import httpx

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "gemma4:latest"

def run_agent(user_message: str, tools: list, max_turns: int = 30):
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_message},
    ]
    
    for turn in range(max_turns):
        response = httpx.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": messages,
            "tools": tools,
        }, timeout=120).json()
        
        choice = response["choices"][0]
        message = choice["message"]
        messages.append(message)
        
        if not message.get("tool_calls"):
            return message["content"]  # Final response
        
        # Execute tool calls
        for tc in message["tool_calls"]:
            result = dispatch_tool(tc["function"]["name"], 
                                   json.loads(tc["function"]["arguments"]))
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
    
    return "Max turns reached."
```

### Minimal Memory Store (inspired by Hermes)

```python
from pathlib import Path

JEMMA_HOME = Path.home() / ".jemma"
MEMORY_DIR = JEMMA_HOME / "memories"
ENTRY_SEP = "\n§\n"

class MemoryStore:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.memory = self._read(MEMORY_DIR / "MEMORY.md")
        self.user = self._read(MEMORY_DIR / "USER.md")
    
    def _read(self, path):
        if not path.exists(): return []
        return [e.strip() for e in path.read_text().split("§") if e.strip()]
    
    def _write(self, path, entries):
        path.write_text(ENTRY_SEP.join(entries))
    
    def add(self, target, content):
        store = self.memory if target == "memory" else self.user
        store.append(content)
        self._write(MEMORY_DIR / f"{'MEMORY' if target == 'memory' else 'USER'}.md", store)
    
    def system_prompt_block(self):
        parts = []
        if self.memory:
            parts.append(f"MEMORY:\n" + ENTRY_SEP.join(self.memory))
        if self.user:
            parts.append(f"USER PROFILE:\n" + ENTRY_SEP.join(self.user))
        return "\n\n".join(parts)
```

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemma 4 poor tool calling | High | Use client-side parser; test extensively with simple tools first |
| Context window too small | Medium | Aggressive context compression; fewer tools in schema |
| Hermes codebase too large to adapt | Medium | Focus on Tier 1-2 only; the core is ~3k lines stripped |
| Tool schema token overhead | Medium | Reduce to 5-8 tools max for Gemma 4's context |
| Ollama API differences | Low | Ollama's OpenAI-compat endpoint is well-tested |

---

## 9. Summary Recommendation

**Fork the architecture, not the codebase.** Hermes Agent at 100k+ lines is too large to adapt wholesale in a hackathon. Instead:

1. **Copy verbatim:** `tools/registry.py`, `tools/memory_tool.py`, `tools/skill_manager_tool.py`, `cron/jobs.py`
2. **Simplify:** Write a 200-line agent loop targeting Ollama directly (vs. 9,200-line `run_agent.py`)
3. **Strip:** No gateway, no multi-provider, no ACP, no RL environments — CLI only
4. **Add:** Industrial safety layer, LAN actuation controls (your differentiator)
5. **Test:** Validate Gemma 4 tool calling with 3-5 tools before scaling up

The Hermes architecture is validated at scale (57k stars, 382 contributors). Its design choices — file-based persistence, bounded memory, progressive skills disclosure, self-registering tools — are all Gemma 4-friendly and hackathon-compatible.
