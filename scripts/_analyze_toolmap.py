"""Analyze TOOL_MAP structure and cross-references in tools.py"""
import ast
import sys

with open(sys.argv[1]) as f:
    tree = ast.parse(f.read())

# Find all TOOL_MAP references (both definition and .update() calls)
for node in ast.walk(tree):
    # TOOL_MAP = { ... }
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'TOOL_MAP':
                if isinstance(node.value, ast.Dict):
                    print(f"=== TOOL_MAP INITIAL (line {node.lineno}) ===")
                    for k, v in zip(node.value.keys, node.value.values):
                        k_val = k.value if isinstance(k, ast.Constant) else ast.dump(k)
                        if isinstance(v, ast.Name):
                            v_val = v.id
                        elif isinstance(v, ast.Call) and isinstance(v.func, ast.Name):
                            v_val = f"{v.func.id}()"
                        else:
                            v_val = ast.dump(v)[:60]
                        print(f"  TOOL_MAP['{k_val}'] = {v_val}")
                    print(f"  Total in init: {len(node.value.keys)}")
    
    # TOOL_MAP.update({ ... })
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                if isinstance(call.func.value, ast.Name) and call.func.value.id == 'TOOL_MAP' and call.func.attr == 'update':
                    # Find the source dict
                    dict_node = None
                    if call.args:
                        dict_node = call.args[0]
                    if isinstance(dict_node, ast.Name):
                        # It's a reference to another variable
                        print(f"\n=== TOOL_MAP.update({dict_node.id}) (line {node.lineno}) ===")
                    elif isinstance(dict_node, ast.Dict):
                        print(f"\n=== TOOL_MAP.update( inline dict ) (line {node.lineno}) ===")
                        for k, v in zip(dict_node.keys, dict_node.values):
                            k_val = k.value if isinstance(k, ast.Constant) else ast.dump(k)
                            v_val = v.id if isinstance(v, ast.Name) else ast.dump(v)[:60]
                            print(f"  '{k_val}' -> {v_val}")
                        print(f"  Total in update: {len(dict_node.keys)}")

print("\n\n=== ALL TOOL_MAP.update() CALLS ===")
for node in ast.walk(tree):
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                if isinstance(call.func.value, ast.Name) and call.func.value.id == 'TOOL_MAP' and call.func.attr == 'update':
                    arg = call.args[0]
                    name = arg.id if isinstance(arg, ast.Name) else "inline_dict"
                    print(f"  Line {node.lineno}: TOOL_MAP.update({name})")
