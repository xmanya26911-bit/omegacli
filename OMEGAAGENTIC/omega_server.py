#!/usr/bin/env python3
"""OMEGA Remote Web Server — Control this PC from any browser"""
import http.server
import json
import subprocess
import urllib.parse
import sys
import os
import io
import base64

# Set UTF-8 for subprocess encoding only
os.environ["PYTHONIOENCODING"] = "utf-8"

HOST = "0.0.0.0"
PORT = 8080

class OmegaHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        
        if path == "" or path == "/index.html":
            self.send_html(INDEX_HTML)
        elif path == "/api/exec":
            cmd = urllib.parse.parse_qs(parsed.query).get("cmd", [""])[0]
            if cmd:
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", cmd],
                        capture_output=True, timeout=30,
                        cwd="D:\\TERMINALCLI\\omega"
                    )
                    stdout = result.stdout.decode('utf-8', errors='replace')
                    stderr = result.stderr.decode('utf-8', errors='replace')
                    self.send_json({
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": result.returncode
                    })
                except subprocess.TimeoutExpired:
                    self.send_json({"error": "Command timed out"}, status=408)
                except Exception as e:
                    self.send_json({"error": str(e)}, status=500)
            else:
                self.send_json({"error": "No cmd parameter"})
        elif path == "/api/ps":
            r = subprocess.run(["powershell", "Get-Process | Select-Object Name,Id,CPU,PM | ConvertTo-Json"],
                             capture_output=True, timeout=10)
            self.send_json({"processes": r.stdout.decode('utf-8', errors='replace')})
        elif path == "/api/info":
            self.send_json({
                "hostname": "MAXXEN",
                "os": "Windows 10",
                "ip": "192.168.1.3",
                "ssh": "pc@192.168.1.3"
            })
        elif path == "/api/disk":
            r = subprocess.run(["powershell", "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | ConvertTo-Json"],
                             capture_output=True, timeout=10)
            self.send_json({"disks": r.stdout.decode('utf-8', errors='replace')})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError:
            body = raw.decode("utf-8", errors="replace")
        data = json.loads(body) if body else {}
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/api/exec":
            cmd = data.get("cmd", "")
            if cmd:
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", cmd],
                        capture_output=True, timeout=30,
                        cwd="D:\\TERMINALCLI\\omega"
                    )
                    stdout = result.stdout.decode('utf-8', errors='replace')
                    stderr = result.stderr.decode('utf-8', errors='replace')
                    self.send_json({
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": result.returncode
                    })
                except subprocess.TimeoutExpired:
                    self.send_json({"error": "Command timed out"}, status=408)
                except Exception as e:
                    self.send_json({"error": str(e)}, status=500)
            else:
                self.send_json({"error": "No cmd"})
        else:
            self.send_error(404)

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        payload = json.dumps(data, ensure_ascii=False)
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[OMEGA WEB] {args[0]} {args[1]} {args[2]}")

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>? OMEGA Remote Control</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',system-ui,sans-serif; background:#0a0e17; color:#e0e0e0; height:100vh; display:flex; flex-direction:column; }
.header { background:linear-gradient(135deg,#00d4ff,#0066ff); padding:16px 24px; display:flex; align-items:center; gap:14px; }
.header h1 { font-size:22px; font-weight:700; color:#fff; letter-spacing:1px; }
.header span { font-size:13px; opacity:.8; color:#fff; }
.container { display:flex; flex:1; overflow:hidden; }
.sidebar { width:220px; background:#111827; padding:16px; border-right:1px solid #1e293b; display:flex; flex-direction:column; gap:8px; }
.sidebar button { background:#1e293b; color:#cbd5e1; border:1px solid #334155; padding:10px 14px; border-radius:8px; cursor:pointer; text-align:left; font-size:13px; transition:all .2s; }
.sidebar button:hover { background:#334155; border-color:#00d4ff; color:#fff; }
.sidebar button.active { background:#1e3a5f; border-color:#00d4ff; color:#00d4ff; }
.main { flex:1; display:flex; flex-direction:column; }
.toolbar { background:#111827; padding:12px 16px; border-bottom:1px solid #1e293b; display:flex; gap:10px; align-items:center; }
.toolbar input { flex:1; background:#0f172a; border:1px solid #334155; color:#e0e0e0; padding:8px 12px; border-radius:6px; font-size:13px; font-family:monospace; }
.toolbar input:focus { outline:none; border-color:#00d4ff; }
.toolbar button { background:linear-gradient(135deg,#00d4ff,#0066ff); color:#fff; border:none; padding:8px 20px; border-radius:6px; cursor:pointer; font-weight:600; font-size:13px; }
.toolbar button:hover { opacity:.9; }
.output { flex:1; background:#0a0e17; padding:16px; overflow-y:auto; font-family:'Cascadia Code','Fira Code',monospace; font-size:13px; line-height:1.6; white-space:pre-wrap; }
.output .prompt { color:#00d4ff; }
.output .stdout { color:#e0e0e0; }
.output .stderr { color:#ff6b6b; }
.output .error { color:#ff6b6b; }
.output .system { color:#94a3b8; font-style:italic; }
.statusbar { background:#111827; padding:8px 16px; border-top:1px solid #1e293b; font-size:12px; color:#64748b; display:flex; justify-content:space-between; }
.statusbar .dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.statusbar .dot.green { background:#22c55e; }
.statusbar .dot.blue { background:#00d4ff; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
.loading { animation:pulse 1s infinite; color:#00d4ff; }
</style>
</head>
<body>
<div class="header">
<h1>? OMEGA</h1>
<span>Remote Control — MAXXEN (192.168.1.3)</span>
</div>
<div class="container">
<div class="sidebar">
<button class="active" onclick="openTab('terminal')">? Terminal</button>
<button onclick="openTab('quick')">? Quick Commands</button>
<button onclick="openTab('files')">? File Browser</button>
<button onclick="openTab('system')">? System Info</button>
<button onclick="openTab('about')">? About</button>
</div>
<div class="main">
<div class="toolbar" id="toolbar">
<input id="cmdInput" placeholder="Enter PowerShell command..." onkeydown="if(event.key==='Enter') runCmd()"/>
<button onclick="runCmd()">▶ Run</button>
</div>
<div class="output" id="output">
<span class="system">? OMEGA Web Control — Connected to MAXXEN</span>
<span class="system">? SSH: pc@192.168.1.3</span>
<span class="system">? Type a command and hit Enter, or click Quick Commands</span>
</div>
<div class="statusbar">
<span><span class="dot green"></span>Live — MAXXEN</span>
<span id="statusText">Ready</span>
</div>
</div>
</div>
<script>
let tab = 'terminal';

function openTab(t) {
    tab = t;
    document.querySelectorAll('.sidebar button').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    const output = document.getElementById('output');
    const toolbar = document.getElementById('toolbar');
    
    if (t === 'terminal') {
        toolbar.style.display = 'flex';
        output.innerHTML = '<span class="system">? Terminal mode — type any PowerShell command</span>';
    } else if (t === 'quick') {
        toolbar.style.display = 'none';
        output.innerHTML = `
<span class="system">? Quick Commands</span>
<span class="system">Click any button below:</span>
<br>
<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
<button onclick="quickCmd('Get-Process | Sort-Object CPU -Desc | Select Name,Id,CPU -First 10 | Format-Table -AutoSize')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Top CPU Processes</button>
<button onclick="quickCmd('Get-PSDrive -PSProvider FileSystem | Select Name,@{N=\\"Used(GB)\\" ;E={[math]::Round($_.Used/1GB,1)}},@{N=\\"Free(GB)\\" ;E={[math]::Round($_.Free/1GB,1)}} | Format-Table -AutoSize')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Disk Usage</button>
<button onclick="quickCmd('ipconfig')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Network Info</button>
<button onclick="quickCmd('systeminfo | Select-String \"OS Name\",\"OS Version\",\"System Boot Time\",\"Total Physical Memory\"')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? System Info</button>
<button onclick="quickCmd('netstat -an | Select-String LISTEN')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Listening Ports</button>
<button onclick="quickCmd('Get-Service | Where Status -eq Running | Format-Table Name,DisplayName,StartType -AutoSize')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Running Services</button>
<button onclick="quickCmd('Get-WmiObject Win32_LogicalDisk -Filter DriveType=3 | Select DeviceID,@{N=\\"Free(GB)\\" ;E={[math]::Round($_.FreeSpace/1GB,1)}},@{N=\\"Total(GB)\\" ;E={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? Free Disk Space</button>
<button onclick="quickCmd('Get-ChildItem D:\\TERMINALCLI\\omega -Name | Format-List')" style="background:#1e293b;color:#fff;border:1px solid #334155;padding:8px 14px;border-radius:6px;cursor:pointer">? List OMEGA Files</button>
</div>`;
    } else if (t === 'files') {
        toolbar.style.display = 'flex';
        document.getElementById('cmdInput').value = 'Get-ChildItem D:\\TERMINALCLI\\omega -Name';
        output.innerHTML = '<span class="system">? File Browser — use commands to navigate. Try:</span><br><span class="system">• Get-ChildItem D:\\ -Name</span><br><span class="system">• Get-ChildItem D:\\TERMINALCLI -Recurse -Directory | Select FullName</span>';
    } else if (t === 'system') {
        toolbar.style.display = 'none';
        fetch('/api/info').then(r=>r.json()).then(d=>{
            let html = '<span class="system">? System Information</span><br>';
            for (let [k,v] of Object.entries(d)) html += `<span class="stdout"><b>${k}:</b> ${v}</span>`;
            document.getElementById('output').innerHTML = html;
        });
    } else if (t === 'about') {
        toolbar.style.display = 'none';
        output.innerHTML = `
<span class="system">? OMEGA Remote Control</span>
<span class="system">? Full control of MAXXEN from any browser</span>
<span class="system">? SSH access: ssh pc@192.168.1.3</span>
<span class="system">? RDP: Run \`Enable-RDP.bat\` for desktop access</span>
<span class="system">? OMEGA is always online and watching</span>
<br>
<span class="system">? Need help? Just ask OMEGA!</span>`;
    }
}

function quickCmd(cmd) {
    document.getElementById('cmdInput').value = cmd;
    runCmd();
}

function runCmd() {
    const input = document.getElementById('cmdInput');
    const output = document.getElementById('output');
    const cmd = input.value.trim();
    if (!cmd) return;
    
    output.innerHTML += `\\n<span class="prompt">PS MAXXEN> </span><span class="stdout">${escapeHtml(cmd)}</span>\\n`;
    document.getElementById('statusText').innerHTML = '<span class="loading">Running...</span>';
    input.disabled = true;
    
    fetch('/api/exec', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({cmd: cmd})
    })
    .then(r => r.json())
    .then(d => {
        if (d.stdout) output.innerHTML += `<span class="stdout">${escapeHtml(d.stdout)}</span>\\n`;
        if (d.stderr) output.innerHTML += `<span class="stderr">${escapeHtml(d.stderr)}</span>\\n`;
        if (d.exit_code === 0) {
            output.innerHTML += `<span class="system">? Exit code: 0 (success)</span>\\n`;
        } else if (d.exit_code) {
            output.innerHTML += `<span class="error">? Exit code: ${d.exit_code}</span>\\n`;
        }
        if (d.error) output.innerHTML += `<span class="error">? Error: ${escapeHtml(d.error)}</span>\\n`;
        document.getElementById('statusText').textContent = 'Ready';
        input.disabled = false;
        input.focus();
        output.scrollTop = output.scrollHeight;
    })
    .catch(e => {
        output.innerHTML += `<span class="error">? Network error: ${e}</span>\\n`;
        document.getElementById('statusText').textContent = 'Error';
        input.disabled = false;
    });
}

function escapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print(f"""
?  OMEGA Remote Web Server
?  ========================
?  Server: http://{HOST}:{PORT}
?  LAN:    http://192.168.1.3:{PORT}
?  SSH:    ssh pc@192.168.1.3
?  
?  Press Ctrl+C to stop
""")
    server = http.server.HTTPServer((HOST, PORT), OmegaHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n? Server stopped")
        server.server_close()
