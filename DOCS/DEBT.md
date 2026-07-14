# OMEGA Technical Debt Register

## Phase 4 Baseline — 2026-07-11

| # | Description | Impact | Risk | Effort | Priority |
|---|-------------|--------|------|--------|----------|
| 1 | **cli.py (53 funcs, 0% typed)** — Terminal UI core has zero type hints | No IDE completions, breakage risk on edits | Low (simple code) | Medium | Medium |
| 2 | **memory.py (56 funcs, 0% typed)** — Memory system needs types | Unsafe type conversions at runtime | Medium | Medium | Medium |
| 3 | **tools.py F841 unused vars** — ~96 dead variable assignments | Dead code, confusing | Very low (dead code) | Low | Low |
| 4 | **tools.py F401 unused imports** — ~33 intentional try/except import checks with unused re-exports | Code noise, but intentional pattern | None (deliberate) | Very low | Very low |
| 5 | **agent.py W293 whitespace** — 62 style issues in docstrings | Cosmetic only | None | Very low | Very low |
| 6 | **tools.py 6864 LOC / 213 funcs** — Largest monolith | High cognitive load, hard to test | High (coupling) | High | High |
| 7 | **omega_god_tier.py (1105 funcs, 0% typed)** — Auto-generated wrappers | Massively repetitive, any change needs regeneration | Low (auto-generated) | Very high | Low |
| 8 | **prompts.py (4216 LOC, 0% typed)** — Prompt/tool definitions data file | Data file, hard to validate | Low | Medium | Low |
| 9 | **No import dependency graph** — Unknown coupling between modules | Architecture changes risk unintended breakage | High | Medium | High |
| 10 | **80 tests for ~62K LOC** — ~0.13 tests per 100 LOC | Regression coverage gap | High | Very high | High |
| 11 | **No import cycle detection** — Circular imports possible but undetected | Can cause runtime crashes | Medium | Low | Medium |
| 12 | **omega_exploit_dev.py (2345 LOC, 80% typed)** — Well-typed but large | Maintainable, lower priority | Low | Medium | Low |
| 13 | **omega_swe_engine.py (2457 LOC, 89% typed)** — Well-typed, modular | Good shape | Low | Low | Very low |
| 14 | **100+ flat .py files in root** — Historical attack scripts clutter root | Hard to distinguish core from artifacts | Low | Medium | Low |
| 15 | **Hardcoded tool description strings in tools.py** — ~200 inline tool schemas | Duplication between code and documentation | Medium | High | Medium |

## Legend
- **Priority**: High / Medium / Low — aligned with Phase 4 milestones
- **Effort**: Very high / High / Medium / Low / Very low — estimated person-hours
- **Risk**: Severity if not addressed

## Closing Items
When an item is resolved, move it to the bottom with a resolution note.
