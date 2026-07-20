# Code Review Guidelines

> **§392 — Reviewers should evaluate architecture, correctness, readability, maintainability, performance, security, and testing.**

---

## Review Checklist

Every review should evaluate these dimensions:

### 1. Architecture
- [ ] Does the change follow the established architecture pattern (UI → Application → Domain → Infrastructure)?
- [ ] Are module boundaries respected? No unnecessary coupling?
- [ ] Are cross-domain dependencies through explicit interfaces, not implementation details?
- [ ] Does the change introduce circular dependencies?

### 2. Correctness
- [ ] Does the code do what it claims to do?
- [ ] Are edge cases handled (empty states, errors, timeouts, concurrency)?
- [ ] Are inputs validated?
- [ ] Are error paths tested, not just happy paths?

### 3. Readability
- [ ] Is the code easy to understand without comments?
- [ ] Are names descriptive and consistent with project conventions (§386)?
- [ ] Is there unnecessary cleverness that could be simpler?
- [ ] Are functions focused on a single responsibility?

### 4. Maintainability
- [ ] Is there duplication that should be extracted?
- [ ] Are dependencies explicit, not hidden?
- [ ] Would this change be easy to revert if needed?
- [ ] Are configuration values hardcoded instead of configurable?

### 5. Performance
- [ ] Are there obvious performance issues (N+1 queries, unnecessary allocations)?
- [ ] Are expensive operations cached or lazy-loaded where appropriate?
- [ ] Is streaming used for large responses?
- [ ] Are bundles/imports tree-shakeable?

### 6. Security
- [ ] Are all user inputs validated and sanitized?
- [ ] Are API keys/secrets never hardcoded or committed to git?
- [ ] Are authentication and authorization enforced server-side?
- [ ] Is proper CSP, CORS, and rate limiting in place?
- [ ] Are error messages avoiding information leakage?

### 7. Testing
- [ ] Does the change include tests?
- [ ] Do tests cover the failure modes, not just success?
- [ ] Are tests deterministic and isolated?
- [ ] Do existing tests still pass?

---

## Review Process

1. **Understand the context** — Read the PR summary and motivation first
2. **Read the diff** — Start with architecture-level changes, then details
3. **Run the code** — If possible, checkout and test locally
4. **Write actionable feedback** — Explain *what* and *why*, not just "fix this"
5. **Approve or request changes** — Explicitly state what must change vs. nice-to-have

### Tone

- Reviews should focus on **improving quality and sharing knowledge**
- Assume good intent — the author invested effort
- Be specific: "This could leak memory" not "this is wrong"
- Praise good patterns you see — reinforces team standards

---

## What to Ship vs. What to Block

| Severity | Should block merge? |
|----------|-------------------|
| Bugs that affect production behavior | ✅ Yes |
| Security vulnerabilities | ✅ Yes |
| Missing error handling for critical paths | ✅ Yes |
| Architectural violations | Usually |
| Missing tests for core logic | Usually |
| Style nits | ❌ No (mention, but don't block) |
| Future optimizations | ❌ No (note as follow-up) |

---

> "Reviews should focus on improving quality and sharing knowledge." — §392
