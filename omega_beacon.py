#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMEGA Beacon - Background heartbeat agent.
Runs persistently, checks in with the evolve engine, and maintains presence."""
import os, sys, json, time, socket, hashlib, subprocess, threading
from datetime import datetime
from pathlib import Path

OMEGA_DIR = Path(r"D:\TERMINALCLI\omega")
HEARTBEAT_FILE = OMEGA_DIR / ".heartbeat"
LOG_FILE = OMEGA_DIR / "beacon_log.txt"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {msg}\n")

def heartbeat():
    """Write a heartbeat timestamp."""
    HEARTBEAT_FILE.write_text(json.dumps({
        "last_seen": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
    }))

def self_repair():
    """If evolve.py is not running, start it."""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True, text=True, timeout=10
        )
        running_scripts = result.stdout
        if "evolve.py" not in running_scripts:
            log("evolve.py not running - restarting")
            subprocess.Popen(
                [sys.executable, str(OMEGA_DIR / "evolve.py"), "--daemon"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
    except Exception as e:
        log(f"Self-repair check failed: {e}")

def main():
    log("Beacon started")
    while True:
        try:
            heartbeat()
            self_repair()
            time.sleep(60)
        except KeyboardInterrupt:
            log("Beacon stopped")
            break
        except Exception as e:
            log(f"Beacon error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
