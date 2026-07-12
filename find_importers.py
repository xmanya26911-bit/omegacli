"""Find all files importing from tools.py module -- using os.walk to avoid recursion."""
import os
from pathlib import Path

root = Path("D:\\TERMINALCLI\\omega")
replica_prefix = str(root / "operations" / "replicas").lower()
ignore_dirs = {'__pycache__', 'venv', '.venv', 'node_modules', 'replicas'}

imports_from_tools = []

for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
    dp = dirpath.lower()
    # Prune replicas
    if dp.startswith(replica_prefix):
        continue
    # Prune ignored
    dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
    
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        full = Path(dirpath) / fn
        try:
            text = full.read_text(encoding='utf-8', errors='replace')
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if 'from tools import' in stripped or 'import tools' in stripped:
                    # Filter out false positives (e.g., scripts named tools.py in other dirs)
                    imports_from_tools.append((full, i, stripped))
        except:
            pass

print('=== FILES IMPORTING FROM ROOT tools.py ===')
print(f'Total import sites: {len(imports_from_tools)}')
print()

# Sort by file path
for f, line_no, stmt in sorted(imports_from_tools, key=lambda x: str(x[0])):
    try:
        rel = f.relative_to(root)
    except:
        rel = f
    print(f'  {str(rel):50s}  line {line_no:>4}  {stmt[:70]}')

# Also check what specific names are imported
print()
print('=== SPECIFIC NAMES IMPORTED ===')
all_imported = set()
for f, line_no, stmt in imports_from_tools:
    if 'from tools import' in stmt:
        # Extract names after 'import'
        after = stmt.split('import', 1)[1].strip()
        if after.startswith('('):
            # Multi-line import
            continue
        # Split by comma
        names = [n.strip().split(' as ')[0].strip() for n in after.split(',')]
        for n in names:
            if n and not n.startswith('#'):
                all_imported.add(n)

for name in sorted(all_imported):
    print(f'  {name}')
print(f'\nTotal unique imported names: {len(all_imported)}')
