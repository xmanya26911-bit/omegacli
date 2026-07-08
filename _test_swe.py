"""Test SWE Engine v2.0"""
import sys
sys.path.insert(0, r'D:\TERMINALCLI\omega')
from omega_swe_engine import swe_self_test

results = swe_self_test()
for name, status, detail in results:
    icon = 'PASS' if status == 'PASS' else 'FAIL'
    print(f'{icon}: {name} - {detail}')
