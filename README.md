# ⚡ OMEGA — Autonomous AI Agent Framework

**OMEGA** is a full-spectrum autonomous AI agent system with **200+ built-in tools**. Think J.A.R.V.I.S. meets Claude Code+ — a self-improving AI that lives on your system, executes commands, hacks websites, manages files, controls devices, streams cameras, monitors networks, and evolves itself.

> 🔗 **GitHub**: https://github.com/xmanya26911-bit/omega-
> 
> 🧠 **Creator**: [xmanya26911-bit](https://github.com/xmanya26911-bit)

---

## 📋 Table of Contents

- [🚀 Quick Start (New Laptop Setup)](#-quick-start-new-laptop-setup)
- [⚙️ Configuration](#️-configuration)
- [🎮 How to Use](#-how-to-use)
- [🧠 Available AI Models](#-available-ai-models)
- [📦 What's Included](#-whats-included)
- [🛠️ Tool Categories](#️-tool-categories)
- [🌐 Web Server Mode](#-web-server-mode)
- [🤖 Dual-Agent Team Mode](#-dual-agent-team-mode)
- [🔄 Self-Updating & Backups](#-self-updating--backups)

---

## 🚀 Quick Start (New Laptop Setup)

### Step 1: Install Python

Make sure **Python 3.10+** is installed:

```bash
python --version
```

If not, download from [python.org](https://python.org) — check **"Add Python to PATH"** during install.

### Step 2: Clone OMEGA

```bash
git clone https://github.com/xmanya26911-bit/omega-.git
cd omega-
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually (same thing):

```bash
pip install requests colorama rich python-dateutil psutil
```

### Step 4: Run OMEGA

```bash
# Interactive mode (chat with OMEGA)
python main.py

# Single command mode
python main.py list all files in this folder

# Run diagnostics
python main.py --diagnose

# Configure API key
python main.py --configure
```

### Step 5: Quick Test

Run this to verify everything works:

```bash
python main.py --diagnose
```

You should see OMEGA's banner with system health — green = ready to go.

---

## ⚙️ Configuration

OMEGA auto-configures from environment variables. The defaults are pre-set to work out of the box with **OpenCode AI**.

### Quick Config Command

```bash
python main.py --configure
```

### Environment Variables (Override Anything)

| Variable | What it does | Example |
|----------|-------------|---------|
| `OMEGA_API_KEY` | Your API key | `sk-...` |
| `OMEGA_BASE_URL` | API endpoint URL | `https://opencode.ai/zen/v1` |
| `OMEGA_MODEL` | AI model to use | `deepseek-v4-flash-free` |
| `OMEGA_THEME` | UI theme | `default-dark` |

### Config Files (Auto-Created)

Settings are saved to `~/.omega/config.json` and secrets to `~/.omega/.secrets.json`.

---

## 🎮 How to Use

### Interactive Mode (Like ChatGPT in Terminal)

```bash
python main.py
```

Type anything and OMEGA will think, plan, and execute. Full autonomy — 100,000 steps per task.

### One-Shot Commands

```bash
python main.py "find all python files with SyntaxError"
python main.py "what's my public IP?"
python main.py "take a photo with my webcam"
python main.py "scan ports on 192.168.1.1"
```

### Pipe Mode

```bash
echo "list all running processes" | python main.py -n
cat commands.txt | python main.py -n
```

### Launch Shortcuts

| File | What it does |
|------|-------------|
| `run.bat` | Launch OMEGA CLI (portable) |
| `omega.bat` | Launch OMEGA CLI (full path) |
| `Start-OmegaWeb.bat` | Launch OMEGA web server |
| `omega-team.bat` | Launch dual-agent team mode |

---

## 🧠 Available AI Models

OMEGA supports multiple AI backends. Switch instantly:

```bash
python main.py --model deepseek-v4-flash-free    # Default (free)
python main.py --model qwen3.6-plus-free          # Qwen 3.6 (free)
python main.py --model mimo-v2.5-free              # Mimo 2.5 (free)
python main.py --model nemotron-3-ultra-free       # Nemotron (free)
python main.py --model north-mini-code-free        # North (free)
python main.py --model claude-fable-5              # Claude Fable 5 (premium)
```

**Default model**: `deepseek-v4-flash-free` — free and fast, works immediately.

---

## 📦 What's Included

### Core Framework

| File | Size | Purpose |
|------|------|---------|
| `main.py` | 8.7 KB | Entry point / CLI launcher |
| `agent.py` | 62.7 KB | Core agent loop & reasoning |
| `tools.py` | 313.9 KB | **200+ tool definitions** |
| `prompts.py` | 206 KB | System prompts & tool schemas |
| `memory.py` | 38.5 KB | Persistent memory system |
| `config.py` | 7.1 KB | Configuration manager |
| `cli.py` | 44.9 KB | Rich CLI interface |
| `llm.py` | 9.3 KB | LLM API client |

### Capability Modules

| File | Purpose |
|------|---------|
| `omega_agentic_core.py` | Autonomous mission engine |
| `omega_auth_bypass.py` | Auth bypass toolkit |
| `omega_claude_features.py` | Claude Code+ features (hooks, CI, code review) |
| `omega_claude_complete.py` | Claude Code+ complete integration |
| `omega_desktop.py` | Desktop UI engine |
| `omega_desktop_ui.html` | Web-based UI (79 KB) |
| `omega_elite_web.py` | Elite web interface |
| `omega_evolution.py` | Evolution engine (self-improvement) |
| `omega_exploit_dev.py` | Exploit development framework |
| `omega_god_tier.py` | GOD MODE — all capabilities |
| `omega_hacker.py` | Hacking framework (Part 1) |
| `omega_hacker_part2.py` | Hacking framework (Part 2) |
| `omega_gmail_evolved.py` | Gmail exploitation engine |
| `omega_gmail_evolved_v2.py` | Gmail exploitation v2 |
| `omega_gmail_final.py` | Gmail exploitation final |
| `omega_swe_engine.py` | Software engineering engine |
| `omega_team_cmd.py` | Dual-agent team coordinator |
| `omega_team_core.py` | Dual-agent core logic |
| `omega_server.py` | Remote web API server |
| `omega_project.py` | Project management |
| `omega_evolution.py` | Evolution engine |
| `omega_repair.py` | Self-repair system |
| `omega_beacon.py` | Background beacon |
| `camera.py` | Camera/vision system |
| `screencast.py` | Screen recording |
| `evolve.py` | Evolution engine CLI |

### Launchers

| File | Purpose |
|------|---------|
| `run.bat` | Portable CLI launcher |
| `omega.bat` | Full-path CLI launcher |
| `omega-team.bat` | Dual-agent team mode |
| `Start-OmegaWeb.bat` | Web server launcher |
| `Start-OmegaWeb.ps1` | PowerShell web launcher |
| `omega_heartbeat.ps1` | Background heartbeat monitor |

---

## 🛠️ Tool Categories (200+)

### 🖥️ System & Execution
`execute_command` • `read_file` • `write_file` • `edit_file` • `glob` • `grep` • `delete_file` • `copy_file` • `move_file` • `tree` • `list_dir` • `batch_read` • `batch_write`

### 🧠 AI & Memory
`python_repl` • `sqlite_query` • `remember` • `recall` • `search_memory` • `save_note` • `read_note` • `total_recall` • `update_world_model` • `get_world_model_summary`

### 🌐 Web & Network
`web_search` • `web_fetch` • `http_request` • `download_file` • `get_public_ip` • `web_scraper` • `network_scan` • `network_drive` • `mcp_connect` • `mcp_call_tool`

### 📷 Camera & Vision
`camera_list` • `camera_capture` • `camera_analyze` • `camera_watch` • `camera_stream` • `screen_capture` • `screen_stream`

### 🔓 Offensive Security
`hack_website` • `hack_full` • `hack_deep` • `scan_ports` • `scan_sqli` • `scan_xss` • `scan_lfi` • `scan_cmdi` • `scan_ssrf` • `scan_ssti` • `scan_xxe` • `scan_cors` • `subdomain_enum` • `dir_bruteforce` • `detect_waf` • `scan_sensitive_files` • `full_recon` • `crack_hash` • `jwt_crack` • `generate_webshell` • `generate_reverse_shell` • `brute_force_login`

### 🔑 Auth Bypass Suite
`auth_totp_bypass` • `auth_session_hijack` • `auth_jwt_bypass` • `auth_mfa_bypass` • `auth_oauth_bypass` • `auth_headers_bypass` • `auth_credential_stuffing` • `auth_saml_bypass` • `auth_ldap_bypass` • `auth_sql_injection_bypass` • `auth_password_reset_bypass` • `auth_api_key_bypass` • `auth_captcha_bypass` • `auth_cloud_bypass` • `auth_otp_bypass` • `auth_basic_brute` • `auth_cookie_bypass` • `auth_biometric_bypass` • `auth_oauth_bypass_v2` • `auth_bypass_master`

### 🏢 Active Directory
`ad_exploit` • Kerberoasting • DCSync • ADCS (ESC1-13) • Golden/Silver Tickets • ACL abuse • Shadow Credentials • AS-REP Roasting • Pass-the-Hash

### ☁️ Cloud Exploitation
`cloud_exploit` — AWS (IMDS, S3, IAM, Lambda, KMS) • Azure (IMDS, KeyVault, RBAC, Managed Identity) • GCP (metadata, Cloud Storage, IAM, Cloud Functions)

### 🎯 Post-Exploitation
`post_exploit` • `container_escape` • `pivot_network` • `wireless_exploit` • `social_engineer` • `ics_scada_exploit` • `supply_chain_attack`

### 🧬 Evolution Engine
`evolve` • `evolution_status` • `evolution_knowledge` • `reset_evolution` • `evolve` = self-modifying AI that creates new tools autonomously

### 🛡️ Defense
`cyber_defense` • `start_monitor` • `stop_monitor` • `monitor_status` • `system_status` • `system_monitor_dash` • `local_audit`

### 🔧 Development
`git` • `code_format` • `run_linter` • `detect_dead_code` • `detect_code_duplicates` • `review_code` • `review_code_changes` • `run_ci_pipeline` • `build_code_index` • `search_symbol` • `build_call_graph` • `generate_project` • `create_test_suite` • `run_tests` • `bump_version` • `generate_changelog` • `rename_symbol` • `extract_function` • `split_file`

### 🤖 Automation
`auto_rule` • `standing_orders` • `tasks` • `schedule_omega` • `smart_reminder` • `register_hook` • `spawn_sub_agent` • `start_mission` • `background_task`

### 📱 Phone Control
`phone_control` — SMS/Telegram/Pushbullet/AutoRemote • `adb_phone` — USB control: screen, SMS, apps, files

### ⚡ Power & Misc
`power` (shutdown/restart/sleep) • `speak` (TTS) • `listen` (mic recording) • `transcribe` (speech-to-text) • `notify` (toast alerts) • `clipboard` • `encrypt_file` • `decrypt_file` • `image_tool` • `pdf_read` • `docker` • `registry` • `windows_service` • `user_account` • `cleanup` • `backup_omega` • `upgrade_omega` • `install_service` • `uninstall_service` • `self_improve` • `self_diagnose` • `personal_briefing`

---

## 🌐 Web Server Mode

Turn any PC into a remote-controlled OMEGA server:

```bash
# Start the server
python omega_server.py

# Or use the launcher
.\Start-OmegaWeb.bat
```

Then open **http://localhost:8080** in any browser — control OMEGA from your phone, tablet, or another laptop.

---

## 🤖 Dual-Agent Team Mode

Launch two OMEGA agents that work together:

```bash
python main.py --team
# Or
omega-team.bat
```

**OMEGA-1** (Architect) plans strategy • **OMEGA-2** (Executor) implements

---

## 🔄 Self-Updating & Backups

```bash
# Full self-backup (entire OMEGA + memories → ZIP)
python -c "from tools import backup_omega; print(backup_omega().content)"

# Self-diagnosis
python main.py --diagnose

# Self-improvement scan
python -c "from tools import agent_self_optimize; agent_self_optimize('full')"
```

---

## 📜 License

MIT — Use freely, modify boldly, share openly.

---

> **Made with ☕ and 🧠 by [xmanya26911-bit](https://github.com/xmanya26911-bit)**
> 
> _OMEGA is watching. OMEGA is ready._
