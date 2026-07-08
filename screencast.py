#!/usr/bin/env python3
"""OMEGA Screencast Module — Screen capture, streaming, and screen sharing.
Leverages MSS (cross-platform) for fast screen capture, and provides
an MJPEG HTTP stream server so the user can view or share their screen live."""

import os
import sys
import time
import json
import base64
import threading
import io
import logging
from pathlib import Path
from datetime import datetime

import warnings
warnings.filterwarnings('ignore')

import numpy as np
from PIL import Image

logger = logging.getLogger("omega.screencast")

# ─── Constants ───────────────────────────────────────────────────────────────

SNAPSHOT_DIR = Path("D:\\TERMINALCLI")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Try to import MSS for fastest screen capture
_HAS_MSS = False
try:
    import mss
    _HAS_MSS = True
except ImportError:
    pass

# Fallback: PIL.ImageGrab
_HAS_PILGRAB = False
try:
    from PIL import ImageGrab
    _HAS_PILGRAB = True
except ImportError:
    pass


# ─── Screen Capture ──────────────────────────────────────────────────────────

def _get_screen_info():
    """Get information about all monitors/displays."""
    if _HAS_MSS:
        try:
            with mss.MSS() as sct:
                monitors = []
                for i, m in enumerate(sct.monitors):
                    monitors.append({
                        "index": i,
                        "width": m["width"],
                        "height": m["height"],
                        "left": m["left"],
                        "top": m["top"],
                    })
                return monitors
        except Exception:
            pass
    
    # Fallback: try PIL ImageGrab
    if _HAS_PILGRAB:
        try:
            img = ImageGrab.grab()
            return [{
                "index": 0,
                "width": img.width,
                "height": img.height,
                "left": 0,
                "top": 0,
            }]
        except Exception:
            pass
    
    return [{"index": 0, "width": 0, "height": 0, "left": 0, "top": 0, "error": "No screen capture available"}]


def capture_screen(monitor=1, save=True, output_path=""):
    """Capture the screen (or a specific monitor).
    
    Args:
        monitor: Monitor index (0=all monitors, 1=primary, etc.)
        save: Whether to save the image to disk
        output_path: Optional specific path to save to
    
    Returns:
        dict with filepath, dimensions, and base64-encoded JPEG data
    """
    img = None
    
    # Method 1: MSS (fastest)
    if _HAS_MSS:
        try:
            with mss.MSS() as sct:
                if monitor == 0 and len(sct.monitors) > 0:
                    # Capture all monitors combined
                    sct_img = sct.grab(sct.monitors[0])
                elif monitor < len(sct.monitors):
                    sct_img = sct.grab(sct.monitors[monitor])
                else:
                    sct_img = sct.grab(sct.monitors[1])
                
                img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
        except Exception as e:
            logger.warning(f"MSS capture failed: {e}")
    
    # Method 2: PIL ImageGrab (fallback)
    if img is None and _HAS_PILGRAB:
        try:
            if monitor == 0:
                # Grab all monitors
                img = ImageGrab.grab(all_screens=True)
            else:
                img = ImageGrab.grab()
        except Exception as e:
            logger.warning(f"PIL ImageGrab failed: {e}")
    
    if img is None:
        return {"success": False, "error": "No screen capture method available"}
    
    # Determine save path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if not output_path:
        output_path = str(SNAPSHOT_DIR / f"screenshot_{timestamp}.jpg")
    
    # Save to disk
    saved_path = ""
    if save:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, "JPEG", quality=85)
        saved_path = output_path
    
    # Encode as base64 JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    jpeg_bytes = buf.getvalue()
    b64_data = base64.b64encode(jpeg_bytes).decode("utf-8")
    
    return {
        "success": True,
        "filepath": saved_path,
        "width": img.width,
        "height": img.height,
        "format": "jpeg",
        "size_bytes": len(jpeg_bytes),
        "base64": b64_data,
        "timestamp": datetime.now().isoformat(),
    }


def list_screens():
    """List all available monitors/displays."""
    info = _get_screen_info()
    result = []
    for m in info:
        result.append({
            "index": m["index"],
            "width": m["width"],
            "height": m["height"],
            "left": m["left"],
            "top": m["top"],
        })
    return result


