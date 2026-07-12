#!/usr/bin/env python3
"""
🧬 OMEGA DOCTOR — CORE COORDINATOR
Unified command interface for all doctor subsystems:
  - check   → Run full diagnostics
  - repair  → Run auto-repair
  - monitor → Start/stop/status background monitor
  - snapshot → Create/list/restore recovery snapshots
  - recover → Recover a specific file
  - status  → Show overall system health
  - safemode → Enter safe mode
  - trend   → Show health history trends

Usage:
  python doctor_core.py <command> [options]
  Or import and use programmatically.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

OMEGA_DIR = Path(__file__).resolve().parent.parent


def print_header(title: str):
    """Print a styled header."""
    print()
    print("=" * 60)
    print(f"  🧬 {title}")
    print("=" * 60)


def print_section(label: str, content: str):
    """Print a labeled section."""
    print(f"\n  {label}")
    print(f"  {'─' * 40}")
    for line in content.split("\n"):
        print(f"  {line}")


# ──────────────────────────────────────────────
#  COMMANDS
# ──────────────────────────────────────────────

def cmd_check(args) -> int:
    """Run full diagnostics."""
    print_header("OMEGA DOCTOR — FULL DIAGNOSTICS")

    try:
        from diagnostics import run_all_checks
        report = run_all_checks()
        print(report.summary())

        # Auto-save health state
        try:
            from recovery import save_health_state
            save_health_state(report.to_dict())
        except ImportError:
            pass

        if args.json:
            print(json.dumps(report.to_dict(), indent=2))

        return 1 if report.critical_failures else 0
    except Exception as e:
        print(f"\n  ❌ Diagnostics engine failed: {e}")
        print("  ↳ Try: doctor repair  or  doctor safemode")
        return 2


def cmd_repair(args) -> int:
    """Run auto-repair."""
    print_header("OMEGA DOCTOR — AUTO REPAIR")

    try:
        from repair_engine import run_auto_repair
        report = run_auto_repair(
            fix_syntax=not args.no_syntax,
            fix_config=not args.no_config,
            clean_cache=not args.no_cache,
            fix_dirs=not args.no_dirs,
        )
        print(report.summary())

        if args.json:
            print(json.dumps({
                "successful": report.success_count,
                "failed": report.fail_count,
                "actions": [
                    {"target": a.target, "action": a.action,
                     "success": a.success, "detail": a.detail}
                    for a in report.actions
                ],
            }, indent=2))

        return 1 if report.fail_count > 0 else 0
    except Exception as e:
        print(f"\n  ❌ Repair engine failed: {e}")
        return 2


def cmd_monitor(args) -> int:
    """Manage the background monitor."""
    try:
        from monitor import start_monitor, stop_monitor, monitor_status, get_monitor

        if args.monitor_action == "start":
            interval = args.interval if args.interval else 300
            auto_repair = not args.no_auto_repair
            ok = start_monitor(interval, auto_repair)
            if ok:
                print(f"\n  ✅ Monitor started (interval={interval}s, auto_repair={auto_repair})")
            else:
                print("\n  ⚠️  Monitor was already running")
            return 0

        elif args.monitor_action == "stop":
            ok = stop_monitor()
            print(f"\n  {'✅' if ok else '⚠️'} Monitor stopped")
            return 0

        elif args.monitor_action == "status":
            status = monitor_status()
            print_header("OMEGA DOCTOR — MONITOR STATUS")
            print(f"\n  Status: {'🟢 RUNNING' if status['is_running'] else '🔴 STOPPED'}")
            print(f"  Checks: {status.get('checks_performed', 0)}")
            print(f"  Failures: {status.get('failures_detected', 0)}")
            print(f"  Auto-repair: {'ON' if status.get('auto_repair') else 'OFF'}")
            if status.get('latest_check'):
                lr = status['latest_check']
                print(f"  Latest: {lr.get('passed', 0)} passed, {lr.get('failed', 0)} failed")
            return 0

        else:
            print(f"Unknown monitor action: {args.monitor_action}")
            return 1
    except Exception as e:
        print(f"\n  ❌ Monitor error: {e}")
        return 2


def cmd_snapshot(args) -> int:
    """Manage recovery snapshots."""
    try:
        from recovery import create_snapshot, list_snapshots, restore_snapshot, cleanup_old_snapshots

        if args.snapshot_action == "create":
            ok, path = create_snapshot(args.name)
            if ok:
                size_mb = Path(path).stat().st_size / (1024 * 1024)
                print(f"\n  ✅ Snapshot created: {Path(path).name} ({size_mb:.1f} MB)")
            else:
                print(f"\n  ❌ Snapshot failed: {path}")
            return 0 if ok else 1

        elif args.snapshot_action == "list":
            snaps = list_snapshots()
            print_header("OMEGA DOCTOR — RECOVERY SNAPSHOTS")
            if snaps:
                for i, s in enumerate(snaps, 1):
                    print(f"\n  {i}. 📦 {s['name']}")
                    print(f"     Size: {s['size_mb']:.1f} MB")
                    print(f"     Created: {s['created']}")
                    print(f"     Path: {s['path']}")
            else:
                print("\n  📭 No snapshots available.")
                print("  Create one with: doctor snapshot create")
            return 0

        elif args.snapshot_action == "restore":
            snaps = list_snapshots()
            if not snaps:
                print("\n  ❌ No snapshots to restore from.")
                return 1

            if args.snapshot_name:
                # Find by name
                match = [s for s in snaps if s['name'] == args.snapshot_name]
                if not match:
                    print(f"\n  ❌ Snapshot '{args.snapshot_name}' not found.")
                    return 1
                snap_path = match[0]['path']
            else:
                # Use latest
                snap_path = snaps[0]['path']
                print(f"\n  Using latest snapshot: {snaps[0]['name']}")

            ok, detail = restore_snapshot(snap_path, args.target_dir)
            print(f"\n  {'✅' if ok else '❌'} {detail}")
            return 0 if ok else 1

        elif args.snapshot_action == "cleanup":
            keep = args.keep if args.keep else 5
            removed = cleanup_old_snapshots(keep)
            if removed > 0:
                print(f"\n  🗑️  Removed {removed} old snapshots (keeping {keep})")
            else:
                print(f"\n  ✅ No snapshots to clean up (keeping {keep})")
            return 0

        else:
            print(f"Unknown snapshot action: {args.snapshot_action}")
            return 1
    except Exception as e:
        print(f"\n  ❌ Snapshot error: {e}")
        return 2


def cmd_recover(args) -> int:
    """Recover a specific file from snapshot."""
    if not args.file:
        print("\n  ❌ No file specified. Usage: doctor recover <filename>")
        return 1

    try:
        from recovery import recover_file
        ok, detail = recover_file(args.file)
        print(f"\n  {'✅' if ok else '❌'} {detail}")
        return 0 if ok else 1
    except Exception as e:
        print(f"\n  ❌ Recovery error: {e}")
        return 2


def cmd_status(args) -> int:
    """Show overall system health status."""
    print_header("OMEGA DOCTOR — SYSTEM HEALTH")

    # Quick file check
    critical = ["agent.py", "tools.py", "llm.py", "config.py", "memory.py", "prompts.py", "cli.py"]
    print("\n  📁 Critical Files:")
    all_ok = True
    for fname in critical:
        fpath = OMEGA_DIR / fname
        if fpath.exists():
            size = fpath.stat().st_size
            ok = size > 100
            icon = "✅" if ok else "⚠️"
            print(f"    {icon} {fname}  ({size:,} bytes)")
            if not ok:
                all_ok = False
        else:
            print(f"    ❌ {fname}  (MISSING)")
            all_ok = False

    # Monitor status
    try:
        from monitor import monitor_status
        ms = monitor_status()
        icon = "🟢" if ms.get("is_running") else "🔴"
        print(f"\n  📊 Monitor: {icon} {'Running' if ms.get('is_running') else 'Stopped'}")
        if ms.get("checks_performed"):
            print(f"     Checks: {ms['checks_performed']}, "
                  f"Failures: {ms['failures_detected']}")
    except Exception:
        print(f"\n  📊 Monitor: ⚪ Not available")

    # Last diagnostics
    try:
        from diagnostics import quick_health
        qr = quick_health()
        print(f"\n  🔬 Last Diagnostic: {qr.passed_count}/{len(qr.checks)} passed")
        if qr.critical_failures:
            for c in qr.critical_failures:
                print(f"     ❌ [{c.severity.upper()}] {c.name}: {c.detail}")
    except Exception:
        print(f"\n  🔬 Diagnostics: ⚪ Not available")

    # Snapshots
    try:
        from recovery import list_snapshots
        snaps = list_snapshots()
        print(f"\n  💾 Snapshots: {len(snaps)} available")
        if snaps:
            print(f"     Latest: {snaps[0]['name']} ({snaps[0]['size_mb']:.1f} MB)")
    except Exception:
        pass

    # Recovery history
    try:
        from recovery import get_health_trend
        trend = get_health_trend(5)
        if trend:
            print(f"\n  📈 Health Trend (last {len(trend)} checks):")
            for r in trend:
                pct = (r.get("passed", 0) / max(r.get("total", 1), 1)) * 100
                icon = "✅" if pct >= 80 else "⚠️" if pct >= 50 else "❌"
                print(f"     {icon} {r['timestamp'][:19]}  "
                      f"{r.get('passed', 0)}/{r.get('total', 0)} ({pct:.0f}%)")
    except Exception:
        pass

    print(f"\n  Overall: {'✅ HEALTHY' if all_ok else '⚠️  ISSUES DETECTED'}")
    print("=" * 60)

    if not all_ok:
        print("  Recommended: doctor repair")
    return 0


def cmd_safemode(args) -> int:
    """Enter safe mode."""
    print_header("OMEGA DOCTOR — SAFE MODE")
    try:
        from fallback import is_safe_mode_needed, safe_mode_repl
        needed, reasons = is_safe_mode_needed()
        if needed:
            print("\n  Safe mode recommended due to:")
            for r in reasons:
                print(f"    • {r}")
            print()
            safe_mode_repl()
        else:
            print("\n  ✅ Safe mode not needed. All critical components appear healthy.")
            print("  Use 'doctor check' for a full diagnostic.")
        return 0
    except Exception as e:
        print(f"\n  ❌ Safe mode error: {e}")
        return 2


def cmd_trend(args) -> int:
    """Show health history trends."""
    try:
        from recovery import get_health_trend
        count = args.limit if args.limit else 20
        records = get_health_trend(count)

        print_header("OMEGA DOCTOR — HEALTH TREND")
        if not records:
            print("\n  📭 No health history available.")
            print("  Run 'doctor check' to create the first record.")
            return 0

        print(f"\n  Last {len(records)} health checks:\n")
        print(f"  {'Time':<22} {'Passed':>8} {'Failed':>8} {'Health':>8}")
        print(f"  {'─' * 48}")
        for r in records:
            total = r.get("total", 1)
            pct = (r.get("passed", 0) / max(total, 1)) * 100
            icon = "🟢" if pct >= 80 else "🟡" if pct >= 50 else "🔴"
            print(f"  {r['timestamp'][:19]:<22} "
                  f"{r.get('passed', 0):>8} "
                  f"{r.get('failed', 0):>8} "
                  f"{icon} {pct:>5.0f}%")

        # Average
        avg_passed = sum(r.get("passed", 0) for r in records) / len(records)
        avg_failed = sum(r.get("failed", 0) for r in records) / len(records)
        print(f"\n  Average: {avg_passed:.1f} passed / {avg_failed:.1f} failed per check")
        print()

        return 0
    except Exception as e:
        print(f"\n  ❌ Trend error: {e}")
        return 2


# ──────────────────────────────────────────────
#  INTERACTIVE SHELL
# ──────────────────────────────────────────────

def interactive_shell():
    """Run an interactive doctor shell."""
    print("\n🧬 OMEGA Doctor Interactive Shell")
    print("Type 'help' for commands, 'exit' to quit.\n")

    while True:
        try:
            cmd = input("🏥 doctor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue
        if cmd in ("exit", "quit", "q"):
            break
        if cmd == "help":
            print("""
  Commands:
    check           Run full diagnostics
    repair          Run auto-repair
    status          Show system health
    monitor start   Start background monitor
    monitor stop    Stop background monitor
    monitor status  Show monitor status
    snapshot        Create a recovery snapshot
    snapshots       List recovery snapshots
    recover <file>  Recover a file from snapshot
    safemode        Enter safe mode
    trend           Show health history trend
    help            Show this help
    exit            Exit doctor shell
            """)
            continue

        # Parse command
        parts = cmd.split()
        cmd_name = parts[0]
        cmd_args = parts[1:] if len(parts) > 1 else []

        # Create a mock args namespace
        class Args:
            pass

        a = Args()

        if cmd_name == "check":
            a.json = False
            cmd_check(a)
        elif cmd_name == "repair":
            a.no_syntax = False
            a.no_config = False
            a.no_cache = False
            a.no_dirs = False
            a.json = False
            cmd_repair(a)
        elif cmd_name == "status":
            cmd_status(a)
        elif cmd_name == "monitor" and cmd_args:
            a.monitor_action = cmd_args[0]
            a.interval = int(cmd_args[1]) if len(cmd_args) > 1 else 300
            a.no_auto_repair = False
            cmd_monitor(a)
        elif cmd_name == "snapshot" and cmd_args and cmd_args[0] == "create":
            a.snapshot_action = "create"
            a.name = None
            cmd_snapshot(a)
        elif cmd_name in ("snapshot", "snapshots") and (not cmd_args or cmd_args[0] == "list"):
            a.snapshot_action = "list"
            cmd_snapshot(a)
        elif cmd_name == "recover" and cmd_args:
            a.file = cmd_args[0]
            cmd_recover(a)
        elif cmd_name == "safemode":
            cmd_safemode(a)
        elif cmd_name == "trend":
            a.limit = int(cmd_args[0]) if cmd_args else 20
            cmd_trend(a)
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")


# ──────────────────────────────────────────────
#  CLI PARSER
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omega-doctor",
        description="🧬 OMEGA Doctor — Self-Repair & Health System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  check              Run full diagnostics
  repair             Run auto-repair
  monitor            Manage background health monitor
  snapshot           Manage recovery snapshots
  recover <file>     Recover a file from snapshot
  status             Show overall system health
  safemode           Enter safe mode
  trend              Show health history trends
  shell              Interactive doctor shell
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # check
    p_check = subparsers.add_parser("check", help="Run full diagnostics")
    p_check.add_argument("--json", action="store_true", help="Output as JSON")

    # repair
    p_repair = subparsers.add_parser("repair", help="Run auto-repair")
    p_repair.add_argument("--no-syntax", action="store_true", help="Skip syntax fix")
    p_repair.add_argument("--no-config", action="store_true", help="Skip config fix")
    p_repair.add_argument("--no-cache", action="store_true", help="Skip cache cleanup")
    p_repair.add_argument("--no-dirs", action="store_true", help="Skip directory fix")
    p_repair.add_argument("--json", action="store_true", help="Output as JSON")

    # monitor
    p_mon = subparsers.add_parser("monitor", help="Manage health monitor")
    p_mon.add_argument("monitor_action", choices=["start", "stop", "status"],
                       help="Action to perform")
    p_mon.add_argument("--interval", type=int, default=300, help="Check interval (seconds)")
    p_mon.add_argument("--no-auto-repair", action="store_true", help="Disable auto-repair")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Manage recovery snapshots")
    p_snap.add_argument("snapshot_action", choices=["create", "list", "restore", "cleanup"],
                        help="Action to perform")
    p_snap.add_argument("--name", help="Snapshot name (for create/restore)")
    p_snap.add_argument("--target-dir", help="Restore to target directory")
    p_snap.add_argument("--keep", type=int, default=5, help="Number of snapshots to keep (cleanup)")

    # recover
    p_rec = subparsers.add_parser("recover", help="Recover a file from snapshot")
    p_rec.add_argument("file", help="File to recover")

    # status
    subparsers.add_parser("status", help="Show system health")

    # safemode
    subparsers.add_parser("safemode", help="Enter safe mode")

    # trend
    p_trend = subparsers.add_parser("trend", help="Show health trends")
    p_trend.add_argument("--limit", type=int, default=20, help="Number of records to show")

    # shell
    subparsers.add_parser("shell", help="Interactive doctor shell")

    return parser


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command or args.command == "shell":
        interactive_shell()
        return

    commands = {
        "check": cmd_check,
        "repair": cmd_repair,
        "monitor": cmd_monitor,
        "snapshot": cmd_snapshot,
        "recover": cmd_recover,
        "status": cmd_status,
        "safemode": cmd_safemode,
        "trend": cmd_trend,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        exit_code = cmd_func(args)
        sys.exit(exit_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
