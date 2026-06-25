import threading
from ear import Ear
from eye import Eye
from nerve import Nerve

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BRAIN_URL = "http://10.42.0.1:5000"
MJPEG_PORT = 8000
WAKE_WORD = "siri"

COMMANDS = {

    "lights on":  "LIGHTS_ON",
    "lights off": "LIGHTS_OFF",
    "fan on":     "FAN_ON",
    "fan off":    "FAN_OFF",
    "music on":   "MUSIC_ON",
    "pause music":"PAUSE_MUSIC",
    "music off":  "MUSIC_OFF"
}

# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    nerve = Nerve(brain_url=BRAIN_URL, mjpeg_port=MJPEG_PORT)

    ear = Ear(
        wake_word=WAKE_WORD,
        commands_dict=COMMANDS,
        on_command=nerve.send_command
    )

    eye = Eye(on_frame=nerve.send_frame)

    # Ear is controlled by the brain via Socket.IO
    # brain/vision.py emits 'ear_control' when occupancy changes
    ear_thread = None
    @nerve.sio.on('ear_control')
    def handle_ear_control(data):
        nonlocal ear_thread
        active = data.get('active', False)
        if active and not ear.is_listening:
            print("[Main] Brain activated ear.")
            ear.is_listening = True
            ear_thread = threading.Thread(target=ear.start, daemon=True)
            ear_thread.start()
        elif not active and ear.is_listening:
            print("[Main] Brain deactivated ear.")
            ear.is_listening = False

    nerve.start()

    eye_thread = threading.Thread(target=eye.start, daemon=True)
    eye_thread.start()

    print("[Main] eyes_n_ears is running. Press Ctrl+C to stop.")

    try:
        eye_thread.join()
        ear_thread.join()
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
        eye.stop()
        ear.stop()
        nerve.stop()
        print("[Main] Goodbye.")


if __name__ == "__main__":
    main()
