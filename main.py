#!/usr/bin/env python3
"""OMEGA — God-Level CLI Agent. Entry point."""

import sys
import argparse
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add structured folder paths
_OMEGA = os.path.dirname(os.path.abspath(__file__))
for _p in ["OMEGABACKEND/core", "OMEGATUI", "OMEGADOCTOR", "OMEGAAGENTIC"]:
    sys.path.insert(0, os.path.join(_OMEGA, _p))

# ─── Startup Auto-Repair ─────────────────────────────────────────
try:
    from omega_repair import run_startup_repair
    _repair_result = run_startup_repair()
except Exception:
    pass  # Repair is best-effort; never block startup
# ─────────────────────────────────────────────────────────────────

from config import Config, AVAILABLE_MODELS, ConfigError
from agent import Agent
from cli import print_banner, print_info, print_error, print_warning

VERSION = "1.5.0"


def parse_args():
    parser = argparse.ArgumentParser(
        description="OMEGA — God-Level CLI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  omega                    Start interactive session
  omega list all files     Run a single request
  omega --model qwen3.6-plus-free  Start with specific model
  omega --diagnose         Run self-diagnostics
  omega --configure        Configure API key interactively
        """,
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="Request to execute (omit for interactive mode)",
    )
    parser.add_argument(
        "--model", "-m",
        help=f"Model to use. Available: {', '.join(AVAILABLE_MODELS)}",
    )
    parser.add_argument(
        "--non-interactive", "-n",
        action="store_true",
        help="Non-interactive mode (pipe input)",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run self-diagnostics and exit",
    )
    parser.add_argument(
        "--configure",
        action="store_true",
        help="Configure OMEGA interactively",
    )
    parser.add_argument(
        "--team", "-t",
        action="store_true",
        help="Launch DUAL-OMEGA TEAM mode (two agents working together)",
    )
    parser.add_argument(
        "--team-task",
        help="Task for the DUAL-OMEGA TEAM to execute",
    )
    parser.add_argument(
        "--tui", "-i",
        action="store_true",
        help="Launch OMEGA Enhanced TUI (rich interface)",
    )
    return parser.parse_args()


def configure_interactive():
    """Interactive configuration wizard."""
    from cli import console as rich_console
    from rich.prompt import Prompt

    print_banner()
    print_info("OMEGA Configuration Wizard")
    print_info("Press Enter to skip any setting.")
    print()

    config = Config()

    # API Key
    current = config.api_key
    if current:
        print_info(f"Current API key: {'***' + current[-4:]}")
    else:
        print_warning("No API key configured!")
    key = Prompt.ask("  API key", default="") if rich_console else input("  API key: ").strip()
    if key:
        config.save_secret("api_key", key)
        print_info("✓ API key saved")

    # Base URL
    url = Prompt.ask("  Base URL", default=config.base_url) if rich_console else input(f"  Base URL [{config.base_url}]: ").strip()
    if url:
        config.base_url = url

    # Model
    print_info(f"Available models: {', '.join(AVAILABLE_MODELS)}")
    model = Prompt.ask("  Model", default=config.model) if rich_console else input(f"  Model [{config.model}]: ").strip()
    if model and model in AVAILABLE_MODELS:
        config.model = model

    config.save()
    print_info("✓ Configuration saved to ~/.omega/config.json")
    print_info("✓ Secrets saved to ~/.omega/.secrets.json")


def _boot_sequence(config):
    """Streamlined boot initialization — Claude Code style."""
    from cli import (
        console as rich_console, print_info, print_warning, print_success,
        _use_rich, sanitize, _theme_ansi, _theme_ansi_bright, Style, print_error,
    )
    from prompts import TOOL_DEFINITIONS
    from pathlib import Path

    if _use_rich:
        from cli import get_theme_colors
        c = get_theme_colors()
        from rich.text import Text

        lines = []
        lines.append(("  ◇ Initializing core systems", "dim"))
        lines.append((f"  ◇ AI engine: {config.model}", "tool"))
        # Check connectivity
        try:
            import requests
            r = requests.get(config.base_url.rstrip('/v1') + "/models", timeout=5,
                           headers={"Authorization": f"Bearer {config.api_key}"})
            if r.status_code < 500:
                lines.append(("  ◇ API: Connected", "success"))
            else:
                lines.append(("  ◇ API: Degraded", "warning"))
        except Exception:
            lines.append(("  ◇ API: Standby", "warning"))
        lines.append(("  ◇ Memory: Online", "success"))
        lines.append((f"  ◇ Tools: {len(TOOL_DEFINITIONS)} protocols", "success"))
        # OMEGA.md project config check
        try:
            from omega_project import discover_omega_md
            omega_files = discover_omega_md()
            if omega_files:
                files_str = ", ".join([Path(f).name for f, _ in omega_files[:3]])
                lines.append((f"  ◇ Project: {files_str}", "success"))
        except Exception:
            pass
        # Camera check
        try:
            from camera import list_cameras
            cams = list_cameras(max_check=10)
            active_cams = [cam for cam in cams if cam.get("available")]
            if active_cams:
                lines.append((f"  ◇ Vision: {len(active_cams)} camera(s)", "success"))
        except Exception:
            pass

        for text, style_name in lines:
            style_map = {
                "dim": f"dim {c['dim_text']}",
                "tool": f"bold {c['tool_call']}",
                "success": f"bold {c['accent_success']}",
                "warning": f"bold {c['accent_warning']}",
            }
            t = Text(text, style=style_map.get(style_name, c['dim_text']))
            rich_console.print(t)
        rich_console.print()
    else:
        from cli import _S
        dc = _theme_ansi("dim")
        sc = _theme_ansi_bright("success")
        tc = _theme_ansi_bright("title")
        d = _S['diamond']
        print(f"  {d} Initializing core systems")
        print(f"  {d} AI engine: {tc}{config.model}{Style.RESET_ALL}")
        print(f"  {d} Memory: {sc}Online{Style.RESET_ALL}")
        print(f"  {d} Tools: {sc}{len(TOOL_DEFINITIONS)} protocols{Style.RESET_ALL}")
        print()

    # Config validation
    issues = config.validate()
    for issue in issues:
        if "API key" in issue:
            print_warning(issue)
        else:
            print_error(issue)

    return issues


def main():
    args = parse_args()

    if args.version:
        print(f"OMEGA v{VERSION}")
        return

    try:
        config = Config()
    except ConfigError as e:
        print_error(str(e))
        return

    if args.configure:
        configure_interactive()
        return

    if args.diagnose:
        from tools import self_diagnose
        print_banner(config)
        result = self_diagnose()
        print(result.content)
        return
    
    if args.team or args.team_task:
        try:
            from omega.bridge.__main__ import main as bridge_main
            bridge_args = ["--all"]  # Start Supervisor + Omega + WS
            task = args.team_task or " ".join(args.request) if args.request else ""
            if task:
                bridge_args.append(task)
            sys.argv = ["omega-bridge"] + bridge_args
            bridge_main()
        except ImportError as e:
            print_error(f"Bridge module not available: {e}")
            print_info("Run from omega project directory: cd /d/TERMINALCLI/omega")
        return

    if args.model:
        if not config.set_model(args.model):
            print_error(f"Unknown model: {args.model}")
            print_info(f"Available: {', '.join(AVAILABLE_MODELS)}")
            return

    # JARVIS-style boot sequence
    _boot_sequence(config)

    print_banner(config)

    agent = Agent(config)

    # ── TUI Mode ──
    if args.tui:
        from omega_tui import run_tui
        run_tui(agent)
        return

    if args.request:
        request = " ".join(args.request)
        from cli import print_user_input
        print_user_input(request)
        agent.run_once(request)
    elif not sys.stdin.isatty() or args.non_interactive:
        piped = sys.stdin.read().strip()
        if piped:
            from cli import print_user_input
            print_user_input(piped)
            agent.run_once(piped)
        else:
            agent.run_interactive()
    else:
        agent.run_interactive()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        pass
