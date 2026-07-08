#!/usr/bin/env python3
"""Ω OMEGA Desktop App — Full desktop application with web UI, MCP, and 200+ tools.
   Launches a local HTTP server + optional native PyWebView window.
   Usage: python omega_desktop.py [--port PORT] [--native] [--no-browser]
"""

import os, sys, json, time, threading, io, base64, urllib.parse, uuid, queue, re, socket, signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ─── OMEGA Core Path ────────────────────────────────────────────
OMEGA_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(OMEGA_DIR))

# Attempt to load OMEGA core modules
try:
    from agent import Agent
    from config import Config, AVAILABLE_MODELS
    from tools import execute_tool, TOOL_MAP
    from prompts import TOOL_DEFINITIONS
    from memory import get_persistent_memory, save_memory, search_memories, list_memories
    from memory import save_note as memory_save_note, read_note as memory_read_note, list_notes, delete_note
    from cli import format_size
    OMEGA_CORE = True
except Exception as e:
    OMEGA_CORE = False
    print(f"[OMEGA DESKTOP] Warning: Could not load OMEGA core: {e}")

# ─── Global State ────────────────────────────────────────────────
CLIENTS = {}  # session_id -> {"agent": Agent, "messages": [], "created": time}
AGENT_SESSIONS = {}
DEFAULT_PORT = 3000
VERSION = "1.0.0"

def get_or_create_agent(session_id=None):
    """Get or create an OMEGA agent session."""
    if session_id and session_id in AGENT_SESSIONS:
        return AGENT_SESSIONS[session_id]
    if not OMEGA_CORE:
        return None
    try:
        config = Config()
        agent = Agent(config)
        session_id = session_id or str(uuid.uuid4())
        AGENT_SESSIONS[session_id] = agent
        return agent
    except Exception as e:
        return None

