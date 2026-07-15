#!/usr/bin/env python3
"""OMEGA ADK Team — Multi-agent CLI. Entry point for the clean public repo.

Usage:
    python main.py --team "Build a login page"    One-shot team task
    python main.py --team                         Interactive team mode
    python main.py --help                         Show help
"""

import sys
import os
import argparse

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "1.5.0"


def parse_args():
    parser = argparse.ArgumentParser(
        description="OMEGA ADK Team — Multi-Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --team "Build a login page"   One-shot team task
  python main.py --team                        Interactive team mode
        """,
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="Request to execute (omit for interactive mode)",
    )
    parser.add_argument(
        "--team", "-t",
        action="store_true",
        help="Launch OMEGA ADK TEAM mode (orchestrator + 5 specialists)",
    )
    parser.add_argument(
        "--team-task",
        help="Task for the OMEGA ADK TEAM to execute",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.version:
        print(f"OMEGA ADK Team v{VERSION}")
        return

    if args.team or args.team_task:
        from omega.team import run_team_task, run_team_interactive
        task = args.team_task or " ".join(args.request) if args.request else ""
        if task:
            run_team_task(task)
        else:
            run_team_interactive()
        return

    # Default: show help
    print("OMEGA ADK Team — Multi-Agent CLI")
    print()
    print("Usage:")
    print("  python main.py --team 'your task here'")
    print("  python main.py --team              (interactive mode)")
    print()


if __name__ == "__main__":
    main()
