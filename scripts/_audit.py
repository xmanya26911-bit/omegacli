"""OMEGA System Audit — Phase 4 baseline measurement.
Run: python _audit.py

Measures: file sizes, LOC, type coverage, test counts, startup time, module dependencies.
"""
import ast
import os
import sys
import time
import typing
from collections import defaultdict
from pathlib import Path

OMEGA_DIR = Path("D:/TERMINALCLI/omega")
SKIP_DIRS = {"__pycache__", ".git", "venv", "node_modules", "archive", "replicas", "tests"}

def count_loc_and_types(filepath):
    """Count LOC, functions, classes, and type-annotated functions."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, Exception):
        return {"loc": 0, "funcs": 0, "typed_funcs": 0, "classes": 0, "typed": 0}

    loc = 0
    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            loc += 1

    funcs = 0
    typed_funcs = 0
    classes = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs += 1
            if node.returns or any(
                arg.annotation for arg in node.args.args if arg.arg != "self"
            ):
                typed_funcs += 1
        elif isinstance(node, ast.AsyncFunctionDef):
            funcs += 1
            if node.returns or any(
                arg.annotation for arg in node.args.args if arg.arg != "self"
            ):
                typed_funcs += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1

    typed = typed_funcs / funcs * 100 if funcs > 0 else 0
    return {"loc": loc, "funcs": funcs, "typed_funcs": typed_funcs, "classes": classes, "typed": typed}


def audit():
    print("=" * 72)
    print("  OMEGA SYSTEM AUDIT — Phase 4 Baseline")
    print("=" * 72)

    # 1. Module inventory
    print(f"\n{'─'*72}")
    print("  MODULE INVENTORY")
    print(f"{'─'*72}")
    print(f"  {'Module':<35} {'LOC':>7} {'Funcs':>6} {'Typd%':>7} {'Classes':>8}")
    print(f"  {'─'*35} {'─'*7} {'─'*6} {'─'*7} {'─'*8}")

    total_loc = 0
    total_funcs = 0
    total_typed = 0
    modules = []

    for f in sorted(OMEGA_DIR.glob("[a-z]*.py")):
        if f.name.startswith("_"):
            continue
        info = count_loc_and_types(f)
        modules.append((f.name, info))
        total_loc += info["loc"]
        total_funcs += info["funcs"]
        total_typed += info["typed_funcs"]
        print(f"  {f.name:<35} {info['loc']:>7,} {info['funcs']:>6} {info['typed']:>6.1f}% {info['classes']:>8}")

    # 2. Package modules
    print(f"\n  {'─'*35} {'─'*7} {'─'*6} {'─'*7} {'─'*8}")
    for pkg_dir in sorted(OMEGA_DIR.glob("omega/*/")):
        pkg_name = f"omega/{pkg_dir.name}/"
        pkg_loc = 0
        pkg_funcs = 0
        pkg_typed = 0
        pkg_classes = 0
        for f in sorted(pkg_dir.glob("*.py")):
            if f.name.startswith("_"):
                continue
            info = count_loc_and_types(f)
            pkg_loc += info["loc"]
            pkg_funcs += info["funcs"]
            pkg_typed += info["typed_funcs"]
            pkg_classes += info["classes"]
        total_loc += pkg_loc
        total_funcs += pkg_funcs
        total_typed += pkg_typed
        typed_pct = pkg_typed / pkg_funcs * 100 if pkg_funcs > 0 else 0
        print(f"  {pkg_name:<35} {pkg_loc:>7,} {pkg_funcs:>6} {typed_pct:>6.1f}% {pkg_classes:>8}")

    print(f"  {'─'*35} {'─'*7} {'─'*6} {'─'*7} {'─'*8}")
    typed_pct = total_typed / total_funcs * 100 if total_funcs > 0 else 0
    print(f"  {'TOTAL':<35} {total_loc:>7,} {total_funcs:>6} {typed_pct:>6.1f}%")

    # 3. Largest files
    print(f"\n{'─'*72}")
    print("  LARGEST MODULES (>1000 LOC)")
    print(f"{'─'*72}")
    large = sorted([(m["loc"], name) for name, m in modules if m["loc"] > 1000], reverse=True)
    for loc, name in large:
        typed_pct = sum(m["typed"] for n, m in modules if n == name)
        print(f"  {name:<35} {loc:>7,} LOC")

    # 4. Test count
    print(f"\n{'─'*72}")
    print("  TEST SUITE")
    print(f"{'─'*72}")
    test_files = list(OMEGA_DIR.glob("omega/tests/test_*.py"))
    test_funcs = sum(count_loc_and_types(f)["funcs"] for f in test_files)
    print(f"  Test files: {len(test_files)}")
    print(f"  Test functions: {test_funcs}")

    # 5. Startup benchmark
    print(f"\n{'─'*72}")
    print("  STARTUP BENCHMARK")
    print(f"{'─'*72}")
    sys.path.insert(0, str(OMEGA_DIR))
    import importlib
    times = []
    for i in range(3):
        importlib.invalidate_caches()
        start = time.perf_counter()
        import tools
        importlib.reload(tools)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"  tools.py import #{i+1}: {elapsed*1000:.1f} ms")
    avg = sum(times) / len(times)
    print(f"  Average: {avg*1000:.1f} ms")

    # 6. Critical module sizes
    print(f"\n{'─'*72}")
    print("  CRITICAL MODULE SIZES")
    print(f"{'─'*72}")
    critical = ["tools.py", "prompts.py", "omega_god_tier.py", "agent.py",
                 "cli.py", "evolve.py", "omega_claude_features.py",
                 "omega_exploit_dev.py", "omega_swe_engine.py"]
    for name in critical:
        f = OMEGA_DIR / name
        if f.exists():
            info = count_loc_and_types(f)
            print(f"  {name:<30} {info['loc']:>7,} LOC, {info['funcs']:>4} funcs, "
                  f"{info['typed']:>5.1f}% typed, {info['classes']:>4} classes")

    # 7. Type coverage summary
    print(f"\n{'─'*72}")
    print("  TYPE COVERAGE SUMMARY")
    print(f"{'─'*72}")
    typed_str = f"{total_typed} / {total_funcs} functions typed"
    print(f"  Overall: {typed_pct:.1f}% ({typed_str})")

    print(f"\n{'═'*72}")
    print("  Audit complete.")
    print(f"{'═'*72}")


if __name__ == "__main__":
    audit()
