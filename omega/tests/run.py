"""
OMEGA Test Runner — Discover and run all unit tests.

Usage:
    python -m omega.tests.run                  # All tests
    python -m omega.tests.run -v               # Verbose
    python -m omega.tests.run test_config      # Specific module
"""

import sys
import unittest
from pathlib import Path


def discover() -> unittest.TestSuite:
    """Discover all tests in the omega/tests/ package."""
    test_dir = Path(__file__).parent.resolve()
    loader = unittest.TestLoader()
    return loader.discover(str(test_dir), pattern="test_*.py")


def run(verbosity: int = 2) -> unittest.TestResult:
    """Run all discovered tests and return the result."""
    suite = discover()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == "__main__":
    verbosity = 2
    target_module = None

    args = sys.argv[1:]
    if "-q" in args:
        verbosity = 1
        args.remove("-q")
    if "-v" in args:
        verbosity = 2
        args.remove("-v")

    if args:
        target_module = args[0]
        suite = unittest.TestLoader().loadTestsFromName(target_module)
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
    else:
        result = run(verbosity=verbosity)

    sys.exit(0 if result.wasSuccessful() else 1)
