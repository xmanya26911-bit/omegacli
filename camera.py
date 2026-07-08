#!/usr/bin/env python3
"""OMEGA Camera Module — Webcam capture, streaming, and computer vision features.
Supports any DirectShow-compatible camera including Camo Studio virtual webcam."""

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

# Suppress OpenCV warnings
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'
import warnings
warnings.filterwarnings('ignore')

import cv2
import numpy as np

logger = logging.getLogger("omega.camera")

# ─── Constants ───────────────────────────────────────────────────────────────

DEFAULT_CAMERA_INDEX = 0
SNAPSHOT_DIR = Path.home() / ".omega" / "camera_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Camera Management ───────────────────────────────────────────────────────

def _open_camera(index=0, backend=None):
    """Open a camera with retry logic. Returns (cap, backend_used) or (None, None)."""
    backends_to_try = []
    if backend is not None:
        backends_to_try = [backend]
    else:
        backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_ANY]  # DirectShow first on Windows

    for b in backends_to_try:
        try:
            cap = cv2.VideoCapture(index, b)
            if cap.isOpened():
                # Test read
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    return cap, b
                cap.release()
        except Exception:
            continue
    return None, None


def list_cameras(max_check=10):
    """Scan and list all available camera devices with details."""
    available = []
    for i in range(max_check):
        cap, backend = _open_camera(i)
        if cap is not None:
            info = {
                "index": i,
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "brightness": cap.get(cv2.CAP_PROP_BRIGHTNESS),
                "contrast": cap.get(cv2.CAP_PROP_CONTRAST),
                "saturation": cap.get(cv2.CAP_PROP_SATURATION),
                "hue": cap.get(cv2.CAP_PROP_HUE),
                "gain": cap.get(cv2.CAP_PROP_GAIN),
                "exposure": cap.get(cv2.CAP_PROP_EXPOSURE),
                "backend": cap.getBackendName(),
            }
            # Clean up NaN/None values
            info = {k: (v if v is not None and v == v else 0) for k, v in info.items()}
            available.append(info)
            cap.release()
    return available


def capture_frame(index=DEFAULT_CAMERA_INDEX, save=True, output_path=None):
    """Capture a single frame from the specified camera.
    
    Args:
        index: Camera device index (default 0)
        save: Whether to save the image to disk
        output_path: Specific path to save to (auto-generated if None)
    
    Returns:
        dict with frame info, filepath, and base64-encoded image
    """
    cap, backend = _open_camera(index)
    if cap is None:
        return {"success": False, "error": f"Camera {index} not available"}

    # Read a few frames to let auto-exposure settle
    frame = None
    for _ in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            break
        time.sleep(0.05)

    cap.release()

    if frame is None or frame.size == 0:
        return {"success": False, "error": "Failed to capture frame"}

    h, w = frame.shape[:2]
    timestamp = datetime.now()

    result = {
        "success": True,
        "camera_index": index,
        "width": w,
        "height": h,
        "channels": frame.shape[2] if len(frame.shape) > 2 else 1,
        "timestamp": timestamp.isoformat(),
        "filesize_bytes": 0,
        "filepath": "",
    }

    # Save to disk
    if save:
        if output_path:
            path = Path(output_path)
        else:
            filename = f"snap_cam{index}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            path = SNAPSHOT_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        result["filepath"] = str(path)
        result["filesize_bytes"] = path.stat().st_size

    # Encode as base64 JPEG for inline viewing
    ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ret:
        result["base64_jpg"] = base64.b64encode(buf.tobytes()).decode('utf-8')
        result["base64_len"] = len(result["base64_jpg"])

    return result


