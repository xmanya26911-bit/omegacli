#!/usr/bin/env python3
"""OMEGA Auto-Repair & Health System
   Runs at startup to ensure file integrity, clean up temp files,
   check for syntax errors in critical files, and auto-fix common issues.
   Created: 2026-07-05
"""

import os
import sys
import ast
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

OMEGA_DIR = Path(__file__).parent.resolve()
LOG_FILE = OMEGA_DIR / "omega_repair.log"

# ── Files to check for syntax validity ──
CRITICAL_FILES = [
    "agent.py",
    "llm.py",
    "tools.py",
    "memory.py",
    "config.py",
    "prompts.py",
    "cli.py",
]

# ── Files/dirs to never create in the repo ──
FORBIDDEN_ITEMS = [
    "passwords.txt",
    "pass.txt",
    "credentials.txt",
]

# ── Temp patterns to clean ──
TEMP_PATTERNS = [
    "*.bak",
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.log",
]


def log(msg):
    """Append a timestamped message to the repair log (no stdout noise)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


def check_syntax(filepath: Path) -> bool:
    """Check Python file for syntax errors. Returns True if valid."""
    try:
        source = filepath.read_text(encoding="utf-8")
        ast.parse(source)
        return True
    except SyntaxError as e:
        log(f"❌ SYNTAX ERROR in {filepath.name}: {e}")
        return False
    except Exception as e:
        log(f"⚠️  Cannot check {filepath.name}: {e}")
        return True  # Don't block on non-syntax issues


def clean_temp_files():
    """Remove temporary/build artifacts."""
    count = 0
    for pattern in TEMP_PATTERNS:
        for f in OMEGA_DIR.glob(pattern):
            try:
                if f.is_file():
                    f.unlink()
                    count += 1
            except OSError:
                pass
    
    # Clean __pycache__ directories (max 3 levels deep to avoid recursion)
    for root, dirs, files in os.walk(str(OMEGA_DIR), topdown=True, followlinks=False):
        # Limit depth to 5 levels
        rel_depth = root[len(str(OMEGA_DIR)):].count(os.sep)
        if rel_depth > 5:
            dirs[:] = []  # Don't go deeper
            continue
        if "__pycache__" in dirs:
            cache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                count += 1
                dirs.remove("__pycache__")
            except OSError as e:
                log(f"⚠️  Could not remove {cache_path}: {e}")
    
    if count > 0:
        log(f"🧹 Cleaned {count} temp file(s)")
    return count


def check_forbidden_files():
    """Check for files that should never be in the repo."""
    found = []
    for name in FORBIDDEN_ITEMS:
        f = OMEGA_DIR / name
        if f.exists():
            try:
                f.unlink()
                found.append(name)
                log(f"🗑️  Removed forbidden file: {name}")
            except OSError as e:
                log(f"⚠️  Could not remove {name}: {e}")
    return found


def ensure_dirs():
    """Ensure critical directories exist."""
    dirs = [
        OMEGA_DIR / "sessions",
        Path.home() / ".omega" / "memory",
        Path.home() / ".omega" / "total_recall",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return len(dirs)


def run_startup_repair() -> dict:
    """Run all repair checks. Returns report dict."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "syntax_errors": [],
        "files_cleaned": 0,
        "forbidden_removed": [],
        "dirs_ensured": 0,
        "status": "OK",
    }
    
    # 1. Check syntax of critical files
    for name in CRITICAL_FILES:
        f = OMEGA_DIR / name
        if f.exists():
            if not check_syntax(f):
                report["syntax_errors"].append(name)
        else:
            log(f"⚠️  Missing critical file: {name}")
    
    # 2. Clean temp files
    report["files_cleaned"] = clean_temp_files()
    
    # 3. Remove forbidden files
    report["forbidden_removed"] = check_forbidden_files()
    
    # 4. Ensure critical directories
    report["dirs_ensured"] = ensure_dirs()
    
    if report["syntax_errors"]:
        report["status"] = "ERRORS_FOUND"
        log(f"❌ Syntax errors in: {', '.join(report['syntax_errors'])}")
        print(f"  ⚠️  OMEGA auto-repair found {len(report['syntax_errors'])} syntax error(s) — check omega_repair.log")
    
    # Save report
    report_file = OMEGA_DIR / "omega_repair_report.json"
    try:
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass
    
    return report


if __name__ == "__main__":
    print("\n🔧 OMEGA Auto-Repair System")
    print("═" * 40)
    result = run_startup_repair()
    print(f"\n  Status: {result['status']}")
    print(f"  Files cleaned: {result['files_cleaned']}")
    if result["syntax_errors"]:
        print(f"  ⚠️  syntax errors: {', '.join(result['syntax_errors'])}")
    print()
