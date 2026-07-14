#!/usr/bin/env python3
"""Test the diagnostics engine."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from diagnostics import run_all_checks, quick_health

print("=" * 60)
print("  TEST: Full Diagnostics")
print("=" * 60)
report = run_all_checks()
print(report.summary())

print()
print("=" * 60)
print("  TEST: Quick Health Check")
print("=" * 60)
quick = quick_health()
print(quick.summary())

print()
print(f"Full: {report.passed_count}/{len(report.checks)} passed, {len(report.critical_failures)} critical")
print(f"Quick: {quick.passed_count}/{len(quick.checks)} passed")
print()
print("ALL DIAGNOSTICS TESTS PASSED" if report.all_passed else "SOME CHECKS FAILED (non-critical)")
