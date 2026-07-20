# Ω OMEGA Desktop

Native desktop application for OMEGA AI — built with Tauri v2.

## Prerequisites

- Rust 1.70+ (via rustup.rs)
- Node.js 18+
- WebView2 (pre-installed on Windows 10+)

## Quick Start

```bash
# Start in dev mode (opens chat app in native window)
cd apps/desktop
npm install
npx tauri dev

# Build for production
npx tauri build --ci
# Installer at: src-tauri/target/release/bundle/nsis/
```

## Features

- **Native window** — No browser chrome, dedicated Omega window
- **System tray** — Minimize to tray with context menu
- **Native notifications** — OS-level notification support
- **File system access** — Drag & drop file uploads with native dialog
- **Offline splash** — Shows loading screen while connecting
- **Auto-updates** — (planned) Tauri updater integration

## Configuration

Edit `src-tauri/tauri.conf.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `app.windows[0].title` | "Ω OMEGA" | Window title |
| `app.windows[0].width` | 1200 | Default width |
| `app.windows[0].height` | 800 | Default height |
| `build.devUrl` | https://omega-chat-five.vercel.app | URL to load |

## Plugins

| Plugin | Purpose |
|--------|---------|
| `tauri-plugin-shell` | Open external URLs |
| `tauri-plugin-notification` | Native push notifications |
| `tauri-plugin-fs` | File system access |
| `tauri-plugin-dialog` | File open/save dialogs |
| `tauri-plugin-process` | Process management |

## Project Structure

```
apps/desktop/
├── package.json          # Frontend deps + scripts
├── public/
│   └── index.html        # Splash screen
└── src-tauri/
    ├── Cargo.toml        # Rust deps
    ├── tauri.conf.json   # Tauri configuration
    ├── build.rs          # Build script
    └── src/
        ├── main.rs       # Entry point
        └── lib.rs        # App setup + plugins
```

## Building Installer

```bash
npx tauri build --ci
# Output: src-tauri/target/release/bundle/nsis/Omega_1.5.0_x64-setup.exe
```
