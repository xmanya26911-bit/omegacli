"""Download the @anthropic-ai/claude-code npm package and extract its source."""
import requests
import json
import tarfile
import io
import os
import sys
import traceback

OUTPUT_DIR = "D:\\TERMINALCLI\\omega\\claude-code-npm-source"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get the latest version info
print("Looking up package info...")
r = requests.get("https://registry.npmjs.org/@anthropic-ai/claude-code", timeout=30)
data = r.json()

# Get latest version
latest = data.get("dist-tags", {}).get("latest", "")
if not latest:
    versions = list(data.get("versions", {}).keys())
    latest = versions[-1]
print(f"Latest version: {latest}")

# Get tarball URL
tarball_url = data.get("versions", {}).get(latest, {}).get("dist", {}).get("tarball", "")
if not tarball_url:
    print("ERROR: Could not find tarball URL")
    sys.exit(1)

print(f"Tarball URL: {tarball_url}")
print(f"Downloading... (this may take a while)")

# Download tarball
print(f"Downloading from {tarball_url}...")
r = requests.get(tarball_url, timeout=300)
r.raise_for_status()
print(f"Downloaded {len(r.content):,} bytes")

tar_bytes = io.BytesIO(r.content)
tar = tarfile.open(fileobj=tar_bytes, mode="r:gz")

members = tar.getmembers()
print(f"Extracting {len(members)} files...")
try:
    tar.extractall(path=OUTPUT_DIR, filter='data')
except TypeError:
    tar.extractall(path=OUTPUT_DIR)
tar.close()

# List what we got
js_files = []
for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        if f.endswith('.js') or f.endswith('.ts') or f.endswith('.json'):
            full = os.path.join(root, f)
            rel = os.path.relpath(full, OUTPUT_DIR)
            size = os.path.getsize(full)
            js_files.append((rel, size))

print(f"\nExtracted {len(js_files)} JS/TS/JSON files:")
js_files.sort(key=lambda x: -x[1])
for rel, size in js_files[:40]:
    print(f"  {size:>10,} B  {rel}")

if len(js_files) > 40:
    print(f"  ... and {len(js_files) - 40} more")

print(f"\nTotal files extracted to: {OUTPUT_DIR}")
print(f"Package version: {latest}")
