"""Analyze tools.py structure: functions, classes, globals, imports."""
import ast
import sys
from collections import defaultdict

with open(sys.argv[1]) as f:
    tree = ast.parse(f.read())

funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

# Top-level assignments (global variables)
top_assigns = []
for n in ast.iter_child_nodes(tree):
    if isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name):
                top_assigns.append(t.id)
    elif isinstance(n, ast.AugAssign):
        if isinstance(n.target, ast.Name):
            top_assigns.append(n.target.id)

# Imports
imports = []
for n in ast.iter_child_nodes(tree):
    if isinstance(n, ast.Import):
        for alias in n.names:
            imports.append(("import", alias.name))
    elif isinstance(n, ast.ImportFrom):
        module = n.module or ""
        for alias in n.names:
            imports.append(("from", module, alias.name))

print(f"=== tools.py OVERVIEW ===")
print(f"Total lines in file: {tree.body[-1].end_lineno if hasattr(tree.body[-1], 'end_lineno') else 'N/A'}")
print(f"Functions: {len(funcs)}")
print(f"Classes: {len(classes)}")
print(f"Top-level globals/consts: {len(top_assigns)}")
print()

print("=== IMPORTS ({}) ===".format(len(imports)))
for imp in imports:
    if imp[0] == "import":
        print(f"  import {imp[1]}")
    else:
        print(f"  from {imp[1]} import {imp[2]}")

print()
print("=== GLOBAL VARIABLES ===")
for g in sorted(top_assigns):
    print(f"  {g}")

print()
print("=== ALL FUNCTIONS ({}) ===".format(len(funcs)))
for i, f in enumerate(funcs):
    decorators = [d.id for d in f.decorator_list if isinstance(d, ast.Name)]
    is_async = isinstance(f, ast.AsyncFunctionDef)
    prefix = "async " if is_async else ""
    deco_str = f"@{decorators[0]} " if decorators else ""
    # Count lines
    lines = f.end_lineno - f.lineno + 1 if hasattr(f, 'end_lineno') else 0
    print(f"  {i+1:3d}. {deco_str}{prefix}def {f.name}  [{lines}L, line {f.lineno}]")

print()
print("=== ALL CLASSES ({}) ===".format(len(classes)))
for c in classes:
    methods = [n.name for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    print(f"  class {c.name}: {len(methods)} methods")
    for m in methods:
        m_node = next(n for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == m)
        ml = m_node.end_lineno - m_node.lineno + 1
        print(f"    - {m} [{ml}L]")
