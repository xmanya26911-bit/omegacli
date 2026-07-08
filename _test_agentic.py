"""Test Agentic Core v2.0"""
import sys
sys.path.insert(0, r'D:\TERMINALCLI\omega')
from omega_agentic_core import agentic_self_test

results = agentic_self_test()
for name, status, detail in results:
    print(f"{status}: {name} - {detail}")
