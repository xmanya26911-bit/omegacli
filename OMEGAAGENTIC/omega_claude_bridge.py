"""
OMEGA <-> CLAUDE CODE INTEGRATION BRIDGE
==========================================
Bridges OMEGA (Python) with the REAL Claude Code CLI (claude.exe).

Provides launch, config sync, and status monitoring.

Uses:
  Binary: C:/Users/pc/.local/bin/claude.exe
  Source: D:/TERMINALCLI/omega/claude-core/

Author: OMEGA AI
"""

import os
import sys
import json
import subprocess
import shutil
import tempfile
import io
from pathlib import Path
from datetime import datetime

# ─── Console Encoding Fix ─────────────────────────────────────────
_ENC_FIXED = False
def _fix_enc():
    global _ENC_FIXED
    if _ENC_FIXED:
        return
    _ENC_FIXED = True
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            except Exception:
                pass
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            try:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
            except Exception:
                pass

# ─── Emoji-safe printing ─────────────────────────────────────────
# Replace unicode emojis with ASCII equivalents for Windows console
_EMOJI_MAP = {
    "\U0001f300": "~",   # 🌀
    "\u274c": "X",       # ❌
    "\u2705": "V",       # ✅
    "\U0001f4e6": "[]",  # 📦
    "\u2699\ufe0f": "[*]", # ⚙️
    "\U0001f517": "<>",  # 🔗
    "\u2139": "i",       # ℹ️
    "\u26a0": "!",       # ⚠️
    "\U0001f680": "->",  # 🚀
    "\u23f3": "!t",       # ⏳
    "\u2b50": "*",       # ⭐
    "\U0001f525": "~f",   # 🔥
    "\U0001f44d": "+",    # 👍
    "\u23f0": "!a",       # ⏰
    "\u270f": "(/",      # ✏️
    "\U0001f4cb": "[]",   # 📋
    "\u2714": "V",       # ✔
    "\U0001f511": "(k)",  # 🔑
    "\U0001f4a1": "(i)",  # 💡
    "\U0001f50d": "(s)",  # 🔍
    "\u2611": "V",       # ☑
    "\U0001f504": "<->",  # 🔄
}

def _safe(text: str) -> str:
    """Replace emojis with ASCII safe equivalents."""
    for emoji, repl in _EMOJI_MAP.items():
        text = text.replace(emoji, repl)
    return text

def _print(text: str = ""):
    """Print with safe encoding."""
    _fix_enc()
    try:
        print(_safe(text))
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

# ─── CONSTANTS ───────────────────────────────────────────────────────────────

CLAUDE_BINARY = r"C:\Users\pc\.local\bin\claude.exe"
CLAUDE_CORE_DIR = Path(__file__).parent / "claude-core"
CLAUDE_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", r"C:\Users\pc\.claude"))
CLAUDE_GLOBAL_CONFIG = Path(os.environ.get("CLAUDE_GLOBAL_CONFIG", r"C:\Users\pc\.claude.json"))
CLAUDE_ALIAS_SCRIPT = Path(__file__).parent / "claude.ps1"
CLAUDE_BAT_SCRIPT = Path(__file__).parent / "claude.bat"
OMEGA_CLAUDE_LOG = Path(__file__).parent / "claude-bridge.log"

# ─── SUPPORTED FEATURES ──────────────────────────────────────────────────────

SUPPORTED_MODES = {
    "tui": "Full interactive Terminal UI (the real Claude Code experience)",
    "pipe": "Pipe mode (stdin/stdout for scripted use)",
    "noninteractive": "Non-interactive mode for automation",
}

# ─── BRIDGE ENGINE ───────────────────────────────────────────────────────────


