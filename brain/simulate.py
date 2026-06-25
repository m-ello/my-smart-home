"""
simulate.py — RPi simulator for brain UI development.
Connects to the brain via Socket.IO and lets you fire commands,
toggle person presence, and stream a fake MJPEG feed,
all without the actual RPi4 running.

Usage:
    python simulate.py [--brain http://localhost:5000]
"""

import argparse
import socketio
import threading
import time

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

BRAIN_URL = "http://localhost:5000"

COMMANDS = {
    "w": ("lights on",  "LIGHTS_ON"),
    "q": ("lights off", "LIGHTS_OFF"),
    "s": ("fan on",     "FAN_ON"),
    "a": ("fan off",    "FAN_OFF"),
    "c": ("music on",   "MUSIC_ON"),
    "x": ("music pause","PAUSE_MUSIC"),
    "z": ("music off",  "MUSIC_OFF"),
    "2": ("person enters (ear ON)",  "__PERSON_ON__"),
    "1": ("person leaves (ear OFF)", "__PERSON_OFF__"),
}

# ------------------------------------------------------------------
# Socket.IO client
# ------------------------------------------------------------------

sio = socketio.Client(reconnection=True, reconnection_attempts=0)

@sio.event
def connect():
    print(f"[Sim] Connected to brain at {BRAIN_URL}")
    print_menu()

@sio.event
def disconnect():
    print("[Sim] Disconnected from brain.")

@sio.event
def connect_error(data):
    print(f"[Sim] Connection error: {data}")

@sio.on('state')
def on_state(data):
    devices = data.get('devices', {})
    count   = data.get('count', 0)
    print(f"[Sim] Brain state → devices={devices}  command_count={count}")

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def print_menu():
    print("\n┌─────────────────────────────────────┐")
    print("│         RPi Simulator               │")
    print("├─────────────────────────────────────┤")
    for key, (label, _) in COMMANDS.items():
        print(f"│  [{key}] {label:<33}│")
    print("│  [q] quit                           │")
    print("└─────────────────────────────────────┘")

def send_command(text, command):
    if not sio.connected:
        print("[Sim] Not connected.")
        return
    payload = {'text': text, 'command': command}
    sio.emit('command', payload)
    print(f"[Sim] Sent command: {command}  (text='{text}')")

def send_ear_control(active: bool):
    if not sio.connected:
        print("[Sim] Not connected.")
        return
    sio.emit('ear_control',    {'active': active})
    sio.emit('person_present', {'present': active})
    state = "ON" if active else "OFF"
    print(f"[Sim] Sent ear_control={state} + person_present={active}")

# ------------------------------------------------------------------
# Input loop (runs in main thread)
# ------------------------------------------------------------------

def input_loop():
    while True:
        try:
            key = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if key == '0':
            break
        elif key == 'm':
            print_menu()
        elif key in COMMANDS:
            _, code = COMMANDS[key]
            text, _ = COMMANDS[key]
            if code == "__PERSON_ON__":
                send_ear_control(True)
            elif code == "__PERSON_OFF__":
                send_ear_control(False)
            else:
                send_command(text, code)
        else:
            print(f"[Sim] Unknown key '{key}'. Press [m] to show the menu.")

    print("[Sim] Exiting...")
    if sio.connected:
        sio.disconnect()

# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", default=BRAIN_URL, help="Brain URL")
    args = parser.parse_args()
    BRAIN_URL = args.brain

    print(f"[Sim] Connecting to {BRAIN_URL} ...")
    try:
        sio.connect(BRAIN_URL)
    except Exception as e:
        print(f"[Sim] Could not connect: {e}")
        print("[Sim] Make sure brain/main.py is running first.")
        exit(1)

    input_loop()
