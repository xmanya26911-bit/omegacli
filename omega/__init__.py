"""
OMEGA — God-Level Autonomous Engineering System.

This package contains the core OMEGA framework, organized into focused
subpackages for tools, prompts, operations, and system management.

Package Structure:
    omega/              Package root (this file)
    omega/tools/        Tool implementations (split from monolithic tools.py)
    omega/prompts/      System prompts and tool definitions
    omega/ops/          Operations and exploit modules
    omega/tests/        Unit and integration tests
"""

__version__ = "1.5.0"
__author__ = "OMEGA Engineering Team"

from pathlib import Path

PACKAGE_DIR = Path(__file__).parent
ROOT_DIR = PACKAGE_DIR.parent


def get_version() -> str:
    """Return the current OMEGA version string."""
    return __version__
