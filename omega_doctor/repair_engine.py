#!/usr/bin/env python3
"""
🔧 OMEGA DOCTOR — REPAIR ENGINE
Auto-fixes common issues:
  - Syntax errors in Python files
  - Missing directories
  - Corrupted config files
  - Missing imports
  - Broken __pycache__ corruption
  - File permission issues
  - Critical file restoration from replicas
"""

import os
import sys
import ast
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict

OMEGA_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = OMEGA_DIR / "omega_doctor" / "repair_log.txt"


def log(msg: str):
    """Append timestamped message to repair log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass
    print(f"  🏥 [Repair] {msg}")


class RepairAction:
    """Record of a single repair action taken."""
    def __init__(self, target: str, action: str, success: bool, detail: str = ""):
        self.target = target
        self.action = action
        self.success = success
        self.detail = detail
        self.timestamp = datetime.now().isoformat()

    def __repr__(self):
        icon = "✅" if self.success else "❌"
        return f"{icon} {self.action} on {self.target}: {self.detail}"


class RepairReport:
    """Collection of repair actions."""
    def __init__(self):
        self.actions: List[RepairAction] = []
        self.start_time = datetime.now()

    def add(self, action: RepairAction):
        self.actions.append(action)
        log(f"{'OK' if action.success else 'FAIL'} {action.action} → {action.target}: {action.detail}")

    @property
    def success_count(self) -> int:
        return sum(1 for a in self.actions if a.success)

    @property
    def fail_count(self) -> int:
        return sum(1 for a in self.actions if not a.success)

    def summary(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"  🔧 OMEGA REPAIR REPORT")
        lines.append(f"  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        for a in self.actions:
            icon = "✅" if a.success else "❌"
            lines.append(f"  {icon} {a.action} → {a.target}")
            if a.detail:
                lines.append(f"     └─ {a.detail}")
        lines.append("-" * 60)
        lines.append(f"  Successful: {self.success_count}/{len(self.actions)}  |  Failed: {self.fail_count}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ──────────────────────────────────────────────
#  REPAIR FUNCTIONS
# ──────────────────────────────────────────────

def fix_python_syntax(filepath: Path) -> Tuple[bool, str]:
    """
    Attempt to fix common syntax errors in a Python file.
    Only fixes specific patterns; if it can't, reports the issue.
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Cannot read file: {e}"

    try:
        ast.parse(source)
        return True, "No syntax errors"
    except SyntaxError as e:
        pass  # We know there's an error, try to fix

    original = source
    fixes_applied = []

    # Fix 1: Bare 'except:' without exception type → 'except Exception:'
    import re
    new_source = re.sub(r'(?m)^(\s*)except\s*:\s*$', r'\1except Exception:', source)
    if new_source != source:
        fixes_applied.append("bare except → except Exception")
        source = new_source

    # Fix 2: Missing colon on function/class/if/for/while/try
    patterns = [
        (r'(?m)^(\s*)(def|class|if|elif|else|for|while|try|with|except|finally)\b(.*?)(?<!:)\s*$',
         lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}:"),
    ]
    for pat, repl in patterns:
        new_source = re.sub(pat, repl, source)
        if new_source != source:
            fixes_applied.append("added missing colons")
            source = new_source

    # Fix 3: Try to parse again
    try:
        ast.parse(source)
        filepath.write_text(source, encoding="utf-8")
        return True, f"Fixed: {', '.join(fixes_applied)}" if fixes_applied else "Reparsed OK"
    except SyntaxError as e2:
        if fixes_applied:
            return False, f"Applied fixes ({', '.join(fixes_applied)}) but remaining error: {e2}"
        return False, f"Cannot auto-fix: {e2}"


