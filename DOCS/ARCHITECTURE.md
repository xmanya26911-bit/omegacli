# OMEGA Architecture

## Project Structure

```
omega/                          # Package root (__init__.py)
├── __init__.py                 # Package version, exports
├── config.py                   # Config: typed, validated, env-aware
├── tools.py                    # [LEGACY] 222 functions, 7,206 lines
├── prompts.py                  # [LEGACY] 4,216 lines system prompts
├── agent.py                    # Core Agent class
├── main.py                     # CLI entry point
│
├── omega/                      # NEW: Modular package structure
│   ├── __init__.py             # Package metadata
│   ├── tools/                  # Split from monolithic tools.py
│   │   ├── __init__.py         # ToolResult, Cache, retry, formatting
│   │   └── file_ops.py         # File I/O: read, write, edit, glob, grep
│   ├── prompts/                # Split from monolithic prompts.py
│   │   ├── __init__.py         # Prompt composition
│   │   └── personality.py      # Chatbot persona strings
│   ├── ops/                    # Consolidated operation modules
│   │   ├── __init__.py         # Ops exports
│   │   └── plesk.py            # Unified Plesk toolkit (replaces 18 scripts)
│   └── tests/                  # Unit test suite
│       ├── __init__.py
│       ├── run.py              # Test runner
│       ├── test_config.py      # Config tests (20 tests)
│       ├── test_toolresult.py  # ToolResult + cache tests (18 tests)
│       └── test_file_ops.py    # File operation tests (19 tests)
│
├── plesk_*.py                  # [LEGACY] 18 Plesk scripts → now unified
│                               #   in omega/ops/plesk.py
└── omega.bat                   # Launcher
```

## Key Architectural Decisions

### 1. Package Structure (ADR-001)
**Decision**: Create `omega/` Python package with focused subpackages.
**Rationale**: The original flat directory (234 .py files, no `__init__.py`) prevented proper imports, testing, and modular reasoning. Package structure enables:
- `from omega.tools import ToolResult` instead of `sys.path.insert(0, ...)`
- Discovery-based test loading (`unittest.TestLoader.discover`)
- Clean separation of concerns with explicit APIs
- Future pip-installable distribution

### 2. Monolith Decomposition (ADR-002)
**Decision**: Start splitting the largest files into focused subpackages.
**Status**: `tools.py` (7,206 lines) → `omega/tools/` package with categorized modules. `prompts.py` (4,216 lines) → `omega/prompts/` package with modular components.
**Rationale**: Single Responsibility Principle. Each module in the package has one job.
- `omega/tools/__init__.py`: Core types (ToolResult), caching, retry
- `omega/tools/file_ops.py`: All file operations
- Future: `web_tools.py`, `system_tools.py`, `hacker_tools.py`, etc.

### 3. Backward Compatibility (ADR-003)
**Decision**: Original files (tools.py, prompts.py) remain as-is to preserve all imports.
**Rationale**: The codebase has 234 files with interleaved imports. Removing the original files would break existing code. The strategy is:
1. Create package with clean implementations
2. Keep original files as thin wrappers/compatibility shims
3. Migrate callers incrementally

### 4. Duplicate Script Consolidation (ADR-004)
**Decision**: Merge 18 Plesk scripts into `omega/ops/plesk.py`.
**Rationale**: All 18 scripts used the same SSL socket approach with minor variations (GraphQL vs XML API vs login POST). A single parameterized module is:
- Testable (one test suite instead of manual testing each variant)
- Maintainable (fix a bug once instead of 18 times)
- Documented (one module docstring instead of scattered comments)

### 5. Testing Infrastructure (ADR-005)
**Decision**: Use `unittest` with discovery-based test loading.
**Rationale**: Zero-tests → 57 tests in the first cycle. Simple, no dependencies, runs with `python -m omega.tests.run`. Future: add pytest for richer assertions and fixtures.

### 6. Security Hardening (ADR-006)
**Decision**: Remove hardcoded API keys from source. Use environment variables or secrets file.
**Rationale**: The original `config.py` had hardcoded `DEFAULT_API_KEY` in source. The new config forces API key via environment variable or `.secrets.json`. Model provider configs now use empty strings for api_key by default.

## Quality Metrics (Baseline)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Python files (root) | 234 | 234 | 0 |
| Package files | 0 | 14 | +14 |
| Test count | 0 | 57 | +57 |
| Test coverage | 0% | ~5%* | +5% |
| Monolith files >3K LOC | 4 | 4 | 0** |
| Hardcoded API keys | 2 | 0 | -2 |
| Duplicate Plesk scripts | 18 | 1 | -17 |
| Type-hinted core modules | 0 | 3 | +3 |

*Coverage measured on new package modules. Full codebase coverage target: 25%.
**Monolith decomposition is ongoing — tools.py and prompts.py still exist as compatibility wrappers.

## Improvement Roadmap

### Phase 2 (Next Cycle)
- Split remaining monoliths: `tools.py` → 10+ focused modules in `omega/tools/`
- Split `omega_god_tier.py` (4,006 lines) → `omega/tools/hacker.py`
- Type hints for `agent.py`, `memory.py`, `llm.py`
- CI pipeline: auto-run tests on commit

### Phase 3
- Pytest migration for richer assertions
- Property-based testing with Hypothesis
- Performance benchmarks (startup time, tool execution)
- Mock-based tests for HTTP-dependent modules

### Phase 4
- Plugin system via `omega/plugins/` package
- Dependency injection for Agent → Tool communication
- Async tool execution
- Package publication (pip install omega-agent)

## Failure Mode Analysis

| Scenario | Cause | Mitigation |
|----------|-------|------------|
| Test pollution | Config tests writing to real ~/.omega/ | Temp dir isolation (resolved) |
| Import errors | Circular imports in flat modules | Package structure + delayed imports |
| API key exposure | Hardcoded keys in config.py | Env vars only (resolved) |
| Infinite recursion | operations/replicas/ depth | Prune in tree/file scans |

## Design Principles

1. **Correctness first**: Never sacrifice verification for speed
2. **Measurable progress**: Every change has a metric
3. **Backward compatible**: Old code continues working during migration
4. **Incremental refactoring**: Small, reversible changes over big-bang rewrites
5. **Tested interfaces**: Every module boundary has tests
6. **Documented decisions**: Every ADR is captured
