import os
import signal
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from memory import Memory
from mind import Mind
from vision import Vision

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

memory = Memory()
mind = Mind(memory=memory, socketio=socketio)

RPI_STREAM_URL = "http://10.42.0.245:8000/stream"
vision = Vision(stream_url=RPI_STREAM_URL, memory=memory, socketio=socketio)

_shutting_down = False

# ------------------------------------------------------------------
# Receive from RPi (nerve.py)
# ------------------------------------------------------------------

@socketio.on('command')
def handle_command(payload):
    mind.process(payload)

@socketio.on('shutdown_ack')
def handle_shutdown_ack():
    """RPi confirmed shutdown — now we can safely exit."""
    print("[Brain] RPi acknowledged shutdown. Exiting.")
    _do_exit()

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/state', methods=['GET'])
def get_state():
    return jsonify({
        **memory.snapshot(),
        'devices': mind.devices
    })

@app.route('/commands/clear', methods=['POST'])
def clear_commands():
    memory.clear_commands()
    socketio.emit('command', {'commands': [], 'count': 0})
    return jsonify({'status': 'cleared'})

@app.route('/device/toggle/<name>', methods=['POST'])
def toggle_device(name):
    if name == 'lights':
        mind.devices['lights'] = not mind.devices.get('lights', False)
    elif name == 'fan':
        mind.devices['fan'] = not mind.devices.get('fan', False)
    elif name == 'music':
        mind.devices['music'] = 'on' if not mind.devices.get('music') else None
    socketio.emit('state', {'devices': mind.devices, 'commands': memory.get_commands()})
    return jsonify({'devices': mind.devices})
 
@app.route('/shutdown', methods=['POST'])
def shutdown_route():
    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({'status': 'shutting_down'})


# ------------------------------------------------------------------
# Clean shutdown
# ------------------------------------------------------------------

def _do_exit():
    """Hard-exit the process. Safe to call from any thread."""
    vision.stop()
    print("[Brain] Goodbye.")
    os._exit(0)

def _shutdown(notify_rpi=True):
    """
    Initiate shutdown sequence.
    If notify_rpi=True, emit 'shutdown' and wait for ack before exiting.
    If notify_rpi=False (e.g. RPi not connected), exit immediately.
    """
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    vision.stop()

    if notify_rpi:
        print("[Brain] Notifying RPi to shut down...")
        socketio.emit('shutdown')
        # Give RPi up to 5 seconds to ack; exit regardless after that
        threading.Timer(5.0, _do_exit).start()
    else:
        _do_exit()

def _handle_signal(sig, frame):
    print(f"\n[Brain] Signal {sig} received. Shutting down...")
    # Run shutdown in a new thread - signal handlers must return quickly
    threading.Thread(target=_shutdown, daemon=True).start()

signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == '__main__':
    vision_thread = threading.Thread(target=vision.start, daemon=True)
    vision_thread.start()

    socketio.run(app, debug=False, host='10.42.0.1', port=5000, use_reloader=False)