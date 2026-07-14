# OMEGA Bridge -> Claude Code CLI
# Bridges OMEGA to the REAL Claude Code binary
# Installed by OMEGA Claude Bridge on 2026-07-10 17:51:39

$claudeBinary = "C:\Users\pc\.local\bin\claude.exe"

if (-not (Test-Path $claudeBinary)) {
    Write-Error "Claude Code binary not found at: $claudeBinary"
    exit 1
}

& $claudeBinary @args
