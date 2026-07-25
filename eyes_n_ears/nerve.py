import socketio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time


# ------------------------------------------------------------------
# MJPEG stream handler
# ------------------------------------------------------------------

class _MJPEGHandler(BaseHTTPRequestHandler):
    """Handles a single MJPEG client connection."""

    def do_GET(self):
        print(f"Client connected: {self.client_address}")
        if self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            while True:
                frame = self.server.nerve.get_latest_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                try:
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                except (BrokenPipeError, ConnectionResetError):
                    break  # client disconnected
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default HTTP logs


class _MJPEGServer(ThreadingHTTPServer):
    """HTTPServer subclass that holds a reference to Synapse."""

    def __init__(self, server_address, nerve):
        super().__init__(server_address, _MJPEGHandler)
        self.nerve = nerve


# ------------------------------------------------------------------
# Nerve
# ------------------------------------------------------------------

class Nerve:
    def __init__(self, brain_url, mjpeg_port=8000):
        """
        Initialize the Nerve module.

        Args:
            brain_url:   URL of the Flask brain
            mjpeg_port:  port to serve the MJPEG stream on (default 8000)
        """
        self.brain_url = brain_url
        self.mjpeg_port = mjpeg_port

        self._latest_frame = None
        self._frame_lock = threading.Lock()

        # Socket.IO client
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0)
        self._register_sio_events()

        # MJPEG server
        self.mjpeg_server = _MJPEGServer(('0.0.0.0', self.mjpeg_port), self)

    # ------------------------------------------------------------------
    # Socket.IO events
    # ------------------------------------------------------------------

    def _register_sio_events(self):
        @self.sio.event
        def connect():
            print(f"[Nerve] Connected to brain at {self.brain_url}")

        @self.sio.event
        def disconnect():
            print("[Nerve] Disconnected from brain.")

        @self.sio.event
        def connect_error(data):
            print(f"[Nerve] Connection error: {data}")

    # ------------------------------------------------------------------
    # Public callbacks (called by Ear and Eye)
    # ------------------------------------------------------------------

    def send_command(self, payload):
        """
        Called by Ear when a voice command is recognized.

        Args:
            payload: dict with 'text' and 'command' keys
        """
        if self.sio.connected:
            self.sio.emit('command', payload)
            print(f"[Nerve] Sent command: {payload['command']}")
        else:
            print("[Nerve] Cannot send command - not connected to brain.")

    def send_frame(self, jpeg_bytes):
        """
        Called by Eye on every frame.
        Stores the latest frame for the MJPEG server to serve.

        Args:
            jpeg_bytes: raw JPEG bytes
        """
        with self._frame_lock:
            self._latest_frame = jpeg_bytes

    def get_latest_frame(self):
        """Used internally by the MJPEG handler."""
        with self._frame_lock:
            return self._latest_frame

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def start(self):
        """Connect to brain and start MJPEG server. Blocking."""
        # Connect Socket.IO to brain
        print(f"[Nerve] Connecting to brain at {self.brain_url} ...")
        try:
            self.sio.connect(self.brain_url)
        except Exception as e:
            print(f"[Nerve] Initial connection failed: {e}. Will retry in background.")

        # Start MJPEG server in a background thread
        mjpeg_thread = threading.Thread(
            target=self.mjpeg_server.serve_forever,
            daemon=True
        )
        mjpeg_thread.start()
        print(f"[Nerve] MJPEG stream available at http://0.0.0.0:{self.mjpeg_port}/stream")

    def stop(self):
        if self.sio.connected:
            self.sio.disconnect()
        self.mjpeg_server.shutdown()
        print("[Nerve] Stopped.")
