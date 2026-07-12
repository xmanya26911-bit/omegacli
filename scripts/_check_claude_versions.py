"""Try to find the raw JS source of Claude Code from npm archives."""
import requests
import json
import os

# Check the package metadata for repository info
r = requests.get("https://registry.npmjs.org/@anthropic-ai/claude-code", timeout=15)
data = r.json()

latest_ver = data.get("dist-tags", {}).get("latest", "")
print(f"Latest: {latest_ver}")

# Check repository field
for ver_name in ["2.1.206", "2.1.200", "2.0.0", "1.0.0"]:
    if ver_name in data.get("versions", {}):
        ver_data = data["versions"][ver_name]
        repo = ver_data.get("repository", {})
        print(f"\n{ver_name}:")
        print(f"  Repository: {json.dumps(repo)}")
        print(f"  Has dist: {'dist' in ver_data.get('dist', {})}")
        print(f"  Tarball size: {ver_data.get('dist', {}).get('fileCount', '?')} files")
        
        # Check if the tarball might have JS source
        tarball = ver_data.get("dist", {}).get("tarball", "")
        if tarball:
            # Quick HEAD request to check size
            h = requests.head(tarball, timeout=10)
            print(f"  Package size: {h.headers.get('content-length', '?')} bytes")
        
        # Check if main/module fields point to JS
        main = ver_data.get("main", "")
        module = ver_data.get("module", "")
        typings = ver_data.get("typings", "")
        exports = ver_data.get("exports", "")
        print(f"  main: {main}")
        print(f"  module: {module}")
        print(f"  typings: {typings}")
        if exports:
            print(f"  exports keys: {list(exports.keys()) if isinstance(exports, dict) else exports}")

# Also check for a separate source package
print("\n\nChecking for source package...")
r2 = requests.get("https://registry.npmjs.org/@anthropic-ai/claude-code-source", timeout=15)
if r2.status_code == 200:
    print("FOUND: @anthropic-ai/claude-code-source")
else:
    print(f"Not found: {r2.status_code}")
    
# Check the GitHub releases approach
print(f"\n\nGitHub releases info:")
# The anthropics/claude-code repo has releases
print("https://github.com/anthropics/claude-code/releases")

# Check version history
versions = sorted(data.get("versions", {}).keys(), key=lambda v: [int(x) for x in v.split('.')])
print(f"\nAll versions ({len(versions)}):")
for v in versions[-20:]:
    ver_data = data["versions"][v]
    tarball_url = ver_data.get("dist", {}).get("tarball", "")
    file_count = ver_data.get("dist", {}).get("fileCount", "?")
    # Get first few files
    print(f"  {v}: {file_count} files")
