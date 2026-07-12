#!/usr/bin/env python3
"""Omnibus code health scorecard generator — uses os.walk to avoid infinite recursion."""
import os, sys, ast, time, collections, statistics, subprocess as sp
from pathlib import Path

root = Path("D:\\TERMINALCLI\\omega")
ignore_dir_names = {'__pycache__', 'venv', '.venv', 'node_modules', 'replicas'}
replica_prefix = str(root / "operations" / "replicas").lower()

filtered = []
for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
    dp = dirpath.lower()
    # Prune: don't descend into replicas
    if dp.startswith(replica_prefix) or 'replicas' in dirnames:
        if 'replicas' in dirnames:
            dirnames.remove('replicas')
        continue
    # Prune ignored dirs
    dirnames[:] = [d for d in dirnames if d not in ignore_dir_names]
    
    for fn in filenames:
        if fn.endswith('.py'):
            full = Path(dirpath) / fn
            filtered.append(full)

# === FILE SIZE ANALYSIS ===
sizes = []
for f in filtered:
    try:
        text = f.read_text(encoding='utf-8', errors='replace')
        lines = text.splitlines()
        loc = len(lines)
        sizes.append((loc, f))
    except Exception as e:
        print(f"  SKIP {f}: {e}")

sizes.sort(key=lambda x: -x[0])
total_loc = sum(s[0] for s in sizes)

print("=" * 70)
print("  OMEGA CODE HEALTH SCORECARD")
print("=" * 70)
print()
print(f"  Total .py files:  {len(filtered)}")
print(f"  Total LOC:        {total_loc}")
print()
print(f"  Files > 3000 LOC: {len([s for s in sizes if s[0] > 3000])}")
print(f"  Files > 1000 LOC: {len([s for s in sizes if s[0] > 1000])}")
print(f"  Files > 500 LOC:  {len([s for s in sizes if s[0] > 500])}")
print()

print("--- TOP 20 LARGEST MODULES ---")
for i, (loc, f) in enumerate(sizes[:20]):
    try:
        rel = f.relative_to(root)
    except ValueError:
        rel = f
    print(f"  {i+1:>2}. {loc:>6} LOC  {rel}")

# === TYPE HINT COVERAGE (CORE MODULES) ===
print()
print("--- TYPE HINT COVERAGE (CORE MODULES) ---")
core_paths = [
    root / "config.py",
    root / "agent.py",
    root / "tools.py",
    root / "prompts.py",
    root / "main.py",
    root / "omega" / "__init__.py",
    root / "omega" / "tools" / "__init__.py",
    root / "omega" / "tools" / "file_ops.py",
    root / "omega" / "prompts" / "__init__.py",
    root / "omega" / "prompts" / "personality.py",
    root / "omega" / "ops" / "plesk.py",
    root / "omega" / "ops" / "__init__.py",
]

for f in core_paths:
    if not f.exists():
        print(f"  {f.name:40s}  FILE NOT FOUND")
        continue
    try:
        text = f.read_text(encoding='utf-8', errors='replace')
        lines = text.splitlines()
        total = len(lines)
        func_defs = 0
        typed_funcs = 0
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if 'def ' in stripped and '->' in stripped:
                typed_funcs += 1
                func_defs += 1
            elif 'def ' in stripped:
                func_defs += 1
        pct = (typed_funcs / func_defs * 100) if func_defs > 0 else 0
        marker = "  OK" if pct > 50 else "  NEEDS WORK"
        print(f"  {f.name:35s} {total:>6} LOC  {typed_funcs:>2}/{func_defs:<2} typed funcs ({pct:3.0f}%){marker}")
    except Exception as e:
        print(f"  {f.name:35s}  ERROR: {e}")

# === TEST SUITE ===
print()
print("--- TEST SUITE ---")
test_dir = root / "omega" / "tests"
test_files = sorted(test_dir.glob("test_*.py"))
total_tests = 0
for tf in test_files:
    text = tf.read_text(encoding='utf-8', errors='replace')
    test_count = text.count("def test_")
    total_tests += test_count
    print(f"  {tf.name:30s}  {test_count:>3} tests")
print(f"\n  Total tests: {total_tests}")

# === DUPLICATE SCRIPT CLUSTERS ===
print()
print("--- DUPLICATE SCRIPT CLUSTERS ---")
cluster_patterns = [
    ("plesk_*.py", "Plesk"),
    ("creds*.py", "Creds"),
    ("cred*.py", "Cred"),
    ("harvest*.py", "Harvest"),
    ("track*.py", "Track"),
    ("school*.py", "School"),
]
for pattern, label in cluster_patterns:
    files = sorted(root.glob(pattern))
    if files:
        total = 0
        for f in files:
            try:
                total += len(f.read_text(encoding='utf-8', errors='replace').splitlines())
            except:
                pass
        print(f"  {label:10s}  {len(files):>3} files  {total:>6} total LOC")

# === STARTUP TIME ===
print()
print("--- STARTUP TIME ---")
results = []
for _ in range(3):
    t0 = time.time()
    r = sp.run(["python", "-c", "import config; import sys; sys.exit(0)"],
               capture_output=True, cwd=str(root), timeout=10)
    elapsed = time.time() - t0
    results.append(elapsed)
avg = statistics.mean(results)
print(f"  Config import (avg 3 runs):  {avg*1000:.1f} ms")

results2 = []
for _ in range(3):
    t0 = time.time()
    r = sp.run(["python", "-c", "from omega import get_version; sys.exit(0)"],
               capture_output=True, cwd=str(root), timeout=10)
    elapsed = time.time() - t0
    results2.append(elapsed)
avg2 = statistics.mean(results2)
print(f"  Package import (avg 3 runs): {avg2*1000:.1f} ms")

# === COMPLEXITY (rough: avg funcs per file, lines per func) ===
print()
print("--- COMPLEXITY ESTIMATES (TOP 10 LARGEST) ---")
for i, (loc, f) in enumerate(sizes[:10]):
    try:
        text = f.read_text(encoding='utf-8', errors='replace')
        func_count = text.count("def ")
        class_count = text.count("class ")
        avg_func_len = loc // max(func_count, 1)
        marker = ""
        if avg_func_len > 80:
            marker = "  LONG FUNCTIONS"
        elif func_count == 0:
            marker = "  (script mode)"
        print(f"  {f.name:35s} {loc:>6} LOC  {func_count:>3} funcs  {class_count:>2} classes  avg {avg_func_len:>3} LOC/func{marker}")
    except:
        pass

print()
print("=" * 70)
print("  SCORECARD COMPLETE")
print("=" * 70)
