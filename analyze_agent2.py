"""Extract agent.py Agent class method signatures in detail."""
import ast, re
from pathlib import Path

with open("D:\\TERMINALCLI\\omega\\agent.py", "r") as f:
    text = f.read()

tree = ast.parse(text)
lines = text.splitlines()

for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'Agent':
        print(f"class Agent (line {node.lineno}):")
        print(f"  Docstring: {(ast.get_docstring(node) or 'N/A')[:80]}")
        print()
        
        for item in ast.iter_child_nodes(node):
            if isinstance(item, ast.FunctionDef):
                args = []
                for i, a in enumerate(item.args.args):
                    arg_str = a.arg
                    if a.annotation:
                        arg_str += f": {ast.unparse(a.annotation)}"
                    args.append(arg_str)
                
                # Handle defaults
                defaults = item.args.defaults
                if defaults:
                    # Match defaults to last N args
                    for j, d in enumerate(defaults):
                        idx = len(args) - len(defaults) + j
                        if '=' not in args[idx]:
                            args[idx] += f"={ast.unparse(d)}"
                
                args_str = ", ".join(args)
                return_hint = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                
                doc = ast.get_docstring(item) or ""
                doc_first = doc.split('\n')[0][:70]
                
                loc = (item.end_lineno or item.lineno) - item.lineno + 1
                
                has_decorator = bool(item.decorator_list)
                decorator_str = f"@{item.decorator_list[0].id} " if has_decorator and isinstance(item.decorator_list[0], ast.Name) else ""
                
                print(f"  {decorator_str}def {item.name}({args_str}){return_hint}:")
                print(f"    line {item.lineno}, {loc} LOC | {doc_first}")
                print()
