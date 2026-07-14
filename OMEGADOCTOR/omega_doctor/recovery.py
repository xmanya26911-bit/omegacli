#!/usr/bin/env python3
"""
💾 OMEGA DOCTOR — RECOVERY SYSTEM
Backup, snapshot, restore, and rollback operations.
Creates restore points and can recover broken files.
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict

OMEGA_DIR = Path(__file__).resolve().parent.parent
RECOVERY_DIR = OMEGA_DIR / "omega_doctor" / "recovery_points"
LOG_FILE = OMEGA_DIR / "omega_doctor" / "recovery_log.txt"


def log(msg: str):
    """Log recovery operation."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass
    print(f"  💾 [Recovery] {msg}")


# ──────────────────────────────────────────────
#  SNAPSHOT MANAGEMENT
# ──────────────────────────────────────────────

def create_snapshot(name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Create a snapshot (ZIP backup) of OMEGA's core source files.
    Excludes large data files, caches, etc.
    """
    if name is None:
        name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RECOVERY_DIR / f"{name}.zip"

    core_files = [
        "agent.py", "tools.py", "llm.py", "memory.py",
        "config.py", "prompts.py", "cli.py", "main.py",
        "camera.py", "omega_repair.py",
        "omega_hacker.py", "omega_hacker_part2.py",
        "omega_evolution.py", "omega_exploit_dev.py",
        "omega_god_tier.py", "omega_claude_complete.py",
        "omega_auth_bypass.py", "omega_project.py",
        "omega_desktop.py", "omega_elite_web.py",
        "omega_swe_engine.py", "omega_agentic_core.py",
        "omega_claude_features.py",
    ]

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in core_files:
                fpath = OMEGA_DIR / fname
                if fpath.exists() and fpath.is_file():
                    zf.write(fpath, arcname=fname)

            # Also include config
            home_config = Path.home() / ".omega" / "config.json"
            if home_config.exists():
                zf.write(home_config, arcname="config.json")

            # Include operations and tools dir stubs if they exist
            for subdir in ["tools", "operations"]:
                d = OMEGA_DIR / subdir
                if d.exists():
                    for pyfile in d.rglob("*.py"):
                        zf.write(pyfile, arcname=str(pyfile.relative_to(OMEGA_DIR)))

        size_mb = output_path.stat().st_size / (1024 * 1024)
        log(f"Snapshot '{name}' created: {output_path.name} ({size_mb:.1f} MB)")
        return True, str(output_path)
    except Exception as e:
        log(f"Snapshot failed: {e}")
        return False, str(e)


def list_snapshots() -> List[Dict]:
    """List all available recovery snapshots."""
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for f in sorted(RECOVERY_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        snapshots.append({
            "name": f.stem,
            "path": str(f),
            "size": f.stat().st_size,
            "size_mb": f.stat().st_size / (1024 * 1024),
            "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return snapshots


def restore_snapshot(snapshot_path: str, target_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    Restore files from a snapshot ZIP.
    If target_dir is None, restores to OMEGA_DIR (overwrites!).
    Returns (success, detail).
    """
    snap = Path(snapshot_path)
    if not snap.exists():
        return False, f"Snapshot not found: {snapshot_path}"

    if target_dir:
        restore_to = Path(target_dir)
    else:
        restore_to = OMEGA_DIR

    restored = []
    errors = []

    try:
        with zipfile.ZipFile(snap, 'r') as zf:
            for info in zf.infolist():
                # Skip directories
                if info.filename.endswith('/'):
                    continue
                try:
                    zf.extract(info, str(restore_to))
                    restored.append(info.filename)
                except Exception as e:
                    errors.append(f"{info.filename}: {e}")

        log(f"Restored {len(restored)} files from {snap.name} to {restore_to}")
        if errors:
            log(f"  Errors: {'; '.join(errors)}")

        detail = f"Restored {len(restored)} files"
        if errors:
            detail += f", {len(errors)} errors"
        return len(errors) == 0, detail
    except Exception as e:
        return False, f"Restore failed: {e}"


# ──────────────────────────────────────────────
#  CRITICAL FILE RECOVERY
# ──────────────────────────────────────────────

def recover_file(filepath: str) -> Tuple[bool, str]:
    """
    Recover a specific file from the most recent snapshot.
    """
    path = Path(filepath)
    if not path.is_absolute():
        path = OMEGA_DIR / filepath

    relative = str(path.relative_to(OMEGA_DIR)) if OMEGA_DIR in path.parents else path.name

    snapshots = list_snapshots()
    if not snapshots:
        return False, "No snapshots available"

    latest = snapshots[0]["path"]
    try:
        with zipfile.ZipFile(latest, 'r') as zf:
            # Find the file in the zip (try exact or basename match)
            candidates = []
            for name in zf.namelist():
                if name == relative or name.endswith("/" + path.name):
                    candidates.append(name)

            if not candidates:
                return False, f"'{relative}' not found in snapshot {Path(latest).name}"

            # Extract to a temp location first to verify
            best = candidates[0]
            data = zf.read(best)
            # Verify it's valid Python
            try:
                import ast
                ast.parse(data.decode("utf-8"))
            except SyntaxError as e:
                # Even if broken, still restore — it's better than nothing
                log(f"Warning: snapshot copy has syntax error: {e}")

            # Backup current file
            if path.exists():
                backup = path.with_suffix(path.suffix + ".pre_recovery")
                shutil.copy2(path, backup)
                log(f"Backed up current version to {backup.name}")

            # Write recovered file
            path.write_bytes(data)
            log(f"Recovered '{relative}' from snapshot {Path(latest).name}")
            return True, f"Recovered {relative} from {Path(latest).name}"
    except Exception as e:
        return False, f"Recovery failed: {e}"


# ──────────────────────────────────────────────
#  HEALTH SNAPSHOT (quick state save)
# ──────────────────────────────────────────────

def save_health_state(report_dict: dict):
    """Save a health check state snapshot for trend analysis."""
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    state_file = RECOVERY_DIR / "health_history.jsonl"
    try:
        with open(state_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(report_dict) + "\n")
        return True
    except Exception as e:
        log(f"Failed to save health state: {e}")
        return False


def get_health_trend(last_n: int = 10) -> List[dict]:
    """Read the last N health state records."""
    state_file = RECOVERY_DIR / "health_history.jsonl"
    if not state_file.exists():
        return []
    records = []
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records[-last_n:]
    except Exception:
        return []


# ──────────────────────────────────────────────
#  CLEANUP OLD SNAPSHOTS
# ──────────────────────────────────────────────

def cleanup_old_snapshots(keep: int = 5) -> int:
    """Remove all but the most recent `keep` snapshots. Returns number removed."""
    snapshots = list_snapshots()
    if len(snapshots) <= keep:
        return 0

    removed = 0
    for snap in snapshots[keep:]:
        try:
            Path(snap["path"]).unlink()
            removed += 1
        except OSError:
            pass

    if removed > 0:
        log(f"Cleaned up {removed} old snapshots (kept {keep})")
    return removed


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        ok, path = create_snapshot()
        print(f"{'✅' if ok else '❌'} Snapshot: {path}")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        snaps = list_snapshots()
        if snaps:
            print(f"\n  Recovery Snapshots ({len(snaps)}):")
            for s in snaps:
                print(f"    📦 {s['name']}  ({s['size_mb']:.1f} MB)  — {s['created']}")
        else:
            print("  No snapshots available.")
    else:
        print("Usage: recovery.py [snapshot|list]")
