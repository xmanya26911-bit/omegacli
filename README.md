# OMEGA CLI

**OMEGA** — Professional Engineering Assistant. An autonomous AI CLI agent with tool execution, memory, web access, and multi-model support.

## Quick Start

```bash
git clone https://github.com/xmanya26911-bit/omegacli.git
cd omegacli
pip install -r requirements.txt
python main.py
```

## Requirements

- Python 3.10+
- Windows (primary) or Linux/macOS (partial)
- An API key from [OpenCode Zen](https://opencode-zen.com) or compatible OpenAI provider

## Usage

```bash
# Interactive session
python main.py

# Single command
python main.py "list all files in current directory"

# With specific model
python main.py --model deepseek-v4-flash-free

# Run diagnostics
python main.py --diagnose
```

## Features

- 💬 Interactive CLI with rich TUI (themes, welcome, command history)
- 🛠️ 150+ built-in tools (file operations, web, code, system, git, SQL)
- 🧠 Long-term memory (persistent across sessions)
- 🔍 Web search and fetch with caching
- 🐍 Python REPL for complex computation
- 🐙 Git integration
- 🖼️ Image processing
- 🔐 File encryption
- 🌐 REST API client
- 📦 Auto-pip-install
- 🔄 Background task execution

## Models

| Model | Status |
|---|---|
| `deepseek-v4-flash-free` | ✅ Free |
| `mimo-v2.5-free` | ✅ Free |
| `hy3-free` | ✅ Free |
| `nemotron-3-ultra-free` | ✅ Free |
| `north-mini-code-free` | ✅ Free |

## Configuration

API keys are configured via the interactive setup:

```bash
python main.py --configure
```

Or by setting environment variables directly in code.

## Project Structure

```
omega/
├── main.py              Entry point
├── omega/
│   ├── core/            Config, events, bus
│   ├── tools/           Tool implementations
│   ├── ui/              Terminal UI (themes, commands, messages)
│   ├── prompts/         System prompts
│   ├── schemas/         Tool definitions
│   └── tests/           Unit tests
├── OMEGABACKEND/core/   Legacy backend (agent, cli, config, llm, memory)
├── requirements.txt
└── README.md
```

## License

MIT
