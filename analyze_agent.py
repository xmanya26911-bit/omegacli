"""Analyze agent.py — extract function signatures, classes, and structure."""
import ast
from pathlib import Path

with open("D:\\TERMINALCLI\\omega\\agent.py", "r") as f:
    text = f.read()

tree = ast.parse(text)

print("=== agent.py STRUCTURE ===")
print(f"Total lines: {len(text.splitlines())}")
print()

classes = []
funcs = []
top_assignments = []

for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ClassDef):
        methods = [n for n in ast.iter_child_nodes(node) if isinstance(n, ast.FunctionDef)]
        classes.append((node.name, node.lineno, (node.end_lineno or node.lineno), len(methods)))
    elif isinstance(node, ast.FunctionDef):
        args = [a.arg for a in node.args.args]
        has_return = any(isinstance(n, ast.AnnAssign) and n.target.id == 'return' for n in ast.iter_child_nodes(node)) if hasattr(ast, 'AnnAssign') else False
        # Check for return annotation
        return_hint = node.returns is not None
        arg_hints = sum(1 for a in node.args.args if a.annotation)
        print(f"FUNC: {node.name}({', '.join(args)}) → line {node.lineno} | args_typed={arg_hints}/{len(args)}, return_typed={return_hint}")
        funcs.append(node)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                top_assignments.append((t.id, node.lineno))

print()
print("--- CLASSES ---")
for name, line, end, nmethods in classes:
    loc = end - line + 1
    print(f"  {name:30s}  line {line:>4}  {loc:>4} LOC  {nmethods:>3} methods")

print()
print("--- TOP-LEVEL ASSIGNMENTS ---")
for name, line in top_assignments:
    print(f"  {name:30s}  line {line:>4}")

print()
print(f"Total: {len(classes)} classes, {len(funcs)} top-level functions")
