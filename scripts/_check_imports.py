"""Check which root .py files are imported by other modules"""
import ast, os

os.chdir("D:/TERMINALCLI/omega")

imported = set()
for fname in [f for f in os.listdir() if f.endswith('.py')]:
    try:
        with open(fname) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported.add(a.name.split('.')[0] + '.py')
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split('.')[0] + '.py')
    except:
        pass

core = {'agent.py', 'tools.py', 'cli.py', 'config.py', 'memory.py', 'prompts.py', 'llm.py'}
also_imported = {f for f in imported if f.endswith('.py') and f not in core and os.path.exists(f)}
print(f'Total files imported: {len(imported)}')
print(f'Non-core imported files: {len(also_imported)}')
for f in sorted(also_imported):
    print(f'  {f}')
