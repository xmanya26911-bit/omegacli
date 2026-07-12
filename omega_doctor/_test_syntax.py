#!/usr/bin/env python3
"""Test syntax of all Omega Doctor modules."""
import ast
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set console encoding to utf-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = [
    '__init__.py',
    'diagnostics.py',
    'repair_engine.py',
    'fallback.py',
    'recovery.py',
    'monitor.py',
    'doctor_core.py',
]

errors = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read())
        print(f'  OK {f}')
    except SyntaxError as e:
        print(f'  FAIL {f}: line {e.lineno}: {e.msg}')
        errors.append(f)

if errors:
    print(f'\nWARNING: {len(errors)} file(s) have syntax errors')
    sys.exit(1)
else:
    print(f'\nALL {len(files)} files pass syntax check!')
