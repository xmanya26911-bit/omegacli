#!/usr/bin/env python3
"""
📊 OMEGA DOCTOR — BACKGROUND MONITOR DAEMON
Continuous health monitoring:
  - Periodic diagnostics
  - Auto-repair on failure detection
  - Alert generation (toast notifications)
  - Health state history
  - Trend analysis
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable

OMEGA_DIR = Path(__file__).resolve().parent.parent
MONITOR_LOG = OMEGA_DIR / "omega_doctor" / "monitor.log"
HEALTH_HISTORY = OMEGA_DIR / "omega_doctor" / "recovery_points" / "health_history.jsonl"


def log(msg: str):
    """Append to monitor log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MONITOR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except OSError:
        pass


# ──────────────────────────────────────────────
#  MONITOR ENGINE
# ──────────────────────────────────────────────

class MonitorDaemon:
    """
    Background health monitor that runs diagnostics periodically
    and triggers repairs when failures are detected.
    """

    def __init__(self, interval: int = 300, auto_repair: bool = True):
        """
        Args:
            interval: Seconds between health checks (default 300 = 5 min)
            auto_repair: Whether to auto-run repair on failure
        """
        self.interval = interval
        self.auto_repair = auto_repair
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_report: Optional[dict] = None
        self._check_count = 0
        self._failure_count = 0
        self._callbacks: List[Callable] = []

    def on_failure(self, callback: Callable):
        """Register a callback to be called on health check failure."""
        self._callbacks.append(callback)

    def _run_health_check(self) -> dict:
        """Run a quick health check and return the report dict."""
        try:
            from diagnostics import quick_health
            report = quick_health()
            return report.to_dict()
        except Exception as e:
            # If diagnostics module itself is broken, do a minimal check
            critical = ["agent.py", "tools.py", "llm.py", "config.py"]
            checks = []
            for fname in critical:
                fpath = OMEGA_DIR / fname
                exists = fpath.exists() and fpath.stat().st_size > 100
                checks.append({
                    "name": f"File: {fname}",
                    "passed": exists,
                    "detail": "" if exists else f"Missing or empty: {fname}",
                    "severity": "critical",
                })
            return {
                "timestamp": datetime.now().isoformat(),
                "total": len(checks),
                "passed": sum(1 for c in checks if c["passed"]),
                "failed": sum(1 for c in checks if not c["passed"]),
                "checks": checks,
            }

    def _save_health_record(self, report: dict):
        """Append health record to history file."""
        try:
            HEALTH_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": datetime.now().isoformat(),
                "passed": report.get("passed", 0),
                "failed": report.get("failed", 0),
                "total": report.get("total", 0),
            }
            with open(HEALTH_HISTORY, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    def _notify(self, title: str, message: str):
        """Send a notification (toast on Windows)."""
        try:
            from plyer import notification
            notification.notify(title=title, message=message, timeout=5)
        except ImportError:
            try:
                # Fall back to PowerShell toast
                import subprocess
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $textNodes = $template.GetElementsByTagName("text")
                $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
                $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("OMEGA Doctor").Show($toast)
                '''
                subprocess.run(["powershell", "-Command", ps_script],
                               capture_output=True, timeout=10)
            except Exception:
                pass  # No notification capability

    def _loop(self):
        """Main monitor loop — runs in background thread."""
        log(f"Monitor started (interval={self.interval}s, auto_repair={self.auto_repair})")

        while not self._stop_event.is_set():
            try:
                report = self._run_health_check()
                self._latest_report = report
                self._check_count += 1

                failed = report.get("failed", 0)
                if failed > 0:
                    self._failure_count += 1
                    log(f"⚠️  Health check #{self._check_count}: {failed} failures")

                    # Get critical failures
                    critical = [c for c in report.get("checks", [])
                                if not c.get("passed", True) and c.get("severity") == "critical"]
                    if critical:
                        names = [c["name"] for c in critical]
                        self._notify(
                            "🩺 OMEGA Doctor Alert",
                            f"{len(critical)} critical issue(s): {', '.join(names[:3])}"
                        )

                        # Auto-repair if enabled
                        if self.auto_repair:
                            try:
                                from repair_engine import run_auto_repair
                                log("Auto-repair triggered by monitor...")
                                repair_report = run_auto_repair()
                                if repair_report.fail_count == 0:
                                    log("Auto-repair successful!")
                                    self._notify(
                                        "🩺 OMEGA Doctor",
                                        f"Auto-repaired {repair_report.success_count} issues."
                                    )
                                else:
                                    log(f"Auto-repair partial: {repair_report.success_count} OK, "
                                        f"{repair_report.fail_count} failed")
                            except Exception as e:
                                log(f"Auto-repair failed: {e}")

                    # Call failure callbacks
                    for cb in self._callbacks:
                        try:
                            cb(report)
                        except Exception:
                            pass
                else:
                    log(f"✅ Health check #{self._check_count}: All passed")

                # Save history
                self._save_health_record(report)

            except Exception as e:
                log(f"❌ Monitor loop error: {e}")

            # Wait for next check or stop signal
            self._stop_event.wait(self.interval)

        log("Monitor stopped.")

    def start(self):
        """Start the monitor in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            log("Monitor already running")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                         name="omega-doctor-monitor")
        self._thread.start()
        log("Monitor daemon started")
        return True

    def stop(self):
        """Signal the monitor to stop."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=10)
            log("Monitor stopped")
            return True
        return False

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def latest_report(self) -> Optional[dict]:
        return self._latest_report

    def get_stats(self) -> dict:
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval,
            "auto_repair": self.auto_repair,
            "checks_performed": self._check_count,
            "failures_detected": self._failure_count,
            "latest_check": self._latest_report,
        }


# ──────────────────────────────────────────────
#  SINGLETON INSTANCE
# ──────────────────────────────────────────────

_monitor: Optional[MonitorDaemon] = None


def get_monitor(interval: int = 300, auto_repair: bool = True) -> MonitorDaemon:
    """Get or create the singleton monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = MonitorDaemon(interval, auto_repair)
    return _monitor


def start_monitor(interval: int = 300, auto_repair: bool = True) -> bool:
    """Convenience: start the background monitor."""
    mon = get_monitor(interval, auto_repair)
    return mon.start()


def stop_monitor() -> bool:
    """Convenience: stop the background monitor."""
    global _monitor
    if _monitor:
        return _monitor.stop()
    return False


def monitor_status() -> dict:
    """Convenience: get monitor status."""
    global _monitor
    if _monitor:
        return _monitor.get_stats()
    return {"is_running": False, "checks_performed": 0, "failures_detected": 0}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "start":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            start_monitor(interval)
            print(f"✅ Monitor started (interval={interval}s)")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_monitor()
                print("Monitor stopped.")
        elif action == "stop":
            stop_monitor()
            print("Monitor stopped.")
        elif action == "status":
            status = monitor_status()
            print(f"\n  📊 OMEGA Doctor Monitor Status")
            print(f"  {'🟢 Running' if status['is_running'] else '🔴 Stopped'}")
            print(f"  Checks performed: {status['checks_performed']}")
            print(f"  Failures detected: {status['failures_detected']}")
            print(f"  Auto-repair: {'ON' if status.get('auto_repair') else 'OFF'}")
            print()
        else:
            print(f"Usage: {sys.argv[0]} [start|stop|status] [interval_seconds]")
    else:
        print(f"Usage: {sys.argv[0]} [start|stop|status] [interval_seconds]")