def log(msg: str):
    """Log a message to the bridge log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(OMEGA_CLAUDE_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {_safe(msg)}\n")
    except Exception:
        pass


def detect_claude_binary() -> bool:
    """Detect if claude.exe is installed and accessible."""
    if not os.path.exists(CLAUDE_BINARY):
        log("Claude binary not found at: " + CLAUDE_BINARY)
        return False
    
    if os.path.isdir(CLAUDE_BINARY):
        log("Path is a directory, not an executable: " + CLAUDE_BINARY)
        return False
    
    size = os.path.getsize(CLAUDE_BINARY)
    log(f"Claude binary found: {CLAUDE_BINARY} ({size:,} bytes)")
    return True


def get_claude_version() -> str:
    """Get version info from Claude Code binary."""
    try:
        result = subprocess.run(
            [CLAUDE_BINARY, "--version"],
            capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip() or result.stderr.strip() or "unknown"
        log(f"Claude Code version: {version}")
        return version
    except Exception as e:
        log(f"Could not get version: {e}")
        return "unknown"


def get_current_config() -> dict:
    """Read the current .claude.json global config."""
    try:
        if CLAUDE_GLOBAL_CONFIG.exists():
            with open(CLAUDE_GLOBAL_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        log(f"Could not read global config: {e}")
        return {}


def get_settings() -> dict:
    """Read the settings.json from config dir."""
    settings_path = CLAUDE_CONFIG_DIR / "settings.json"
    try:
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        log(f"Could not read settings: {e}")
        return {}


def sync_omega_config_to_claude():
    """
    Sync OMEGA's model configuration to Claude Code's settings.
    Allows OMEGA to configure which model Claude Code uses.
    """
    omega_config_path = Path(__file__).parent / "omega_config.json"
    if not omega_config_path.exists():
        log("No OMEGA config found, skipping sync")
        return False
    
    try:
        with open(omega_config_path, "r", encoding="utf-8") as f:
            omega_config = json.load(f)
    except Exception as e:
        log(f"Could not read OMEGA config: {e}")
        return False
    
    log("Config sync check complete")
    return True


def launch_claude_tui(args: list = None) -> int:
    """
    Launch the REAL Claude Code TUI (claude.exe) with given arguments.
    
    Returns:
        Exit code from claude.exe
    """
    if not detect_claude_binary():
        _print("  X Claude Code binary not found!")
        _print(f"     Expected at: {CLAUDE_BINARY}")
        _print("  Run 'omega --install-claude' to fix this.")
        return 1
    
    if args is None:
        args = []
    
    cmd = [CLAUDE_BINARY] + args
    
    _print()
    _print("=" * 70)
    _print("  OMEGA -> REAL CLAUDE CODE BRIDGE")
    _print("  Launching authentic Claude Code Terminal UI...")
    _print("  (Type /exit or Ctrl+C to return to OMEGA)")
    _print("=" * 70)
    _print()
    
    log(f"Launching Claude Code: {' '.join(cmd)}")
    
    try:
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(CLAUDE_CONFIG_DIR)
        
        # Claude Code takes over the terminal
        result = subprocess.run(cmd, env=env)
        
        if result.returncode == 0:
            log("Claude Code exited cleanly")
        else:
            log(f"Claude Code exited with code {result.returncode}")
        
        return result.returncode
    
    except KeyboardInterrupt:
        _print("\n  Claude Code interrupted by user")
        log("Claude Code interrupted by user")
        return 0
    except Exception as e:
        log(f"Error launching Claude Code: {e}")
        _print(f"\n  X Error: {e}")
        return 1


def launch_claude_pipe(command: str = None) -> str:
    """
    Launch Claude Code in pipe mode (non-interactive, one-shot).
    """
    if not detect_claude_binary():
        return "X Claude Code binary not found"
    
    if not command:
        command = "Hello, what can you do?"
    
    cmd = [CLAUDE_BINARY, "--print", command]
    
    log(f"Claude Code pipe: {command[:100]}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(CLAUDE_CONFIG_DIR)}
        )
        
        output = result.stdout or result.stderr or ""
        log(f"Claude Code response ({len(output)} chars)")
        return output
    
    except subprocess.TimeoutExpired:
        log("Claude Code pipe timed out")
        return "Timeout: Claude Code took too long to respond"
    except Exception as e:
        log(f"Pipe error: {e}")
        return f"Error: {e}"


def install_claude_aliases():
    """
    Install claude.bat and claude.ps1 into OMEGA's directory
    so that running 'claude' from OMEGA's shell works.
    """
    # Create claude.bat for cmd.exe
    bat_content = f"""@echo off
REM OMEGA Bridge -> Claude Code CLI
REM Bridges OMEGA to the REAL Claude Code binary
REM Installed by OMEGA Claude Bridge on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"{CLAUDE_BINARY}" %*
"""
    with open(CLAUDE_BAT_SCRIPT, "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    # Create claude.ps1 for PowerShell
    ps1_content = f"""# OMEGA Bridge -> Claude Code CLI
# Bridges OMEGA to the REAL Claude Code binary
# Installed by OMEGA Claude Bridge on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

$claudeBinary = "{CLAUDE_BINARY}"

if (-not (Test-Path $claudeBinary)) {{
    Write-Error "Claude Code binary not found at: $claudeBinary"
    exit 1
}}