# ─── HTTP Handler ────────────────────────────────────────────────
class OmegaDesktopHandler(BaseHTTPRequestHandler):
    """HTTP Server with REST API + SSE streaming + file serving."""
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query)
        
        try:
            # ─── Serve UI ─────────────────────────────────────────
            if path == "/":
                self.send_html(INDEX_HTML)
            elif path == "/api/status":
                self.send_json(self._get_status())
            elif path == "/api/system":
                self.send_json(self._get_system_info())
            elif path == "/api/tools":
                self.send_json(self._get_tools())
            elif path == "/api/models":
                self.send_json({"models": AVAILABLE_MODELS if OMEGA_CORE else []})
            elif path == "/api/memories":
                self.send_json(self._list_memories())
            elif path == "/api/notes":
                self.send_json(self._list_notes())
            elif path == "/api/mcp/status":
                self.send_json({"mcp": self._mcp_status()})
            elif path == "/api/processes":
                self.send_json(self._get_processes())
            elif path == "/api/disks":
                self.send_json(self._get_disks())
            elif path.startswith("/api/read/"):
                fpath = path[len("/api/read/"):]
                self._handle_read_file(fpath)
            elif path.startswith("/api/glob/"):
                pattern = path[len("/api/glob/"):]
                self._handle_glob(pattern)
            elif path.startswith("/api/cwd/"):
                self._handle_list_dir(path[len("/api/cwd/"):])
            elif path == "/api/chat/stream":
                self._handle_chat_sse(query)
            elif path.startswith("/api/note/"):
                note_title = path[len("/api/note/"):]
                self._handle_get_note(note_title)
            elif path == "/api/diagnostics":
                self.send_json(self._run_diagnostics())
            else:
                self.send_error(404, f"Not Found: {path}")
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        
        try:
            body = raw.decode("utf-8", errors="replace")
            data = json.loads(body) if body.strip() else {}
        except Exception:
            data = {}
        
        try:
            if path == "/api/exec":
                self._handle_exec(data)
            elif path == "/api/chat":
                self._handle_chat(data)
            elif path == "/api/chat/stream":
                self._handle_chat_sse_stream(data)
            elif path == "/api/tool":
                self._handle_tool(data)
            elif path == "/api/memory/search":
                self._handle_memory_search(data)
            elif path == "/api/memory/save":
                self._handle_memory_save(data)
            elif path == "/api/memory/delete":
                self._handle_memory_delete(data)
            elif path == "/api/note/save":
                self._handle_note_save(data)
            elif path == "/api/note/delete":
                self._handle_note_delete(data)
            elif path == "/api/session/new":
                self._handle_new_session(data)
            elif path == "/api/mcp/connect":
                self._handle_mcp_connect(data)
            elif path == "/api/mcp/disconnect":
                self._handle_mcp_disconnect(data)
            elif path == "/api/write":
                self._handle_write_file(data)
            elif path == "/api/delete":
                self._handle_delete_file(data)
            elif path == "/api/tasks":
                self._handle_tasks(data)
            else:
                self.send_json({"error": f"Not Found: {path}"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    # ─── API Handlers ────────────────────────────────────────────
    
    def _get_status(self):
        info = {
            "version": VERSION,
            "omega_core": OMEGA_CORE,
            "tools_count": len(TOOL_DEFINITIONS) if OMEGA_CORE else 0,
            "sessions": len(AGENT_SESSIONS),
            "uptime": time.time() - _START_TIME,
            "hostname": socket.gethostname(),
            "platform": sys.platform,
            "python": sys.version,
        }
        if OMEGA_CORE:
            try:
                config = Config()
                info["model"] = config.model
                info["api_connected"] = True
            except:
                info["model"] = "unknown"
                info["api_connected"] = False
        return info
    
    def _get_system_info(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.3)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return {
                "cpu": cpu,
                "cpu_cores": psutil.cpu_count(),
                "ram_total": mem.total,
                "ram_used": mem.used,
                "ram_percent": mem.percent,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "disk_free": disk.free,
                "disk_percent": disk.percent,
                "boot_time": psutil.boot_time(),
            }
        except:
            return {"error": "psutil unavailable"}
    
    def _get_tools(self):
        tools = []
        if OMEGA_CORE:
            for name, info in TOOL_MAP.items():
                tools.append({
                    "name": name,
                    "description": (info.__doc__ or "").strip()[:200] if callable(info) else "",
                })
        return {"tools": sorted(tools, key=lambda x: x["name"]), "total": len(tools)}
    
    def _list_memories(self):
        if not OMEGA_CORE:
            return {"memories": []}
        try:
            mems = list_memories()
            return {"memories": [{"key": k, "value": v[:200] if isinstance(v, str) else str(v)[:200]} for k, v in mems.items()]}
        except:
            return {"memories": []}
    
    def _list_notes(self):
        if not OMEGA_CORE:
            return {"notes": []}
        try:
            notes = list_notes()
            return {"notes": [{"title": n.get("title", "?"), "tags": n.get("tags", []), "created": str(n.get("created", ""))[:19]} for n in notes]}
        except:
            return {"notes": []}
    
    def _mcp_status(self):
        return {"connected": False, "servers": []}
    
    def _get_processes(self):
        try:
            import psutil
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except:
                    pass
            return {"processes": sorted(procs, key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)[:50]}
        except:
            return {"processes": []}
    
    def _get_disks(self):
        try:
            import psutil
            disks = []
            for p in psutil.disk_partitions():
                try:
                    u = psutil.disk_usage(p.mountpoint)
                    disks.append({"device": p.device, "mount": p.mountpoint, "fstype": p.fstype,
                                  "total": u.total, "used": u.used, "free": u.free, "percent": u.percent})
                except:
                    pass
            return {"disks": disks}
        except:
            return {"disks": []}
    
    def _handle_read_file(self, fpath):
        try:
            from tools import read_file
            result = read_file(fpath)
            self.send_json({"content": result.content, "success": True})
        except Exception as e:
            self.send_json({"error": str(e), "success": False}, 500)
    
    def _handle_glob(self, pattern):
        try:
            from tools import glob as omega_glob
            result = omega_glob(pattern)
            self.send_json({"files": result.content, "success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def _handle_list_dir(self, path):
        try:
            path = urllib.parse.unquote(path) or "."
            from tools import list_dir
            result = list_dir(path)
            self.send_json({"content": result.content, "success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def _handle_get_note(self, title):
        try:
            title = urllib.parse.unquote(title)
            note = memory_read_note(title)
            self.send_json({"note": note, "success": True})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def _run_diagnostics(self):
        try:
            from tools import self_diagnose
            result = self_diagnose()
            return {"diagnostics": result.content}
        except:
            return {"diagnostics": "Could not run diagnostics"}
    
    def _handle_exec(self, data):
        import subprocess
        cmd = data.get("cmd", "")
        workdir = data.get("workdir", str(OMEGA_DIR))
        timeout = int(data.get("timeout", 30))
        if not cmd:
            self.send_json({"error": "No cmd"}, 400)
            return
        try:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, timeout=timeout, cwd=workdir
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            self.send_json({
                "stdout": stdout, "stderr": stderr,
                "exit_code": result.returncode, "success": result.returncode == 0
            })
        except subprocess.TimeoutExpired:
            self.send_json({"error": "Command timed out", "success": False})
        except Exception as e:
            self.send_json({"error": str(e), "success": False})
    
    def _handle_chat(self, data):
        message = data.get("message", "")
        session_id = data.get("session_id", "default")
        if not message:
            self.send_json({"error": "No message"}, 400)
            return
        agent = get_or_create_agent(session_id)
        if not agent:
            self.send_json({"error": "OMEGA core not loaded, cannot process chat", "success": False})
            return
        try:
            # Store message in session
            if session_id not in CLIENTS:
                CLIENTS[session_id] = {"messages": [], "created": time.time()}
            CLIENTS[session_id]["messages"].append({"role": "user", "content": message})
            
            # Run agent
            result = agent.run_once(message)
            CLIENTS[session_id]["messages"].append({"role": "assistant", "content": str(result)})
            self.send_json({"response": str(result), "success": True, "session_id": session_id})
        except Exception as e:
            self.send_json({"error": str(e), "success": False})
    
    def _handle_chat_sse(self, query):
        """SSE streaming endpoint for chat."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        message = query.get("message", [""])[0]
        if not message:
            self.wfile.write(f"data: {json.dumps({'error': 'No message'})}\n\n".encode())
            return
        
        session_id = query.get("session_id", ["default"])[0]
        agent = get_or_create_agent(session_id)
        if not agent:
            self.wfile.write(f"data: {json.dumps({'error': 'Agent unavailable'})}\n\n".encode())
            return
        
        try:
            if session_id not in CLIENTS:
                CLIENTS[session_id] = {"messages": [], "created": time.time()}
            CLIENTS[session_id]["messages"].append({"role": "user", "content": message})
            
            # For SSE, we run the agent and stream the thought process
            self.wfile.write(f"data: {json.dumps({'type': 'start', 'message': 'Processing...'})}\n\n".encode())
            self.wfile.flush()
            
            # Import necessary components for streaming
            from tools import execute_tool
            from prompts import TOOL_DEFINITIONS
            
            # Run the agent (simplified streaming)
            self.wfile.write(f"data: {json.dumps({'type': 'thinking', 'content': 'Analyzing request...'})}\n\n".encode())
            self.wfile.flush()
            
            # Full agent execution
            import io as stringio
            old_stdout = sys.stdout
            sys.stdout = stringio.StringIO()
            try:
                result = agent.run_once(message)
                captured = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            
            response_text = str(result)
            CLIENTS[session_id]["messages"].append({"role": "assistant", "content": response_text})
            
            # Send the response in chunks
            chunk_size = 200
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                self.wfile.write(f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.01)
            
            self.wfile.write(f"data: {json.dumps({'type': 'done'})}\n\n".encode())
            self.wfile.flush()
        except Exception as e:
            try:
                self.wfile.write(f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n".encode())
                self.wfile.flush()
            except:
                pass
    
    def _handle_chat_sse_stream(self, data):
        """POST-based SSE for streaming chat."""
        message = data.get("message", "")
        session_id = data.get("session_id", "default")
        if not message:
            self.send_json({"error": "No message"}, 400)
            return
        
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        agent = get_or_create_agent(session_id)
        if not agent:
            self.wfile.write(f"data: {json.dumps({'error': 'Agent unavailable'})}\n\n".encode())
            return
        
        try:
            if session_id not in CLIENTS:
                CLIENTS[session_id] = {"messages": [], "created": time.time()}
            CLIENTS[session_id]["messages"].append({"role": "user", "content": message})
            
            self.wfile.write(f"data: {json.dumps({'type': 'start'})}\n\n".encode())
            self.wfile.flush()
            
            result = agent.run_once(message)
            response_text = str(result)
            CLIENTS[session_id]["messages"].append({"role": "assistant", "content": response_text})
            
            # Stream response
            for i in range(0, len(response_text), 100):
                chunk = response_text[i:i+100]
                self.wfile.write(f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.005)
            
            self.wfile.write(f"data: {json.dumps({'type': 'done'})}\n\n".encode())
            self.wfile.flush()
        except Exception as e:
            try:
                self.wfile.write(f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n".encode())
                self.wfile.flush()
            except:
                pass
    
    def _handle_tool(self, data):
        tool_name = data.get("tool", "")
        params = data.get("params", {})
        if not tool_name or not OMEGA_CORE:
            self.send_json({"error": "Tool not found" if not OMEGA_CORE else "No tool specified"}, 400)
            return
        try:
            result = execute_tool(tool_name, **params)
            self.send_json({"result": str(result.content) if hasattr(result, 'content') else str(result), "success": True})
        except Exception as e:
            self.send_json({"error": str(e), "success": False})
    
    def _handle_memory_search(self, data):
        query = data.get("query", "")
        if not OMEGA_CORE:
            self.send_json({"results": []})
            return
        try:
            results = search_memories(query)
            self.send_json({"results": results})
        except:
            self.send_json({"results": []})
    
    def _handle_memory_save(self, data):
        key = data.get("key", "")
        value = data.get("value", "")
        if not key or not OMEGA_CORE:
            self.send_json({"error": "Invalid"})
            return
        try:
            save_memory(key, value)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_memory_delete(self, data):
        key = data.get("key", "")
        if not key or not OMEGA_CORE:
            self.send_json({"error": "Invalid"})
            return
        try:
            from memory import delete_memory
            delete_memory(key)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_note_save(self, data):
        title = data.get("title", "")
        content = data.get("content", "")
        tags = data.get("tags", [])
        if not title or not OMEGA_CORE:
            self.send_json({"error": "Invalid"})
            return
        try:
            memory_save_note(title, content, tags=tags)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_note_delete(self, data):
        title = data.get("title", "")
        if not title or not OMEGA_CORE:
            self.send_json({"error": "Invalid"})
            return
        try:
            delete_note(title)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_new_session(self, data):
        session_id = str(uuid.uuid4())
        agent = get_or_create_agent(session_id)
        self.send_json({"session_id": session_id, "success": True})
    
    def _handle_mcp_connect(self, data):
        self.send_json({"message": "MCP connect - implement your MCP server here", "success": False})
    
    def _handle_mcp_disconnect(self, data):
        self.send_json({"success": True})
    
    def _handle_write_file(self, data):
        path = data.get("path", "")
        content = data.get("content", "")
        if not path:
            self.send_json({"error": "No path"}, 400)
            return
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self.send_json({"success": True, "path": str(path)})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_delete_file(self, data):
        path = data.get("path", "")
        if not path:
            self.send_json({"error": "No path"}, 400)
            return
        try:
            p = Path(path)
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                import shutil
                shutil.rmtree(p)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    def _handle_tasks(self, data):
        action = data.get("action", "list")
        from tasks import tasks as tasks_tool
        try:
            if action == "list":
                result = tasks_tool(action="list")
            elif action == "add":
                result = tasks_tool(action="add", title=data.get("title",""), description=data.get("description",""), priority=data.get("priority","medium"))
            elif action == "done":
                result = tasks_tool(action="done", task_id=data.get("task_id",""))
            elif action == "delete":
                result = tasks_tool(action="delete", task_id=data.get("task_id",""))
            else:
                result = tasks_tool(action="list")
            self.send_json({"result": str(result.content) if hasattr(result, 'content') else str(result), "success": True})
        except Exception as e:
            self.send_json({"error": str(e)})
    
    # ─── Helpers ─────────────────────────────────────────────────
    def send_html(self, html=None):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if html is None:
            html = self._load_ui()
        self.wfile.write(html.encode("utf-8"))
    
    def _load_ui(self):
        """Load UI from the omega_desktop_ui.html file."""
        ui_path = OMEGA_DIR / "omega_desktop_ui.html"
        if ui_path.exists():
            return ui_path.read_text("utf-8")
        return INDEX_HTML
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
    
    def log_message(self, format, *args):
        print(f"[Ω DESKTOP] {args[0]} {args[1]} {args[2]}")


# ─── Start Time ──────────────────────────────────────────────────
_START_TIME = time.time()

# ─── Server Runner ───────────────────────────────────────────────
def run_server(port=DEFAULT_PORT, host="127.0.0.1"):
    """Start the HTTP server."""
    server = HTTPServer((host, port), OmegaDesktopHandler)
    print(f"\n  ┌──────────────────────────────────────────────┐")
    print(f"  │  Ω OMEGA Desktop v{VERSION}                      │")
    print(f"  │  Running at http://{host}:{port}                 │")
    print(f"  │  Press Ctrl+C to stop                           │")
    print(f"  └──────────────────────────────────────────────┘\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Ω Server stopped.")
        server.server_close()


# ─── Main Entry Point ────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ω OMEGA Desktop App")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default {DEFAULT_PORT})")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    parser.add_argument("--native", action="store_true", help="Open in native PyWebView window")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()
    
    # Start server in background thread
    from threading import Thread
    server_thread = Thread(target=run_server, args=(args.port, args.host), daemon=True)
    server_thread.start()
    time.sleep(0.5)
    
    url = f"http://{args.host}:{args.port}"
    
    if args.native:
        try:
            import webview
            webview.create_window("Ω OMEGA Desktop", url, width=1280, height=800, resizable=True)
            webview.start()
        except ImportError:
            print("PyWebView not available, falling back to browser")
            import webbrowser
            webbrowser.open(url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    elif not args.no_browser:
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


# The UI is loaded from omega_desktop_ui.html
# If that file doesn't exist, a minimal fallback is shown
INDEX_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Ω OMEGA Desktop</title><style>body{font-family:system-ui,sans-serif;background:#0a0e17;color:#e0e0e0;display:flex;align-items:center;justify-content:center;height:100vh}div{text-align:center}h1{color:#00d4ff}.dim{color:#64748b}</style></head><body><div><h1>Ω OMEGA Desktop</h1><p class="dim">UI file not found. Run: <code>python omega_desktop.py</code></p></div></body></html>"""


