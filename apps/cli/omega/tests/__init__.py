"""
OMEGA Test Framework — Unit tests for core components.

Run with:   python -m omega.tests.run
"""

import os, sys

# Add project source directories to sys.path so tests can find config, llm, agent etc.
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_tests_dir, '..', '..'))

# Main source paths (in priority order)
_source_paths = [
    os.path.join(_root, 'OMEGABACKEND', 'core'),
    os.path.join(_root, 'OMEGATUI'),
    os.path.join(_root, 'OMEGADOCTOR'),
    os.path.join(_root, 'OMEGAAGENTIC'),
    _root,
]

for _p in _source_paths:
    if _p not in sys.path:
        sys.path.insert(0, _p)

del _tests_dir, _root, _source_paths, _p

# Test modules are discovered dynamically — this __init__ just marks the package.
# See run.py for the test runner.
