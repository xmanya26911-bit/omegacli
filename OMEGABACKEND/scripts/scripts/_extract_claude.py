"""
Extract the embedded JavaScript source from Claude Code's pkg-compiled binary.
pkg stores the application bundle as a JSON header + gzipped tar after a magic marker.
"""

import struct
import sys
import os
import json
import gzip
import tarfile
import io

BINARY_PATH = "C:\\Users\\pc\\.local\\bin\\claude-core.exe"
OUTPUT_DIR = "D:\\TERMINALCLI\\omega\\claude-code-source"

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(BINARY_PATH, "rb") as f:
    data = f.read()

print(f"Binary size: {len(data):,} bytes ({len(data)/1024/1024:.1f} MB)")

# pkg stores its payload after a specific marker.
# Common markers: 'PAYLOAD', '\x00\x00\x00\x00package.json', '<project>'
# Let's search for JSON-like structure indicating the start of the bundle

# Search for known pkg markers
markers = [b"PAYLOAD", b"package.json", b"//"]

for marker in markers:
    pos = data.find(marker)
    if pos >= 0:
        print(f"  Found '{marker.decode('ascii', errors='replace')}' at offset 0x{pos:x} ({pos:,})")

# Search for "claude" string to find the JS start
# In pkg, the bundle starts with a JSON stats header
# Let's search for the start of a JSON object followed by node_modules references

# Look for the start of the bundle - it typically starts with a JSON header
# and then contains the base64-encoded or gzipped filesystem

# Search for a known JS pattern in the binary
search_terms = [b"require(", b"module.exports", b"__dirname", b"process.argv"]
for term in search_terms:
    pos = data.find(term)
    if pos >= 0:
        print(f"  JS code starts around offset 0x{pos:x} ({pos:,})")

# Try to find the pkg bundlestrap
# In pkg, the bootstrap code contains specific patterns
# Let's look for the string 'pkg' or 'PKG' or the bootstrap JS

# Look for the PAYLOAD: string that pkg uses
idx = data.find(b"PAYLOAD")
if idx >= 0:
    print(f"\nPAYLOAD marker at 0x{idx:x}")
    # After PAYLOAD, there's typically a JSON header with the file list
    # followed by the actual content
    header_end = data.find(b"\x00\x00\x00\x00", idx)
    if header_end >= 0:
        payload_data = data[idx:header_end+4]
        print(f"  PAYLOAD data: {payload_data[:200]!r}")

# Alternative: Search for string "claude-code" or "@anthropic-ai"
for term in [b"@anthropic-ai", b"claude", b"claude-code"]:
    idx = data.find(term)
    if idx >= 0:
        print(f"\n  Found '{term.decode('ascii', errors='replace')}' at 0x{idx:x}")
        # Show context
        context = data[max(0,idx-50):idx+200]
        print(f"  Context: {context[:250]!r}")

# Try to find the pkg Snapshot blob
# pkg uses a specific format: a header with entry count, then entries
# Looking for the pattern where a JS source file is stored

# Search for common file paths
for path_term in [b"/dist/", b"/src/", b"index.js", b"cli.js", b"main.js"]:
    idx = data.find(path_term)
    if idx >= 0:
        print(f"\n  File path '{path_term.decode('ascii', errors='replace')}' at 0x{idx:x}")
        context = data[max(0,idx-10):idx+120]
        print(f"  Context: {context[:200]!r}")

print("\n--- Sample string search ---")
# Look for any readable JS strings near the end of the binary
# (pkg typically puts the bundle at the end)
for offset in range(0, len(data) - 100, 1000000):
    chunk = data[offset:offset+100]
    if b"require" in chunk or b"module" in chunk:
        print(f"  JS-like at {offset:,}: {chunk[:120]!r}")
        break
