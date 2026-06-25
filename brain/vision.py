import cv2
import numpy as np
import threading
import time
from ultralytics import YOLO


class Vision:
    def __init__(self, stream_url, memory, socketio, inactivity_timeout=20):
        """
        Initialize the Vision module.
        Reads the MJPEG stream from the RPi, runs MOG2 + YOLOv8n per frame.
        If a person is detected, activates the ear.
        If no person is detected for inactivity_timeout seconds, deactivates the ear.

        Args:
            stream_url:          MJPEG stream URL
            memory:              Memory instance
            socketio:            SocketIO instance
            inactivity_timeout:  seconds of no detection before ear is deactivated (default 20)
        """
        self.stream_url = stream_url
        self.memory = memory
        self.socketio = socketio
        self.inactivity_timeout = inactivity_timeout

        self._last_detected = None   # timestamp of last person detection
        self._ear_active = False     # current ear state
        self._timer = None           # inactivity timer

        # Stage 1: MOG2
        self.mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=50,
            detectShadows=False
        )

        # Stage 2: YOLOv8n
        self.model = YOLO("yolov8n.pt")

        self.is_running = False
        print("[Vision] Initialized.")

    # ------------------------------------------------------------------
    # Motion detection (Stage 1)
    # ------------------------------------------------------------------

    def _detect_motion(self, frame):
        fg_mask = self.mog2.apply(frame)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        motion_pixels = cv2.countNonZero(fg_mask)
        frame_area = frame.shape[0] * frame.shape[1]
        return motion_pixels > (frame_area * 0.005)

    # ------------------------------------------------------------------
    # Person detection (Stage 2)
    # ------------------------------------------------------------------

    def _person_in_frame(self, frame):
        """Returns True if at least one person is detected in the frame."""
        results = self.model(frame, classes=[0], verbose=False)
        for result in results:
            for box in result.boxes:
                if box.conf[0].item() > 0.4:
                    return True
        return False

    # ------------------------------------------------------------------
    # Ear control
    # ------------------------------------------------------------------

    def _activate_ear(self):
        """Activates the ear and cancels any pending inactivity timer."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        if not self._ear_active:
            self._ear_active = True
            self.memory.set_person_present(True)
            self.socketio.emit('ear_control', {'active': True})
            self.socketio.emit('person_present', {'present': True})
            print("[Vision] Person detected — ear activated.")

    def _schedule_deactivation(self):
        """Starts the inactivity timer. Resets it if already running."""
        if self._timer is not None:
            self._timer.cancel()

        self._timer = threading.Timer(
            self.inactivity_timeout,
            self._deactivate_ear
        )
        self._timer.daemon = True
        self._timer.start()

    def _deactivate_ear(self):
        """Called by the inactivity timer after timeout."""
        self._ear_active = False
        self._timer = None
        self.memory.set_person_present(False)
        self.socketio.emit('ear_control', {'active': False})
        self.socketio.emit('person_present', {'present': False})
        print("[Vision] No person for 20s — ear deactivated.")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def start(self):
        self.is_running = True
        print(f"[Vision] Connecting to stream at {self.stream_url} ...")

        while self.is_running:
            cap = cv2.VideoCapture(self.stream_url)
            if not cap.isOpened():
                print("[Vision] Stream unavailable, retrying in 3s...")
                time.sleep(3)
                continue

            print("[Vision] Stream connected.")
            
            try:
                while self.is_running:
                    ret, frame = cap.read()
                    if not ret:
                        print("[Vision] Stream lost, reconnecting...")
                        break

                    # Stage 1: motion gate
                    if not self._detect_motion(frame):
                        continue

                    # Stage 2: person detection
                    if self._person_in_frame(frame):
                        self._activate_ear()
                    else:
                        # Motion detected but no person — start/reset deactivation timer
                        if self._ear_active:
                            self._schedule_deactivation()

            except Exception as e:
                print(f"[Vision] Error: {e}")
            finally:
                cap.release()
                time.sleep(1)

    def stop(self):
        self.is_running = False
        if self._timer is not None:
            self._timer.cancel()
