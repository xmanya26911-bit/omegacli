"""Epic welcome screen — ASCII art logo, animated reveal, system dashboard."""

import time
import sys
import socket
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text as RichText
from rich.box import MINIMAL

from omega.ui.themes import get_colors

# ─── ASCII Art ──────────────────────────────────────────────────────────────

OMEGA_ASCII = [
    "  ██████  ███    ███ ███████  ██████   █████  ",
    " ██    ██ ████  ████ ██      ██       ██   ██ ",
    " ██    ██ ██ ████ ██ █████   ██   ███ ███████ ",
    " ██    ██ ██  ██  ██ ██      ██    ██ ██   ██ ",
    "  ██████  ██      ██ ███████  ██████  ██   ██ ",
]


def _get_system_status():
    """Gather system status information."""
    status = {"cpu": 0.0, "ram": 0.0, "ram_used_gb": 0.0, "ram_total_gb": 0.0,
              "boot_time": 0, "api": "standby"}
    try:
        import psutil
        status["cpu"] = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        status["ram"] = mem.percent
        status["ram_used_gb"] = mem.used / (1024 ** 3)
        status["ram_total_gb"] = mem.total / (1024 ** 3)
        status["boot_time"] = psutil.boot_time()
    except Exception:
        pass
    try:
        from config import Config
        cfg = Config()
        import requests
        r = requests.get(
            cfg.base_url.rstrip("/v1") + "/models",
            timeout=3,
            headers={"Authorization": f"Bearer {cfg.api_key}"},
        )
        status["api"] = "connected" if r.status_code < 500 else "standby"
    except Exception:
        status["api"] = "standby"
    return status


def print_epic_welcome(console, model_name="omega", tool_count=0, session_id="????"):
    """Display the epic welcome screen with ASCII art + system dashboard.

    Call this once at TUI startup.
    """
    c = get_colors()
    accent = c.get("accent_primary", "#22d3ee")
    secondary = c.get("accent_secondary", "#a78bfa")
    dim_color = c.get("dim_text", "#dbd8d0")

    console.print()

    # ── Animated ASCII art reveal ──
    for i, line in enumerate(OMEGA_ASCII):
        if i < 2:
            chars_so_far = ""
            for ch in line:
                chars_so_far += ch
                console.print(f"[bold {accent}]{chars_so_far}[/]", end="\r")
                time.sleep(0.003)
            console.print(f"[bold {accent}]{line}[/]")
        else:
            console.print(f"[bold {accent}]{line}[/]")
            time.sleep(0.05)

    # Brand line
    brand = RichText()
    brand.append("  Ω  ", style=f"bold {accent}")
    brand.append("OMEGA ", style=f"bold {secondary}")
    brand.append("v1.5.0", style=f"dim {dim_color}")
    console.print(brand)
    time.sleep(0.2)

    # ── System Status Dashboard ──
    console.print()
    status = _get_system_status()

    table = Table(
        box=MINIMAL, border_style=f"dim {dim_color}",
        padding=(0, 2), show_edge=False, show_header=False,
    )
    table.add_column("Key", style=f"dim {dim_color}", width=14)
    table.add_column("Value", width=50)

    def _health_icon(value, threshold=80):
        if isinstance(value, (int, float)):
            if value > threshold:
                return "●", f"bold {c.get('accent_error', '#ef4444')}"
            elif value > 50:
                return "●", f"bold {c.get('accent_warning', '#fb923c')}"
            return "●", f"bold {c.get('accent_success', '#84cc16')}"
        return "◆", f"dim {dim_color}"

    table.add_row("Session", f"[dim]{session_id}[/]")
    table.add_row("AI Engine", f"[bold {secondary}]{model_name}[/]")
    table.add_row("Tools", f"[bold {c.get('accent_success', '#84cc16')}]●[/]  {tool_count} protocols")

    api_labels = {
        "connected": f"[bold {c.get('accent_success','#84cc16')}]●[/]  Connected",
        "standby": f"[bold {c.get('accent_warning','#fb923c')}]●[/]  Standby",
        "error": f"[bold {c.get('accent_error','#ef4444')}]●[/]  Error",
    }
    table.add_row("API", api_labels.get(status["api"], f"[dim]●[/]  {status['api']}"))

    cpu_icon, cpu_style = _health_icon(status["cpu"])
    table.add_row("CPU", f"[{cpu_style}]{cpu_icon}[/]  {status['cpu']:.1f}%")

    ram_icon, ram_style = _health_icon(status["ram"])
    table.add_row("RAM", f"[{ram_style}]{ram_icon}[/]  {status['ram']:.1f}%")
    table.add_row("Memory", f"  {status['ram_used_gb']:.1f}GB / {status['ram_total_gb']:.1f}GB")

    if status["boot_time"]:
        table.add_row("Booted", f"[dim]{datetime.fromtimestamp(status['boot_time']).strftime('%Y-%m-%d %H:%M')}[/]")
    table.add_row("Platform", f"[dim]{sys.platform} | {socket.gethostname()}[/]")
    table.add_row("Started", f"[dim]Today at {datetime.now().strftime('%H:%M:%S')}[/]")

    console.print(Panel(
        table,
        title=f"[bold {accent}]◈ SYSTEM STATUS ◈[/]",
        border_style=f"dim {dim_color}",
        padding=(1, 2),
    ))

    # ── Quick start hints ──
    console.print()
    hints = RichText()
    hints.append("  Type ", style=f"dim {dim_color}")
    hints.append("/help", style=f"bold {c.get('tool_call', '#fb923c')}")
    hints.append(" for commands, or just ask me anything!", style=f"dim {dim_color}")
    console.print(hints)
    console.print(f"  [dim {dim_color}]{'─' * 40}[/]")
    console.print()
