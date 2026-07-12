"""OMEGA Dependency Graph Generator.

Analyzes import relationships between core modules.
Produces a dependency map as a DOT graph and a text report.

Usage: python _deps.py
"""

import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

OMEGA = Path(__file__).parent.resolve()

# Core modules to analyze (skip attack scripts)
CORE = [
    "agent.py", "tools.py", "cli.py", "config.py", "prompts.py",
    "memory.py", "llm.py", "evolve.py", "main.py",
    "omega_god_tier.py", "omega_claude_features.py",
    "omega_exploit_dev.py", "omega_swe_engine.py", "omega_hacker.py",
    "omega_claude_complete.py",
]

# Omega subpackage modules
SUBPACKAGE_FILES = list(OMEGA.glob("omega/**/*.py"))

def extract_imports(path):
    """Extract import relationships from a Python file."""
    with open(path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return [], []
    
    imports = []
    from_imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                from_imports.append(node.module.split(".")[0])
    
    return imports, from_imports

def modname(s):
    return Path(s).stem  # "agent.py" -> "agent"

def main():
    deps = defaultdict(set)
    core_stems = {modname(f) for f in CORE}
    # Also include omega subpackage paths by stem
    sub_stems = {}
    for f in SUBPACKAGE_FILES:
        rel = str(f.relative_to(OMEGA))
        sub_stems[modname(rel)] = rel
    
    for fname in CORE:
        fpath = OMEGA / fname
        if not fpath.exists():
            continue
        top_imports, from_imports = extract_imports(fpath)
        all_imports = top_imports + from_imports
        for mod in all_imports:
            # Check if mod is a core module (by stem)
            if mod in core_stems:
                deps[fname].add(mod)
            # Check if mod is a subpackage module
            if mod in sub_stems:
                deps[fname].add(sub_stems[mod])
    
    for fpath in sorted(SUBPACKAGE_FILES):
        rel = fpath.relative_to(OMEGA)
        name = str(rel)
        top_imports, from_imports = extract_imports(fpath)
        all_imports = top_imports + from_imports
        for mod in all_imports:
            if mod in core_stems:
                deps[name].add(mod)
            if mod.startswith("omega"):
                deps[name].add(mod)
    
    # Print dependency report
    print("=" * 60)
    print("OMEGA CORE DEPENDENCY MAP")
    print("=" * 60)
    print()
    
    # Print per-module dependencies
    for module in sorted(deps.keys()):
        deps_list = sorted(deps[module])
        if deps_list:
            print(f"  {module:40s} → {', '.join(deps_list)}")
        else:
            print(f"  {module:40s} → (none)")
    
    # Circular dependency detection
    print()
    print("-" * 60)
    print("POTENTIAL CIRCULAR PATHS (depth=3)")
    print("-" * 60)
    
    modules_list = sorted(deps.keys())
    found_cycles = set()
    for m in modules_list:
        for d in list(deps.get(m, set())):
            # Find module key that matches d
            d_key = None
            for k in modules_list:
                if modname(k) == d or str(k) == d:
                    d_key = k
                    break
            if d_key and d_key in deps:
                for dd in list(deps[d_key]):
                    dd_key = None
                    for k in modules_list:
                        if modname(k) == dd or str(k) == dd:
                            dd_key = k
                            break
                    if dd_key and dd_key in deps:
                        if m in deps.get(dd_key, set()):
                            cycle = tuple(sorted([m, d_key, dd_key]))
                            if cycle not in found_cycles:
                                found_cycles.add(cycle)
                                print(f"  {m} -> {d_key} -> {dd_key} -> {m}")
    
    if not found_cycles:
        print("  No triangular cycles detected at depth 3")
    
    # Leaf modules
    all_module_names = {}
    for f in CORE:
        all_module_names[modname(f)] = f
    for f in SUBPACKAGE_FILES:
        rel = str(f.relative_to(OMEGA))
        all_module_names[modname(rel)] = rel
    
    print()
    print("-" * 60)
    print("LEAF MODULES (no dependents in core)")
    print("-" * 60)
    all_depended = set()
    for deps_list in deps.values():
        all_depended.update(deps_list)
    
    for stem, fname in sorted(all_module_names.items()):
        if fname.endswith("__init__.py"):
            continue
        if fname not in deps:
            continue
        depended_by = [k for k in deps if fname in deps[k] or stem in deps[k]]
        if not depended_by:
            print(f"  {fname}")
    
    print()
    print("=" * 60)
    print(f"Total modules: {len(deps)}")
    print(f"Total edges: {sum(len(v) for v in deps.values())}")
    print("=" * 60)

if __name__ == "__main__":
    main()
