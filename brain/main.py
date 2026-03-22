import json
import queue
from functools import partial
from flask import Flask, render_template, request, url_for, jsonify
from threading import Thread, Lock
from services.voice_service import VoiceRecognitionService
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

detected_commands = []
lock = Lock()

name = "vadim"
COMMANDS = {
    name + " lights on": "LIGHTS_ON",
    name + " lights off": "LIGHTS_OFF",
    name + " play music": "MUSIC_ON",
    name + " pause music": "MUSIC_PAUSE",
    name + " stop music": "MUSIC_OFF"
}

voice_service = VoiceRecognitionService(COMMANDS, detected_commands, lock, name, socketio)
voice_thread = None

@app.route('/',methods=['GET'])
def main():
    return render_template('index.html')


@app.route('/commands', methods=['GET'])
def get_commands():
    """API endpoint to retrieve recognized commands"""
    with lock:
        return jsonify({
            'commands': detected_commands,
            'count': len(detected_commands)
        })


@app.route('/commands/clear', methods=['POST'])
def clear_commands():
    """Clear the command history"""
    with lock:
        detected_commands.clear()
    return jsonify({'status': 'cleared'})


@app.route('/listening/start', methods=['POST'])
def start_listening():
    """Start voice recognition"""
    global voice_thread

    if not voice_service.is_active():
        voice_service.start()
        voice_thread = Thread(target=voice_service.voice_recognition_thread, daemon=True)
        voice_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already running'})


@app.route('/listening/stop', methods=['POST'])
def stop_listening():
    """Stop voice recognition"""

    if voice_service.is_active():
        voice_service.stop()
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not running'})


@app.route('/listening/status', methods=['GET'])
def listening_status():
    """Check if voice recognition is active"""
    return jsonify({'listening': voice_service.is_active()})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
