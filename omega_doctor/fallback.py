#!/usr/bin/env python3
"""
🛡️ OMEGA DOCTOR — FALLBACK / SAFE MODE
When critical components fail, this provides a minimal operating environment:
  - Safe mode REPL with basic commands
  - Bypasses broken imports
  - Minimal LLM configuration (hardcoded fallbacks)
  - Recovery assistant
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

OMEGA_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
#  SAFE MODE CONFIGURATION
# ──────────────────────────────────────────────

def get_fallback_config() -> dict:
    """Return a minimal hardcoded config for safe mode."""
    return {
        "api_key": "sk-oddl0tKQUeYjsoNB367g2896mS2pKWMrL5Zroct6QzoayXTqC1Uj0aQ3nT4LbKo3",
        "base_url": "https://opencode.ai/zen/v1",
        "model": "deepseek-v4-flash-free",
        "theme": "default-dark",
        "max_steps": 99999,
        "max_tokens": 128000,
    }


def is_safe_mode_needed() -> tuple:
    """
    Check if safe mode is needed.
    Returns (needed: bool, reasons: list).
    """
    reasons = []

    # Check config
    config_path = Path.home() / ".omega" / "config.json"
    if not config_path.exists():
        reasons.append("Config file missing")

    # Check critical files
    critical = ["agent.py", "tools.py", "llm.py"]
    for fname in critical:
        fpath = OMEGA_DIR / fname
        if not fpath.exists():
            reasons.append(f"Critical file missing: {fname}")
        elif fpath.stat().st_size == 0:
            reasons.append(f"Critical file empty: {fname}")

    # Check if core tools module imports
    try:
        import tools as _t
        try:
            _ = _t.TOOL_MAP
        except AttributeError:
            reasons.append("tools.py missing TOOL_MAP")
    except ImportError as e:
        reasons.append(f"tools.py import failed: {e}")

    return len(reasons) > 0, reasons


def enter_safe_mode() -> dict:
    """
    Activate safe mode. Returns a safe mode environment dict.
    This provides minimal functionality until repairs are done.
    """
    safe_config = get_fallback_config()

    print("\n" + "=" * 60)
    print("  🛡️  OMEGA SAFE MODE ACTIVATED")
    print("=" * 60)
    print("  Critical components are unavailable.")
    print("  Operating with hardcoded fallback configuration.")
    print("  Basic commands available: doctor, repair, status, exit")
    print("=" * 60 + "\n")

    return {
        "safe_mode": True,
        "activated_at": datetime.now().isoformat(),
        "config": safe_config,
        "available_commands": [
            "doctor check  — Run diagnostics",
            "doctor repair — Run auto-repair",
            "doctor status — Show system status",
            "doctor exit   — Exit safe mode (if repaired)",
            "help          — Show this message",
        ],
    }


def safe_mode_repl():
    """Run a minimal REPL in safe mode if the main loop can't start."""
    print("\n⚠️  OMEGA cannot start normally. Entering Safe Mode REPL.")
    print("Type 'help' for commands, 'doctor repair' to attempt repairs.\n")

    while True:
        try:
            cmd = input("🛡️  OMEGA-SAFE> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting safe mode.")
            break

        if cmd in ("exit", "quit", "q"):
            print("Exiting safe mode.")
            break
        elif cmd in ("help", "?"):
            print("\nAvailable commands:")
            print("  doctor check   — Run diagnostics")
            print("  doctor repair  — Run auto-repair")
            print("  doctor status  — Show system status")
            print("  doctor report  — Show last repair report")
            print("  doctor config  — Show fallback config")
            print("  exit           — Exit safe mode")
            print()
        elif cmd == "doctor check":
            # Run quick diagnostics
            try:
                from diagnostics import quick_health
                report = quick_health()
                print(report.summary())
            except Exception as e:
                print(f"  ❌ Diagnostics unavailable: {e}")
        elif cmd == "doctor repair":
            try:
                from repair_engine import run_auto_repair
                report = run_auto_repair()
                print(report.summary())
            except Exception as e:
                print(f"  ❌ Repair unavailable: {e}")
        elif cmd == "doctor status":
            print(f"\n  OMEGA Safe Mode — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Working directory: {OMEGA_DIR}")
            for fname in ["agent.py", "tools.py", "llm.py", "config.py"]:
                fpath = OMEGA_DIR / fname
                status = "✅" if (fpath.exists() and fpath.stat().st_size > 100) else "❌"
                print(f"  {status} {fname}")
            print()
        elif cmd == "doctor config":
            cfg = get_fallback_config()
            print(f"\n  Model: {cfg['model']}")
            print(f"  Base URL: {cfg['base_url']}")
            print(f"  Max Steps: {cfg['max_steps']}")
            print()
        else:
            print(f"  Unknown command: {cmd}. Type 'help'.")


if __name__ == "__main__":
    needed, reasons = is_safe_mode_needed()
    if needed:
        print("Safe mode required:")
        for r in reasons:
            print(f"  • {r}")
        safe_mode_repl()
    else:
        print("✅ Safe mode not needed — all critical components appear healthy.")
