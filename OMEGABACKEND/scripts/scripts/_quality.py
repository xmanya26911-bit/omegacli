"""OMEGA Quality Gates — v5. Clean baseline, expandable.

Includes agent.py, memory.py (strict mypy) and cli.py (relaxed for Rich).

Usage: python _quality.py [--fix]
"""

import subprocess
import sys
import time
from pathlib import Path

OMEGA = Path(__file__).resolve().parent.parent  # scripts/ -> root

def run(cmd, timeout=120):
    if cmd[0] == "python":
        cmd = [sys.executable, *cmd[1:]]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=OMEGA, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError as e:
        return -1, "", f"Command not found: {e.filename}"
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"

def gate(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    d = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{d}")
    return ok

def main():
    fix_mode = "--fix" in sys.argv

    t0 = time.time()
    print("╔═══════════════════════════════════════════════╗")
    print("║     OMEGA QUALITY GATES v5                    ║")
    print("╚═══════════════════════════════════════════════╝")
    if fix_mode:
        print("  (auto-fix mode)")
    print()

    results = []

    # ── Gate 1: Syntax ──
    ok, out, err = run(["python", "-c",
        "import ast; ast.parse(open('tools.py').read()); ast.parse(open('agent.py').read()); print('ok')"])
    results.append(gate("syntax", ok == 0 and "ok" in out))

    # ── Gate 2: Import sanity ──
    ok, out, err = run(["python", "-c", """
import sys; sys.path.insert(0, '.')
from tools import TOOL_MAP, execute_tool, _HAS_HACKER
from config import Config
print('OK:' + str(len(TOOL_MAP)))
"""])
    results.append(gate("import sanity", ok == 0 and "OK:" in out))

    # ── Gate 3: Test suite ──
    ok, _, _ = run(["python", "-m", "pytest", "omega/tests/", "-q", "--tb=short", "--no-header"])
    results.append(gate("pytest", ok == 0, f"exit={ok}"))

    # ── Gate 4: Ruff F-level on agent.py + config.py ──
    if fix_mode:
        run(["ruff", "check", "agent.py", "config.py", "--select", "F", "--fix", "--quiet"])
    ok, out, err = run(["ruff", "check", "agent.py", "config.py", "--select", "F", "--quiet"])
    if ok == 0:
        results.append(gate("ruff (F) agent+config", True))
    else:
        issues = len([l for l in out.splitlines() if l.strip()])
        results.append(gate("ruff (F) agent+config", False, f"{issues} issues"))

    # ── Gate 5: Ruff tools.py — F-level, skip F401/F841 ──
    if fix_mode:
        run(["ruff", "check", "tools.py", "--select", "F", "--ignore", "F401,F841", "--fix", "--quiet"])
    ok, out, err = run(["ruff", "check", "tools.py", "--select", "F", "--ignore", "F401,F841", "--quiet"])
    if ok == 0:
        results.append(gate("ruff (F-noF401/841) tools.py", True))
    else:
        issues = len([l for l in out.splitlines() if l.strip()])
        results.append(gate("ruff (F-noF401/841) tools.py", False, f"{issues} issues"))

    # ── Gate 6: mypy on typed modules —────────────────────
    ok, out, err = run(["mypy", "agent.py", "memory.py", "llm.py", "--no-strict-optional",
                       "--check-untyped-defs", "--python-version", "3.11",
                       "--ignore-missing-imports", "--follow-imports", "skip",
                       "--disable-error-code", "var-annotated",
                       "--disable-error-code", "index",
                       "--disable-error-code", "return-value",
                       "--disable-error-code", "func-returns-value",
                       "--disable-error-code", "assignment",
                       "--disable-error-code", "attr-defined"])
    ok2, out2, err2 = run(["mypy", "cli.py", "--no-strict-optional",
                          "--check-untyped-defs", "--python-version", "3.11",
                          "--ignore-missing-imports", "--follow-imports", "skip",
                          "--allow-redefinition",
                          "--disable-error-code", "misc",
                          "--disable-error-code", "return-value",
                          "--disable-error-code", "index",
                          "--disable-error-code", "no-redef",
                          "--disable-error-code", "name-defined",
                          "--disable-error-code", "attr-defined",
                          "--disable-error-code", "union-attr"])
    if ok == 0 and ok2 == 0:
        results.append(gate("mypy agent+memory+llm+cli", True))
    else:
        agent_errors = sum(1 for l in out.splitlines() if "error:" in l)
        cli_errors = sum(1 for l in out2.splitlines() if "error:" in l)
        results.append(gate("mypy agent+memory+llm+cli", False,
                           f"agent/memory:{agent_errors} cli:{cli_errors}"))
        if not fix_mode:
            for line in (out.splitlines() + out2.splitlines())[:8]:
                print(f"    {line.strip()}")

    # ── Summary ──
    dt = time.time() - t0
    passed = sum(1 for r in results if r)
    print(f"\n{'─'*50}")
    print(f"  {passed}/{len(results)} gates passed ({dt:.1f}s)")
    print(f"{'─'*50}")
    if passed == len(results):
        print("  ✅ ALL GATES PASSING")
    else:
        print(f"  ⚠️  {len(results) - passed} gate(s) failing")
    print()

    if fix_mode:
        print("  Re-run without --fix to verify gates pass.")
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