def detect_faces(frame):
    """Detect faces in a frame using Haar cascades. Returns list of face rects."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Use OpenCV's built-in face detector
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]


def detect_motion(frame1, frame2, threshold=5000):
    """Compare two frames and detect significant motion.
    Returns (has_motion, score, diff_image_base64)."""
    if frame1 is None or frame2 is None:
        return False, 0, None
    
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Blur to reduce noise
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    
    diff = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    
    # Dilate to fill gaps
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    score = int(np.sum(thresh) / 255)
    has_motion = score > threshold
    
    # Encode diff image
    diff_b64 = None
    if has_motion:
        _, buf = cv2.imencode('.jpg', thresh, [cv2.IMWRITE_JPEG_QUALITY, 80])
        diff_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
    
    return has_motion, score, diff_b64


def analyze_frame(index=DEFAULT_CAMERA_INDEX, detect_faces_flag=True, detect_motion_flag=True):
    """Capture and analyze a frame for faces and motion.
    
    Returns detailed analysis results.
    """
    cap, backend = _open_camera(index)
    if cap is None:
        return {"success": False, "error": f"Camera {index} not available"}

    # Capture two frames for motion detection
    frames = []
    for _ in range(6):
        ret, frame = cap.read()
        if ret and frame is not None:
            frames.append(frame)
        time.sleep(0.03)
    
    cap.release()
    
    if len(frames) < 2:
        return {"success": False, "error": "Could not capture enough frames"}
    
    frame = frames[-1]  # Latest frame for analysis
    h, w = frame.shape[:2]
    timestamp = datetime.now()
    
    result = {
        "success": True,
        "camera_index": index,
        "width": w,
        "height": h,
        "timestamp": timestamp.isoformat(),
        "faces": [],
        "motion_detected": False,
        "motion_score": 0,
    }
    
    # Face detection
    if detect_faces_flag:
        faces = detect_faces(frame)
        result["faces"] = [
            {"x": int(x), "y": int(y), "width": int(w), "height": int(h), "area": int(w*h)}
            for (x, y, w, h) in faces
        ]
        result["face_count"] = len(faces)
    
    # Motion detection (compare last two frames)
    if detect_motion_flag and len(frames) >= 2:
        has_motion, score, _ = detect_motion(frames[-2], frames[-1])
        result["motion_detected"] = has_motion
        result["motion_score"] = score
    
    # Save annotated frame
    display = frame.copy()
    
    # Draw face rectangles
    for face in result["faces"]:
        x, y, w, h = face["x"], face["y"], face["width"], face["height"]
        cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(display, f"Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    if result["motion_detected"]:
        cv2.putText(display, f"MOTION: {result['motion_score']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Save annotated image
    filename = f"analyze_cam{index}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
    path = SNAPSHOT_DIR / filename
    cv2.imwrite(str(path), display, [cv2.IMWRITE_JPEG_QUALITY, 92])
    result["filepath"] = str(path)
    result["filesize_bytes"] = path.stat().st_size
    
    # Base64 for inline
    _, buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 85])
    result["base64_jpg"] = base64.b64encode(buf.tobytes()).decode('utf-8')
    
    return result


# ─── Background Watcher ──────────────────────────────────────────────────────

class CameraWatcher:
    """Background thread that watches a camera for motion/faces and saves events."""
    
    def __init__(self, index=0, interval=1.0, motion_threshold=5000, 
                 detect_faces=True, max_events=50):
        self.index = index
        self.interval = interval
        self.motion_threshold = motion_threshold
        self.detect_faces_flag = detect_faces
        self.max_events = max_events
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.events = []
        self._prev_frame = None
    
    def start(self):
        if self._running:
            return {"success": False, "error": "Watcher already running"}
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return {"success": True, "message": f"Camera watcher started on index {self.index}"}
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        return {"success": True, "message": "Camera watcher stopped", "events_captured": len(self.events)}
    
    def get_status(self):
        with self._lock:
            return {
                "running": self._running,
                "camera_index": self.index,
                "events_captured": len(self.events),
                "last_events": self.events[-5:] if self.events else []
            }
    
    def _run(self):
        cap, backend = _open_camera(self.index)
        if cap is None:
            self._running = False
            return
        
        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
            
            timestamp = datetime.now()
            event = None
            
            # Motion detection
            if self._prev_frame is not None:
                has_motion, score, _ = detect_motion(self._prev_frame, frame, self.motion_threshold)
                if has_motion:
                    # Save frame
                    filename = f"motion_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                    path = SNAPSHOT_DIR / filename
                    cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    event = {
                        "type": "motion",
                        "timestamp": timestamp.isoformat(),
                        "score": score,
                        "filepath": str(path),
                    }
            
            # Face detection (every few frames)
            if self.detect_faces_flag and (event or int(time.time() * 2) % 3 == 0):
                faces = detect_faces(frame)
                if faces:
                    filename = f"face_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                    path = SNAPSHOT_DIR / filename
                    # Draw rects
                    display = frame.copy()
                    for (x, y, w, h) in faces:
                        cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.imwrite(str(path), display, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    face_event = {
                        "type": "face_detected",
                        "timestamp": timestamp.isoformat(),
                        "face_count": len(faces),
                        "filepath": str(path),
                    }
                    with self._lock:
                        self.events.append(face_event)
                        if len(self.events) > self.max_events:
                            self.events.pop(0)
            
            if event:
                with self._lock:
                    self.events.append(event)
                    if len(self.events) > self.max_events:
                        self.events.pop(0)
            
            self._prev_frame = frame.copy()
            time.sleep(self.interval)
        
        cap.release()


# Global watcher instance
_watcher = None
_watcher_lock = threading.Lock()


def start_watcher(index=0, interval=1.0, motion_threshold=5000, detect_faces=True):
    global _watcher
    with _watcher_lock:
        if _watcher and _watcher._running:
            return {"success": False, "error": "Watcher already running. Stop it first."}
        _watcher = CameraWatcher(index, interval, motion_threshold, detect_faces)
        return _watcher.start()


def stop_watcher():
    global _watcher
    with _watcher_lock:
        if _watcher and _watcher._running:
            return _watcher.stop()
        return {"success": False, "error": "No watcher running"}


def watcher_status():
    global _watcher
    with _watcher_lock:
        if _watcher:
            return _watcher.get_status()
        return {"running": False, "events_captured": 0, "last_events": []}


# ─── MJPEG Stream Server (Optional) ──────────────────────────────────────────

class StreamServer:
    """Simple MJPEG HTTP server so the user can view the camera feed in a browser."""
    
    def __init__(self, index=0, port=8080, quality=70, fps=15):
        self.index = index
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
        
        class MJPEGHandler(BaseHTTPRequestHandler):
            server_ref = self
            
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    html = f"""<html><body style="background:#111;margin:0;overflow:hidden">
                    <h2 style="color:white;font-family:sans-serif;position:absolute;top:10px;left:10px;z-index:10">
                    OMEGA Camera Stream (Camera {self.server_ref.index})</h2>
                    <img src="/stream" style="width:100vw;height:100vh;object-fit:contain">
                    </body></html>"""
                    self.wfile.write(html.encode())
                elif self.path == '/stream':
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    
                    cap = cv2.VideoCapture(self.server_ref.index, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(self.server_ref.index)
                    
                    try:
                        while self.server_ref._running and cap.isOpened():
                            ret, frame = cap.read()
                            if not ret:
                                time.sleep(0.05)
                                continue
                            
                            ret, buf = cv2.imencode('.jpg', frame, 
                                [cv2.IMWRITE_JPEG_QUALITY, self.server_ref.quality])
                            if ret:
                                frame_data = buf.tobytes()
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
                        cap.release()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress HTTP log noise
        
        self._server = HTTPServer(('0.0.0.0', self.port), MJPEGHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        
        return {
            "success": True,
            "message": f"Stream server started at http://localhost:{self.port}",
            "url": f"http://localhost:{self.port}",
            "camera_index": self.index,
        }
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()
        return {"success": True, "message": "Stream server stopped"}


_stream_server = None

def start_stream(index=0, port=8080, quality=70, fps=15):
    global _stream_server
    if _stream_server and _stream_server._running:
        return {"success": False, "error": f"Stream already running at http://localhost:{_stream_server.port}"}
    _stream_server = StreamServer(index, port, quality, fps)
    return _stream_server.start()


def stop_stream():
    global _stream_server
    if _stream_server and _stream_server._running:
        return _stream_server.stop()
    return {"success": False, "error": "No stream running"}


# ─── Cleanup ─────────────────────────────────────────────────────────────────

def cleanup():
    """Stop all camera activity."""
    stop_watcher()
    stop_stream()
