#!/usr/bin/env python3
"""
🔬 OMEGA DOCTOR — DIAGNOSTICS ENGINE
Deep health checks for every OMEGA subsystem.
Scans: syntax, imports, config, memory, tools, LLM, hacker modules, filesystem.
"""

import os
import sys
import ast
import json
import importlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

OMEGA_DIR = Path(__file__).resolve().parent.parent


# ──────────────────────────────────────────────
#  DIAGNOSTIC RESULT TYPE
# ──────────────────────────────────────────────

class Diagnostic:
    """A single diagnostic check result."""
    def __init__(self, name: str, passed: bool, detail: str = "", severity: str = "info"):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.severity = severity  # 'critical', 'warning', 'info'
        self.timestamp = datetime.now().isoformat()

    def __repr__(self):
        status = "✅" if self.passed else "❌"
        return f"{status} {self.name}: {self.detail}"

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


class DiagnosticsReport:
    """Collection of diagnostic results."""
    def __init__(self):
        self.checks: List[Diagnostic] = []
        self.start_time = datetime.now()

    def add(self, check: Diagnostic):
        self.checks.append(check)

    def add_result(self, name: str, passed: bool, detail: str = "", severity: str = "info"):
        self.checks.append(Diagnostic(name, passed, detail, severity))

    @property
    def critical_failures(self) -> List[Diagnostic]:
        return [c for c in self.checks if not c.passed and c.severity == "critical"]

    @property
    def warnings(self) -> List[Diagnostic]:
        return [c for c in self.checks if not c.passed and c.severity == "warning"]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def summary(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"  🔬 OMEGA DIAGNOSTICS REPORT")
        lines.append(f"  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        for c in self.checks:
            status = "✅" if c.passed else "❌"
            sev = f"[{c.severity.upper()}]" if not c.passed else ""
            lines.append(f"  {status} {c.name} {sev}")
            if c.detail and not c.passed:
                lines.append(f"     └─ {c.detail}")
        lines.append("-" * 60)
        lines.append(f"  Passed: {self.passed_count}/{len(self.checks)}  |  "
                      f"Failed: {self.failed_count}  |  "
                      f"Critical: {len(self.critical_failures)}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self):
        return {
            "timestamp": self.start_time.isoformat(),
            "total": len(self.checks),
            "passed": self.passed_count,
            "failed": self.failed_count,
            "critical": len(self.critical_failures),
            "checks": [c.to_dict() for c in self.checks],
        }


# ──────────────────────────────────────────────
#  INDIVIDUAL CHECKS
# ──────────────────────────────────────────────

def check_file_exists(path: Path, name: str) -> bool:
    """Check if a critical file exists."""
    return path.exists() and path.is_file()


def check_python_syntax(path: Path) -> Tuple[bool, str]:
    """Check a Python file for syntax errors."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Read error: {e}"


def check_imports(path: Path) -> List[str]:
    """Extract and return top-level import statements from a Python file."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
        return imports
    except Exception:
        return []


# ──────────────────────────────────────────────
#  RUN ALL DIAGNOSTICS
# ──────────────────────────────────────────────

def run_all_checks() -> DiagnosticsReport:
    """Run every diagnostic check and return the report."""
    report = DiagnosticsReport()

    # ── 1. CRITICAL FILES ──
    critical_files = [
        "agent.py", "tools.py", "llm.py", "memory.py",
        "config.py", "prompts.py", "cli.py", "main.py",
    ]
    for fname in critical_files:
        fpath = OMEGA_DIR / fname
        exists = check_file_exists(fpath, fname)
        report.add_result(
            f"File: {fname}",
            exists,
            detail= "" if exists else f"Missing: {fpath}",
            severity="critical" if fname in ("agent.py", "tools.py") else "warning",
        )
        if exists:
            # Check syntax
            valid, err = check_python_syntax(fpath)
            report.add_result(
                f"Syntax: {fname}",
                valid,
                detail=err if err else "",
                severity="critical",
            )

    # ── 2. CONFIG VALIDATION ──
    try:
        sys.path.insert(0, str(OMEGA_DIR))
        from config import Config
        cfg = Config()
        issues = cfg.validate()
        report.add_result(
            "Configuration",
            len(issues) == 0,
            detail="; ".join(issues) if issues else "All config valid",
            severity="critical" if issues else "info",
        )
        report.add_result(
            f"Model: {cfg.model}",
            True,
            detail=f"Base URL: {cfg.base_url[:50]}...",
        )
    except Exception as e:
        report.add_result(
            "Configuration Load",
            False,
            detail=f"Config load failed: {e}",
            severity="critical",
        )

    # ── 3. LLM CONNECTION TEST ──
    try:
        from config import Config
        cfg_check = Config()
        from llm import LLMClient
        client = LLMClient(cfg_check)
        # Just check initialization, not a full call
        report.add_result(
            "LLM Client Init",
            True,
            detail=f"Model: {client.model}",
        )
    except Exception as e:
        report.add_result(
            "LLM Client Init",
            False,
            detail=f"LLM init failed: {e}",
            severity="critical",
        )

    # ── 4. TOOL MAP INTEGRITY ──
    try:
        from tools import TOOL_MAP, execute_tool
        from prompts import TOOL_DEFINITIONS
        map_count = len(TOOL_MAP)
        def_count = len(TOOL_DEFINITIONS) if TOOL_DEFINITIONS else 0
        report.add_result(
            "Tool Registry",
            map_count > 0,
            detail=f"{map_count} tools in TOOL_MAP, {def_count} with definitions",
        )
        # Check for gaps (handle None entries in TOOL_DEFINITIONS)
        map_names = set(TOOL_MAP.keys())
        def_names = set()
        for t in TOOL_DEFINITIONS:
            if t is None:
                continue
            name = t.get("name")
            if name:
                def_names.add(name)
        missing_from_map = def_names - map_names
        missing_from_defs = map_names - def_names
        if missing_from_map:
            report.add_result(
                "Tool Coverage Gap",
                False,
                detail=f"Defined but not registered: {', '.join(list(missing_from_map)[:5])}",
                severity="warning",
            )
        else:
            report.add_result("Tool Coverage", True, detail="All defined tools are registered")
    except Exception as e:
        report.add_result(
            "Tool Registry",
            False,
            detail=f"Tool map error: {e}",
            severity="critical",
        )

    # ── 5. MEMORY SYSTEM ──
    try:
        from memory import ShortTermMemory, get_persistent_memory
        stm = ShortTermMemory()
        report.add_result(
            "Short-Term Memory",
            True,
            detail=f"Working, {len(stm.messages if hasattr(stm, 'messages') else [])} messages",
        )
        pm = get_persistent_memory()
        report.add_result(
            "Persistent Memory",
            True,
            detail=f"Working",
        )
    except Exception as e:
        report.add_result(
            "Memory System",
            False,
            detail=f"Memory error: {e}",
            severity="critical",
        )

    # ── 6. HACKER MODULES ──
    try:
        import tools as tools_mod
        report.add_result(
            "Hacker Module",
            getattr(tools_mod, '_HAS_HACKER', False),
            detail="Loaded" if getattr(tools_mod, '_HAS_HACKER', False) else "Not available",
            severity="warning",
        )
        report.add_result(
            "Evolution Module",
            getattr(tools_mod, '_HAS_EVOLUTION', False),
            detail="Check tools.py for details",
            severity="info",
        )
    except Exception:
        pass

    # ── 7. DISK SPACE CHECK ──
    try:
        import shutil
        usage = shutil.disk_usage(str(OMEGA_DIR))
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        pct_free = (usage.free / usage.total) * 100
        report.add_result(
            "Disk Space",
            pct_free > 5,
            detail=f"{free_gb:.1f} GB free / {total_gb:.1f} GB total ({pct_free:.1f}%)",
            severity="critical" if pct_free < 2 else "warning" if pct_free < 10 else "info",
        )
    except Exception as e:
        report.add_result("Disk Space Check", False, detail=str(e), severity="warning")

    # ── 8. FILE INTEGRITY (check for corrupt/empty critical files) ──
    for fname in critical_files:
        fpath = OMEGA_DIR / fname
        if fpath.exists():
            size = fpath.stat().st_size
            report.add_result(
                f"Size: {fname}",
                size > 100,
                detail=f"{size:,} bytes",
                severity="critical" if size == 0 else "warning" if size < 500 else "info",
            )

    # ── 9. HOMEDIR CONFIG ──
    home_configs = [
        Path.home() / ".omega" / "config.json",
        Path.home() / ".omega" / ".secrets.json",
        Path.home() / ".omega" / "memory",
    ]
    for path in home_configs:
        exists = path.exists()
        report.add_result(
            f"Home Config: {path.name}",
            exists,
            detail="" if exists else f"Missing: {path}",
            severity="warning" if "secrets" not in str(path) else "info",
        )

    # ── 10. GIT REPOSITORY STATUS ──
    git_dir = OMEGA_DIR / ".git"
    if git_dir.exists():
        try:
            result = subprocess.run(
                ["git", "-C", str(OMEGA_DIR), "status", "--short"],
                capture_output=True, text=True, timeout=10, shell=True,
            )
            # Use shell=True on Windows
            result = subprocess.run(
                f'git -C "{OMEGA_DIR}" status --short',
                capture_output=True, text=True, timeout=10, shell=True,
            )
            dirty_files = [l for l in result.stdout.split("\n") if l.strip()]
            report.add_result(
                "Git Status",
                len(dirty_files) == 0,
                detail=f"{len(dirty_files)} uncommitted changes" if dirty_files else "Clean",
                severity="info",
            )
        except Exception as e:
            report.add_result("Git Status Check", False, detail=str(e), severity="info")
    else:
        report.add_result("Git Repository", False, detail="No .git directory", severity="info")

    return report


def quick_health() -> Dict:
    """Run a quick health check (syntax + config only)."""
    report = DiagnosticsReport()

    # Just check critical files syntax
    critical = ["agent.py", "tools.py", "config.py", "llm.py"]
    for fname in critical:
        fpath = OMEGA_DIR / fname
        if fpath.exists():
            valid, err = check_python_syntax(fpath)
            report.add_result(f"Syntax: {fname}", valid, detail=err if err else "OK",
                              severity="critical")
        else:
            report.add_result(f"File: {fname}", False, detail="MISSING", severity="critical")

    # Try config
    try:
        sys.path.insert(0, str(OMEGA_DIR))
        from config import Config
        cfg = Config()
        issues = cfg.validate()
        report.add_result("Config", len(issues) == 0,
                          detail="; ".join(issues) if issues else "Valid")
    except Exception as e:
        report.add_result("Config", False, detail=str(e), severity="critical")

    return report


if __name__ == "__main__":
    report = run_all_checks()
    print(report.summary())
