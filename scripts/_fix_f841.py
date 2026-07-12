"""Clean up F841 unused variables in tools.py"""
with open('tools.py', 'r') as f:
    content = f.read()

# Issue 1: max_size, old_size in batch_write (lines ~466, 478)
content = content.replace(
    '        total_size = 0\n        max_size = 50*1024*1024  # 50MB',
    '        total_size = 0'
)
# Remove old_size line
content = content.replace(
    "            existed = path_obj.exists()\n            old_size = path_obj.stat().st_size if existed else 0\n\n            if len(content)",
    "            existed = path_obj.exists()\n\n            if len(content)"
)
# total_size is incremented but never used after - remove the counter
content = content.replace(
    '            total_size += len(content)\n\n            path_obj.write_text(content, encoding="utf-8")',
    '            path_obj.write_text(content, encoding="utf-8")'
)

# Issue 2: total_size in download tool (line 825)
content = content.replace(
    '        total_size = int(resp.headers.get("content-length", 0))\n        downloaded = 0\n        chunk_count = 0',
    '        downloaded = 0\n        chunk_count = 0'
)

# Issue 3: formatted in file processing tool (line 3322)
content = content.replace(
    '                formatted = True\n            else:\n                formatted = False\n\n        with open(path, encoding="utf-8")',
    '                pass\n            else:\n                pass\n\n        with open(path, encoding="utf-8")'
)

# Issue 4: pip_result in plugin loading (line 3414)
content = content.replace(
    '            pip_result = _sp.run([sys.executable, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True, timeout=180)',
    '            _sp.run([sys.executable, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True, timeout=180)'
)

# Issue 5: before in temp cleanup (line 3579)
content = content.replace(
    '            before = sum(_os.path.getsize(_os.path.join(dp, f)) for dp, dn, fn in _os.walk(tp) for f in fn) if _os.path.exists(tp) else 0\n            results.append(f"  Temp ({tp}): scanned")',
    '            results.append(f"  Temp ({tp}): scanned")'
)

# Issue 6: clean in temp cleanup (line 3582)
content = content.replace(
    '    clean = _sp.run(["powershell", "-Command", "Get-ChildItem -Path $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"], capture_output=True, timeout=30)',
    '    _sp.run(["powershell", "-Command", "Get-ChildItem -Path $env:TEMP -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"], capture_output=True, timeout=30)'
)

# Issue 7: log_entry in monitor (line 3784)
content = content.replace(
    '                    log_entry = f"[{ts}] CPU:{cpu}% RAM:{mem}% DISK:{disk}%"\n                    # Check thresholds',
    '                    # Check thresholds'
)

# Issue 8: sender_name in team messaging (line 6689)
content = content.replace(
    "    sender_name = _team_get_role(sender)\n    recipient_name = _team_get_role(recipient)",
    "    recipient_name = _team_get_role(recipient)"
)

with open('tools.py', 'w') as f:
    f.write(content)
print('Done — cleaned 9 F841 issues')
