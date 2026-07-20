# Engineering Onboarding

> **§393 — New contributors should understand the project through a structured onboarding path.**

---

## Onboarding Sequence

### Step 1: Product Overview
- **What is OMEGA?** A personal AI ecosystem: CLI TUI + Cloud Chat + LLM Provider
- **Three pillars:**
  - **Omega CLI** — Local Python terminal TUI (uncensored, full system access)
  - **Omega Cloud** — Public chat website (moderated, production-grade)
  - **Omega Provider (OpenCode)** — 5 free LLM models API backend
- **Philosophy:** Everything free, self-owned. CLI-side uncensored.

### Step 2: Architecture
- **Architecture layers:** UI → Application → Domain → Infrastructure (§388)
- **State management:** Local (component) → Shared (app-wide) → Domain (project data) → Server (synced) (§387)
- **Event-driven:** EventBus with 17 event types, typed subscriptions (§387)
- **Module boundaries:** Each module has one responsibility (§385)

### Step 3: Repository Layout
```
omega/
├── packages/            # Reusable libraries
│   ├── errors/          # Error code catalog (§397)
│   └── config/          # Global config system (§396)
├── omega/               # CLI application package
│   ├── core/            # Types, exceptions, config
│   ├── tools/           # Tool implementations
│   ├── ui/              # TUI components, themes
│   ├── bridge/          # Multi-agent bridge (Hermes)
│   ├── prompts/         # System prompts
│   ├── schemas/         # Tool definitions
│   ├── ops/             # Operations modules
│   └── tests/           # Unit tests
├── docs/                # Documentation
├── .github/             # PR templates, CI workflows
└── tests/               # Integration tests
```

### Step 4: Development Environment
- **Python 3.11+** required
- **No dependencies beyond stdlib** for core packages (packages/errors, packages/config use only dataclasses + typing)
- **Run tests:** `python -m unittest discover -s packages/<name>/tests -p "test_*.py" -v`
- **CLI entry:** `omega.bat` → `python -m omega`
- **Config files:** `~/.omega/config.json` and `~/.omega/.secrets.json`

### Step 5: Design System
- **CLI TUI:** prompt_toolkit + rich (ANSI pipeline)
- **Cloud Chat:** Tailwind CSS v4, Hanken Grotesk/Inter/JetBrains Mono
- **Themes:** Dark default, light toggle on cloud; `default-dark` theme in CLI
- **Consistency:** Use design tokens from packages/config for any new config values

### Step 6: Core Domains
- **Error Codes (§397):** All errors in `packages/errors/catalog.py`. Use `raise OmegaException(code, details="...")`
- **Config (§396):** Use `OmegaConfig.load()` for section-based config. Sections: application, AI, repository, security, developer
- **CLI Events:** 17 event types across User/Assistant/Tool/System. Subscribe via EventBus
- **Cloud Auth:** Google OAuth PKCE, full-page redirect. Drive.file scope for storage

### Step 7: Testing Strategy
- **Unit tests:** `unittest` (no pytest dependency needed in CLI)
- **Test per package:** Each packages/ module has its own tests/
- **Run all:** `python -m unittest discover -s packages -p "test_*.py" -v`
- **TDD expected:** Write failing test → verify → implement → verify pass (§394)

### Step 8: Deployment Workflow
- **Landing Page:** `npx vercel deploy --prod --token <token>` (omega-nine-weld.vercel.app)
- **Chat App:** `git push origin master` (auto-deploy via GitHub integration)
- **CLI:** Local only, no deployment pipeline
- **PR workflow:** Every PR needs summary, motivation, testing evidence (§390)

### Step 9: Contribution Guidelines
1. Read the relevant spec section in the Engineering Design Spec
2. Create a feature branch from main
3. Make small, focused changes with meaningful commit messages (§389)
4. Include tests following TDD pattern
5. Update documentation
6. Open PR with completed template (§390)
7. Respond to review feedback (§392)

---

## Quick Reference

| Task | Command |
|------|---------|
| Run CLI | `omega.bat` or `python -m omega` |
| Run all tests | `python -m unittest discover -s packages -p "test_*.py"` |
| Run single test | `python -m unittest packages.errors.tests.test_errors -v` |
| Save config | `OmegaConfig.save()` |
| Raise error | `raise OmegaException(AI_PROVIDER_UNAVAILABLE, details="...")` |
| Validate config | `OmegaConfig.load().validate()` |
