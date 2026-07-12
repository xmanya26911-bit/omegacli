#!/usr/bin/env python3
"""Quick alias to run quality gates from repo root."""
import sys, subprocess
p = subprocess.run([sys.executable, str(__file__).rsplit('\\', 1)[0] + '\\scripts\\_quality.py', *sys.argv[1:]])
sys.exit(p.returncode)
