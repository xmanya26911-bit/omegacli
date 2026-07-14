# OMEGA Architectural Audit & Migration Plan
## Generated: 2026-07-12

---

## PART 1: CURRENT ARCHITECTURE MAP

### Module Dependency Graph
```
                  ┌─────────────┐
                  │   main.py   │
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────────┐
          │              │                  │
    ┌─────▼─────┐  ┌────▼────┐       ┌─────▼──────┐
    │  agent.py │  │  cli.py │       │  tools.py   │◄─── CIRCULAR ────┐
    └─────┬─────┘  └─────────┘       └──────┬──────┘                │
          │                                  │                       │
    ┌─────▼─────┐                     ┌──────▼──────┐               │
    │  config   │                     │  omega/     │               │
    │  llm      │                     │  hacker_    │               │
    │  memory   │                     │  tools      │               │
    │  prompts  │                     │  (25 tools) │               │
    └───────────┘                     └─────────────┘               │
          │                                                         │
          └─────────────────────────────────────────────────────────┘
```

### Current File Inventory

**Layer 1 — Core Runtime (7 modules, all 100% typed)**
| File | Lines | Functions | Dependencies |
|------|-------|-----------|-------------|
| agent.py | 1,505 | 20 | cli, config, llm, memory, prompts, tools, omega_* |
| cli.py | 1,207 | 53 | (self-contained) |
| config.py | 307 | 13 | (self-contained) |
| llm.py | 261 | 7 | config |
| memory.py | 965 | 56 | (self-contained) |
| evolve.py | 1,520 | 49 | (self-contained) |
| tools.py | 6,855 | 213 (88% typed) | agent, config, memory, omega.*, prompts |

**Layer 2 — Prompt & Schema Data (self-contained)**
| File | Lines | Purpose |
|------|-------|---------|
| prompts.py | 4,216 | System prompt + ~244 inline JSON tool schemas |
| main.py | 270 | Entry point and argument parsing |

**Layer 3 — Capability Modules**
| Module | Lines | Typed | Purpose |
|--------|-------|-------|---------|
| omega_claude_features.py | 3,266 | 100% | Claude Code+ features |
| omega_swe_engine.py | 2,457 | 100% | SWE engineering engine |
| omega_exploit_dev.py | 2,345 | 100% | Exploit development |
| omega_god_tier.py | 4,006 | 0% | Auto-generated 1,105 wrappers |
| omega_agentic_core.py | 1,385 | 67% | Mission engine |
| omega_evolution.py | 1,104 | 41% | Evolution engine |
| omega_hacker.py | 1,651 | 0% | Hacking framework P1 |
| omega_hacker_part2.py | 1,280 | 0% | Hacking framework P2 |
| omega_auth_bypass.py | 1,141 | 0% | Auth bypass toolkit |
| omega_claude_complete.py | 685 | 0% | Claude integration |
| omega_team_cmd.py | 625 | 52% | Team command |
| omega_team_core.py | 715 | 58% | Team core |
| omega_tui.py | 322 | 0% | Terminal UI alt |
| omega_desktop.py | 684 | 0% | Desktop UI |
| omega_elite_web.py | 370 | 0% | Web UI |

**Layer 4 — Packages**
| Package | Files | Lines | Purpose |
|---------|-------|-------|---------|
| omega/tools/ | 4 | ~1,800 | ToolResult, file_ops |
| omega/ops/ | 2 | ~500 | Plesk operations |
| omega/prompts/ | 2 | ~300 | Prompt composition |
| omega/tests/ | 7 | ~2,500 | Unit tests (116) |
| omega/doctor/ | 3 | ~1,100 | Diagnostics + repair |
| spiderfoot/ | 5 | ~6,000 | Third-party OSINT |
| scripts/ | 5 | ~1,000 | Quality pipeline |

**Layer 5 — Root Scripts (~180 files)**
~150 pentest/attack scripts, 10+ gmail scripts, various analysis tools

---

## PART 2: CRITICAL ISSUES

### P1 — Architecture
1. **Circular import**: `agent.py` ↔ `tools.py` (agent imports tools, tools imports agent)
2. **TOOL_MAP fragmentation**: 3+ sources (literal dict in tools.py, _HACKER_TOOLS, evolution additions)
3. **No tool registration API**: Tools are manually placed in dict — no decorator, no registry, no metadata
4. **Schema duplication**: ~244 tool schemas in prompts.py duplicated from ~222 actual functions
5. **No permission system**: Every tool has full system access

### P2 — Maintainability
1. **tools.py monolith**: 6,855 lines, 213 functions, mixed concerns (file ops, web, system, hacking)
2. **prompts.py**: 4,216 lines mixing system prompt with 244 inline JSON schemas
3. **Root clutter**: 180+ pentest scripts mixed with core modules
4. **No dependency management**: No explicit dependency graph between tools

### P3 — Quality
1. **Test coverage**: 116 tests for ~62K LOC (~0.2%)
2. **No integration tests**: All tests are unit-level, no end-to-end agent tests
3. **No performance benchmarks**: Startup time, tool latency, memory usage unknown
4. **No security audit**: Tools have no permissions, sandboxing, or access control

---

## PART 3: MIGRATION PLAN

### Phase 3A — Core Infrastructure Refactor (NOW)
**Goal**: Break circular import, create clean layer architecture

1. **Extract ToolRegistry** from tools.py → `omega/tools/registry.py`
   - BaseTool abstract class (name, description, schema, execute)
   - ToolRegistry (register, discover, execute, list)
   - Decorator-based registration: `@tool(name="foo", ...)`
   
2. **Split prompts.py** → `omega/schemas/` package
   - Tool schemas extracted to `omega/schemas/tools.py`
   - System prompts → `omega/schemas/prompts.py`
   
3. **Resolve circular import**
   - tools.py stops importing agent.py
   - agent.py imports ToolRegistry instead of raw tool functions
   
4. **Create core/ package**
   - `omega/core/` with config, exceptions, types

### Phase 3B — Tool System Redesign
1. Design BaseTool with metadata, validation, permissions
2. Create tool discovery system (decorator + filesystem scan)
3. Auto-generate schemas from tool definitions (single source of truth)
4. Add tool dependency management, versioning

### Phase 3C — Agent Pipeline Upgrade
1. Planning layer
2. Task decomposition
3. Self-reflection
4. Context optimization

### Phase 3D — Memory Upgrade
1. Semantic retrieval (embedding-based)
2. Importance scoring
3. Memory decay
4. Knowledge graph

### Phase 3E — Testing Infrastructure
1. Test framework with fixtures
2. Tool contract tests (auto-generated)
3. Integration tests
4. Performance benchmarks

### Phase 3F — Final Quality
1. 100% type coverage on all modules
2. Full docstrings on every function
3. Security audit
4. Documentation generation

---

## PART 4: IMMEDIATE NEXT STEPS

1. Extract ToolRegistry and BaseTool from tools.py
2. Break circular import agent.py ↔ tools.py
3. Create omega/core/ package
4. Add tool decorator API
5. Auto-generate tool schemas from code
6. Migrate tests to new structure