# ─── MJPEG Screen Stream Server ──────────────────────────────────────────────

class ScreenStreamServer:
    """Simple MJPEG HTTP server that streams the screen to a browser."""
    
    def __init__(self, monitor=1, port=8081, quality=70, fps=15):
        self.monitor = monitor
        self.port = port
        self.quality = quality
        self.fps = fps
        self._running = False
        self._server = None
        self._thread = None
    
    def start(self):
        if self._running:
            return {"success": False, "error": "Stream already running"}
        
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
        except ImportError:
            return {"success": False, "error": "HTTP server not available"}
        
        self._running = True
        
        class ScreenMJPEGHandler(BaseHTTPRequestHandler):
            server_ref = self
            
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    html = f"""<html><body style="background:#111;margin:0;overflow:hidden">
                    <h2 style="color:white;font-family:sans-serif;position:absolute;top:10px;left:10px;z-index:10;text-shadow:0 0 8px rgba(0,0,0,0.8)">
                    ? OMEGA Screen Share (Monitor {self.server_ref.monitor})</h2>
                    <img src="/stream" style="width:100vw;height:100vh;object-fit:contain">
                    </body></html>"""
                    self.wfile.write(html.encode())
                elif self.path == '/stream':
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'close')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    try:
                        while self.server_ref._running:
                            # Capture screen
                            buf = io.BytesIO()
                            if _HAS_MSS:
                                try:
                                    with mss.MSS() as sct:
                                        monitor_idx = self.server_ref.monitor
                                        if monitor_idx < len(sct.monitors):
                                            sct_img = sct.grab(sct.monitors[monitor_idx])
                                        else:
                                            sct_img = sct.grab(sct.monitors[1])
                                        img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
                                        img.save(buf, format="JPEG", quality=self.server_ref.quality)
                                except Exception:
                                    time.sleep(0.05)
                                    continue
                            elif _HAS_PILGRAB:
                                try:
                                    img = ImageGrab.grab()
                                    img.save(buf, format="JPEG", quality=self.server_ref.quality)
                                except Exception:
                                    time.sleep(0.05)
                                    continue
                            else:
                                break
                            
                            frame_data = buf.getvalue()
                            try:
                                self.wfile.write(b'--frame\r\n')
                                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                                self.wfile.write(f'Content-Length: {len(frame_data)}\r\n\r\n'.encode())
                                self.wfile.write(frame_data)
                                self.wfile.write(b'\r\n')
                            except Exception:
                                break
                            
                            time.sleep(1.0 / self.server_ref.fps)
                    finally:
                        pass
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress HTTP log noise
        
        self._server = HTTPServer(('0.0.0.0', self.port), ScreenMJPEGHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        
        return {
            "success": True,
            "message": f"Screen stream started at http://localhost:{self.port}",
            "url": f"http://localhost:{self.port}",
            "monitor": self.monitor,
        }
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server = None
        return {"success": True, "message": "Screen stream stopped"}


# ─── Global Stream Instance ──────────────────────────────────────────────────

_stream_server = None
_stream_lock = threading.Lock()


def start_screen_stream(monitor=1, port=8081, quality=70, fps=15):
    """Start a live MJPEG screen stream server."""
    global _stream_server
    with _stream_lock:
        if _stream_server and _stream_server._running:
            return {"success": False, "error": f"Screen stream already running at http://localhost:{_stream_server.port}"}
        _stream_server = ScreenStreamServer(monitor, port, quality, fps)
        return _stream_server.start()


def stop_screen_stream():
    """Stop the screen stream server."""
    global _stream_server
    with _stream_lock:
        if _stream_server and _stream_server._running:
            return _stream_server.stop()
        return {"success": False, "error": "No screen stream running"}


def screen_stream_status():
    """Check if the screen stream is running."""
    global _stream_server
    with _stream_lock:
        if _stream_server and _stream_server._running:
            return {
                "running": True,
                "url": f"http://localhost:{_stream_server.port}",
                "monitor": _stream_server.monitor,
                "port": _stream_server.port,
                "quality": _stream_server.quality,
                "fps": _stream_server.fps,
            }
        return {"running": False}


# ─── Cleanup ─────────────────────────────────────────────────────────────────

def cleanup():
    """Stop all screen streaming activity."""
    stop_screen_stream()
