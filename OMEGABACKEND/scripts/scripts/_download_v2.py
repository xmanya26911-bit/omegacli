"""Download Claude Code v2.0.0 which has raw JS source."""
import requests
import tarfile
import io
import os
import json

OUTPUT_DIR = "D:\\TERMINALCLI\\omega\\claude-code-v2.0.0"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get tarball URL for v2.0.0
r = requests.get("https://registry.npmjs.org/@anthropic-ai/claude-code", timeout=15)
data = r.json()

tarball_url = data["versions"]["2.0.0"]["dist"]["tarball"]
print(f"Downloading v2.0.0 from: {tarball_url}")

r = requests.get(tarball_url, timeout=120)
r.raise_for_status()
print(f"Downloaded {len(r.content):,} bytes")

tar = tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz")
members = tar.getmembers()
print(f"Extracting {len(members)} files...")

try:
    tar.extractall(path=OUTPUT_DIR, filter='data')
except TypeError:
    tar.extractall(path=OUTPUT_DIR)
tar.close()

# List all files
all_files = []
for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, OUTPUT_DIR)
        size = os.path.getsize(full)
        all_files.append((rel, size))

all_files.sort(key=lambda x: -x[1])
print(f"\nAll files ({len(all_files)}):")
for rel, size in all_files:
    print(f"  {size:>10,} B  {rel}")

# Show package.json
pkg_path = os.path.join(OUTPUT_DIR, "package", "package.json")
if os.path.exists(pkg_path):
    with open(pkg_path) as f:
        pkg = json.load(f)
    print(f"\nPackage.json:")
    print(f"  Name: {pkg.get('name')}")
    print(f"  Version: {pkg.get('version')}")
    print(f"  Type: {pkg.get('type')}")
    print(f"  Main: {pkg.get('main')}")
    print(f"  Exports: {json.dumps(pkg.get('exports', {}), indent=4)[:500]}")
    print(f"  Bin: {json.dumps(pkg.get('bin', {}), indent=4)}")