def fix_missing_directory(path: Path) -> bool:
    """Create a missing directory."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        log(f"Cannot create directory {path}: {e}")
        return False


def fix_config_file() -> Tuple[bool, str]:
    """Restore a minimal valid config if corrupted."""
    config_path = Path.home() / ".omega" / "config.json"
    secrets_path = Path.home() / ".omega" / ".secrets.json"

    # Try to fix config
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            # Ensure required keys exist
            changed = False
            if "base_url" not in data:
                data["base_url"] = "https://opencode.ai/zen/v1"
                changed = True
            if "model" not in data:
                data["model"] = "deepseek-v4-flash-free"
                changed = True
            if changed:
                config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return True, "Config repaired (missing keys restored)"
            return True, "Config valid"
        except (json.JSONDecodeError, OSError) as e:
            # Config corrupted — write a fresh one
            try:
                default_config = {
                    "base_url": "https://opencode.ai/zen/v1",
                    "model": "deepseek-v4-flash-free",
                    "theme": "default-dark",
                    "max_steps": 99999,
                    "max_tokens": 128000,
                }
                config_path.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
                return True, f"Config was corrupted, wrote fresh default: {e}"
            except Exception as e2:
                return False, f"Cannot fix config: {e2}"
    else:
        # Config doesn't exist — create it
        try:
            Path.home().joinpath(".omega").mkdir(parents=True, exist_ok=True)
            default_config = {
                "base_url": "https://opencode.ai/zen/v1",
                "model": "deepseek-v4-flash-free",
                "theme": "default-dark",
            }
            config_path.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
            return True, "Created default config"
        except Exception as e:
            return False, f"Cannot create config: {e}"


def clean_pycache(max_depth: int = 5) -> int:
    """Remove all __pycache__ directories. Returns count removed."""
    count = 0
    for root, dirs, files in os.walk(str(OMEGA_DIR), topdown=True, followlinks=False):
        rel_depth = root[len(str(OMEGA_DIR)):].count(os.sep)
        if rel_depth > max_depth:
            dirs.clear()
            continue
        if "__pycache__" in dirs:
            cache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                count += 1
                dirs.remove("__pycache__")
            except OSError:
                pass
    return count


def clean_temp_files() -> int:
    """Remove .pyc, .pyo, .bak, .tmp files."""
    count = 0
    for pattern in ["*.pyc", "*.pyo", "*.bak", "*.tmp"]:
        for f in OMEGA_DIR.glob(pattern):
            try:
                if f.is_file():
                    f.unlink()
                    count += 1
            except OSError:
                pass
    return count


def check_and_fix_critical_imports() -> List[str]:
    """Check that all critical modules can be imported. Return list of failed imports."""
    critical_modules = [
        "config", "memory", "tools", "llm", "prompts",
        "cli", "camera", "omega_hacker", "omega_evolution",
    ]
    failed = []
    for mod_name in critical_modules:
        try:
            importlib.import_module(mod_name)
        except ImportError as e:
            failed.append(f"{mod_name}: {e}")
        except Exception:
            failed.append(f"{mod_name}: init error")
    return failed


def restore_from_replicas(target_file: str) -> Tuple[bool, str]:
    """Try to restore a critical file from a replica backup in operations/replicas."""
    replicas_dir = OMEGA_DIR / "operations" / "replicas"
    if not replicas_dir.exists():
        return False, "No replicas directory found"

    target_path = OMEGA_DIR / target_file

    # Search for the file in replicas
    found_copies = list(replicas_dir.rglob(target_file))
    if not found_copies:
        return False, f"No replica of {target_file} found"

    # Use the most recent one
    best = max(found_copies, key=lambda p: p.stat().st_mtime)
    try:
        # Verify it's valid Python
        content = best.read_text(encoding="utf-8", errors="replace")
        ast.parse(content)
        # Backup the broken file first
        if target_path.exists():
            backup_path = target_path.with_suffix(target_path.suffix + ".broken")
            shutil.copy2(target_path, backup_path)
        # Restore
        target_path.write_text(content, encoding="utf-8")
        return True, f"Restored from {best} (relative to OMEGA_DIR)"
    except Exception as e:
        return False, f"Replica {best} also has errors: {e}"


# ──────────────────────────────────────────────
#  RUN ALL REPAIRS
# ──────────────────────────────────────────────

def run_auto_repair(fix_syntax: bool = True, fix_config: bool = True,
                    clean_cache: bool = True, fix_dirs: bool = True) -> RepairReport:
    """Run all auto-repair actions. Returns report."""
    report = RepairReport()

    log("Starting auto-repair sequence...")

    # 1. Fix critical directories
    if fix_dirs:
        dirs = [
            OMEGA_DIR / "sessions",
            Path.home() / ".omega" / "memory",
            Path.home() / ".omega" / "total_recall",
            OMEGA_DIR / "omega_doctor",
        ]
        for d in dirs:
            if not d.exists():
                ok = fix_missing_directory(d)
                report.add(RepairAction(str(d), "create_dir", ok))

    # 2. Fix config
    if fix_config:
        ok, detail = fix_config_file()
        report.add(RepairAction("config.json", "fix_config", ok, detail))

    # 3. Fix syntax errors in critical files
    if fix_syntax:
        critical = ["agent.py", "tools.py", "config.py", "llm.py", "memory.py", "cli.py", "prompts.py"]
        for fname in critical:
            fpath = OMEGA_DIR / fname
            if fpath.exists():
                ok, detail = fix_python_syntax(fpath)
                if not ok and "No syntax errors" not in detail:
                    # Try restoring from replicas
                    r_ok, r_detail = restore_from_replicas(fname)
                    if r_ok:
                        report.add(RepairAction(fname, "restore_from_replica", True, r_detail))
                    else:
                        report.add(RepairAction(fname, "fix_syntax", ok, detail))
                elif ok and "No syntax errors" not in detail:
                    report.add(RepairAction(fname, "fix_syntax", ok, detail))

    # 4. Clean caches
    if clean_cache:
        pycache_count = clean_pycache()
        if pycache_count > 0:
            report.add(RepairAction("__pycache__", "clean_cache", True,
                                     f"Removed {pycache_count} cache directories"))
        temp_count = clean_temp_files()
        if temp_count > 0:
            report.add(RepairAction("temp_files", "clean_temp", True,
                                     f"Removed {temp_count} temp files"))

    # 5. Check imports
    failed_imports = check_and_fix_critical_imports()
    if failed_imports:
        for fail in failed_imports:
            report.add(RepairAction("import_check", "verify_import", False, fail))
    else:
        report.add(RepairAction("import_check", "verify_import", True, "All critical imports OK"))

    log(f"Auto-repair complete. {report.success_count} OK, {report.fail_count} failed.")
    return report


if __name__ == "__main__":
    report = run_auto_repair()
    print(report.summary())