& $claudeBinary @args
"""
    with open(CLAUDE_ALIAS_SCRIPT, "w", encoding="utf-8") as f:
        f.write(ps1_content)
    
    log("Claude aliases installed")
    _print("  V Claude Code aliases installed:")
    _print(f"     * claude.bat -> {CLAUDE_BAT_SCRIPT}")
    _print(f"     * claude.ps1 -> {CLAUDE_ALIAS_SCRIPT}")


# ─── OMEGA CLAUDE COMMAND HANDLER ────────────────────────────────────────────


def handle_claude_command(args: list) -> int:
    """
    Handle 'omega --claude' commands.
    Default (no args) = launch Claude Code TUI.
    """
    if "--help" in args or "-h" in args:
        _show_help()
        return 0
    
    if "--version" in args or "-v" in args:
        version = get_claude_version()
        _print(f"Claude Code: {version}")
        _print(f"Bridge: OMEGA Claude Bridge v1.0")
        return 0
    
    if "--check" in args or "--status" in args:
        return _show_status()
    
    if "--sync" in args:
        sync_omega_config_to_claude()
        _print("  V Config synced")
        return 0
    
    if "--pipemode" in args or "--pipe" in args:
        input_idx = -1
        for i, arg in enumerate(args):
            if arg.startswith("--input="):
                input_idx = i
                break
            if arg == "--input" and i + 1 < len(args):
                input_idx = i + 1
                break
        
        command = ""
        if input_idx >= 0:
            command = args[input_idx].replace("--input=", "", 1)
        
        response = launch_claude_pipe(command)
        _print(response)
        return 0
    
    # Default: Launch TUI with remaining args
    return launch_claude_tui(args)


def _show_help():
    """Show Claude bridge help."""
    _print("""
  OMEGA <-> CLAUDE CODE BRIDGE HELP
  ==================================

  USAGE:
    omega --claude                    Launch Claude Code TUI
    omega --claude --version          Show version info
    omega --claude --check            Show integration status
    omega --claude --sync             Sync OMEGA config to Claude Code
    omega --claude --pipe --input="p" Run in pipe mode (one-shot)
    omega --claude [args]             Pass args directly to claude.exe

  INSIDE CLAUDE CODE TUI:
    /help       Show help
    /exit       Exit back to OMEGA
    /model      Switch model
    /cost       Show cost info
    Ctrl+C      Interrupt / Return to OMEGA

  CLAUDE CORE SOURCE: D:/TERMINALCLI/omega/claude-core/
  CLAUDE BINARY:     C:/Users/pc/.local/bin/claude.exe
""")


def _show_status() -> int:
    """Show detailed integration status."""
    _fix_enc()
    _print()
    _print("=" * 60)
    _print("  OMEGA <-> CLAUDE CODE INTEGRATION STATUS")
    _print("=" * 60)
    
    # Check binary
    binary_ok = detect_claude_binary()
    _print(f"\n  CLAUDE CODE BINARY:")
    _print(f"     Path:    {CLAUDE_BINARY}")
    _print(f"     Status:  {'V OK' if binary_ok else 'X MISSING'}")
    
    if binary_ok:
        version = get_claude_version()
        _print(f"     Version: {version}")
    
    # Check source files
    _print(f"\n  CLAUDE CORE SOURCE:")
    _print(f"     Path:    {CLAUDE_CORE_DIR}")
    cli_js = CLAUDE_CORE_DIR / "cli.js"
    if cli_js.exists():
        size_kb = os.path.getsize(cli_js) / 1024
        _print(f"     cli.js:  V {size_kb:.0f} KB")
    else:
        _print(f"     cli.js:  X MISSING")
    
    package_json = CLAUDE_CORE_DIR / "package.json"
    if package_json.exists():
        with open(package_json, "r", encoding="utf-8") as f:
            pkg = json.load(f)
            _print(f"     Package: {pkg.get('name', 'unknown')} v{pkg.get('version', '?')}")
    
    # Check config
    _print(f"\n  CONFIGURATION:")
    _print(f"     Config Dir: {CLAUDE_CONFIG_DIR}")
    settings = get_settings()
    _print(f"     Settings:   {json.dumps(settings)}")
    
    global_config = get_current_config()
    if global_config:
        install_method = global_config.get("installMethod", "unknown")
        _print(f"     Install:    {install_method}")
    
    # Check aliases
    _print(f"\n  ALIASES:")
    _print(f"     claude.bat: {'V' if CLAUDE_BAT_SCRIPT.exists() else 'X'} {CLAUDE_BAT_SCRIPT}")
    _print(f"     claude.ps1: {'V' if CLAUDE_ALIAS_SCRIPT.exists() else 'X'} {CLAUDE_ALIAS_SCRIPT}")
    
    _print(f"\n  READY: Run 'omega --claude' to launch the REAL Claude Code!\n")
    return 0


# ─── CLI ENTRY POINT ─────────────────────────────────────────────────────────


def main():
    """CLI entry point when run directly."""
    _fix_enc()
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if not args or args[0] in ("--help", "-h"):
        _show_help()
        return
    
    if args[0] == "--install":
        install_claude_aliases()
        return
    
    handle_claude_command(args)


if __name__ == "__main__":
    main()
