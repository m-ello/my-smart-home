# Smart Home — Distributed Detection & Voice System

A distributed smart home system built as a bachelor's diploma project. Responsibilities are split across two nodes on a local network: a Raspberry Pi 4 handling sensing (camera + microphone) and a laptop acting as the central "brain" (state, logic, and web dashboard).

## Architecture

```
┌────────────────────────────┐      Socket.IO (port 5000)      ┌──────────────────────────────┐
│   eyes_n_ears (Pi 4)       │ ───────────────────────────────▶│         brain (laptop)       │
│                            │◀────────────────────────────────│                              │
│                            │                                 │                              │
│  • eye.py   — Picamera2    │      MJPEG stream (port 8000)   │  • main.py  — Flask +        │
│    capture → JPEG frames   │ ───────────────────────────────▶│    Flask-SocketIO server     │
│  • ear.py   — Vosk voice   │                                 │  • vision.py — MOG2 + YOLOv8n│
│    recognition, wake       │                                 │    on the incoming MJPEG feed│
│    word "chip"             │                                 │  • mind.py  — device state   │
│  • nerve.py — Socket.IO    │                                 │    machine + command router  │
│    client + MJPEG server   │                                 │  • memory.py — thread-safe   │
│                            │                                 │    shared state store        │
└────────────────────────────┘                                 │  • templates/index.html +    │
                                                               │    static/css/style.css      │
                                                               └──────────────────────────────┘
```

The key design point: **detection runs on the brain, not the Pi.** The Pi only captures and streams frames (`eye.py` → `nerve.py`'s MJPEG server on port `8000`); the laptop pulls that MJPEG stream and runs `vision.py` (MOG2 + YOLOv8n) against it. Voice recognition, by contrast, runs locally on the Pi (`ear.py`), and only recognized commands are sent to the brain over Socket.IO.

### eyes_n_ears (Raspberry Pi 4)

- **`eye.py`** — captures frames via `Picamera2` at 320×240, JPEG-encodes them (quality 30), and hands each frame to `nerve.py` through a callback.
- **`ear.py`** — Vosk (`en-us`) speech recognition with a constrained grammar (wake word `"chip"` + the known command phrases). Only processes text if the first word matches the wake word.
- **`nerve.py`** — the Pi's connective layer: a Socket.IO client that talks to the brain, plus a threaded MJPEG HTTP server (`/stream` on port `8000`) that serves whatever frame `eye.py` last produced.
- **`main.py`** — wires `ear`, `eye`, and `nerve` together; listens for `ear_control` (start/stop listening) and `shutdown` events from the brain.
- **`run.sh`** — waits for the brain to become reachable (`ping 10.42.0.1`) before starting `main.py`; logs to `monitor.log`.

### brain (Laptop)

- **`main.py`** — Flask + Flask-SocketIO (`async_mode='threading'`, `cors_allowed_origins='*'`) server on port `5000`. Handles incoming voice `command` events, serves the dashboard, exposes REST routes (`/state`, `/device/toggle/<name>`, `/commands/clear`, `/shutdown`), and coordinates a clean two-way shutdown handshake with the Pi (`shutdown` → `shutdown_ack`).
- **`vision.py`** — pulls the Pi's MJPEG stream and runs the detection pipeline:
    1. **MOG2** background subtraction (`history=500`, `varThreshold=50`) — a frame only proceeds to YOLO if foreground motion exceeds 0.5% of the frame area.
    2. **YOLOv8n** (`ultralytics`, class `0` = person, confidence threshold `0.4`).
    3. On detection → `_activate_ear()`, which emits `ear_control` / `person_present` and cancels any pending deactivation timer.
    4. On motion-without-person → a 10-second `threading.Timer` schedules `_deactivate_ear()`.
- **`mind.py`** — device state machine (lights / fan / music) and command dispatcher; broadcasts `state` updates to the dashboard.
- **`memory.py`** — thread-safe (`Lock`-protected) store for command history and presence state.
- **`templates/index.html` + `static/css/style.css`** — the dashboard: live camera feed, presence/ear/uplink status badges, device toggles, command log.
- **`simulate.py`** — a standalone Socket.IO client that connects to the brain and lets you fake voice commands and presence toggles from the keyboard, for developing the dashboard without the Pi powered on.
- **`run.sh`** — activates the venv and starts `main.py`.
- **`connection_up.sh`** — brings up the local WiFi hotspot (`nmcli con up "Hotspot"`) that the Pi joins.
- **`start_ssh.sh`** — keeps a monitored SSH session open to the Pi (`rrr@10.42.0.245`), logging connects/disconnects to `monitor.log`.

## Getting Started

### Prerequisites

- Raspberry Pi 4 with camera module and microphone, Picamera2 installed
- A laptop to run the brain, on the same network (or hosting the hotspot the Pi joins)
- Python 3 on both machines

### 1. Bring up the network (laptop)

```bash
./connection_up.sh
```

### 2. Start the brain (laptop)

```bash
cd brain/
python -m venv venv && source venv/bin/activate
pip install flask flask-socketio ultralytics opencv-python
./run.sh
```

The dashboard will be served at `http://10.42.0.1:5000`.

### 3. Start eyes_n_ears (Raspberry Pi)

```bash
cd eyes_n_ears/
pip install vosk pyaudio picamera2 python-socketio opencv-python
./run.sh
```

This blocks until it can ping the brain at `10.42.0.1`, then connects and starts streaming.

### 4. Testing without the Pi

```bash
cd brain/
python simulate.py --brain http://localhost:5000
```

Lets you fake voice commands (`w`/`q`/`s`/`a`/`c`/`x`/`z`) and presence toggles (`1`/`2`) from the keyboard.

## Known Issues

- **Stationary-person detection gap**: MOG2 gradually absorbs a motionless person into its background model. When that happens, `_detect_motion()` returns `False` and the loop `continue`s _before_ YOLO ever runs again — so once a person stops moving long enough, the pipeline stops re-confirming their presence altogether (no reactivation, no deactivation) until they move again.
- **No auth on the wire**: Flask-SocketIO is configured with `cors_allowed_origins='*'` and no authentication on the Socket.IO channel or REST routes — fine for a closed hotspot demo, but worth locking down  before any real-world deployment.


