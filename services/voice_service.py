from vosk import Model, KaldiRecognizer
import pyaudio
import json
from threading import Lock


class VoiceRecognitionService:
    def __init__(self, commands_dict, detected_commands, lock, name, socketio):
        """
        Initialize the voice recognition service

        Args:
            commands_dict: Dictionary mapping phrases to command codes
            detected_commands: Shared list to store detected commands
            lock: Threading lock for thread-safe operations
        """
        self.COMMANDS = commands_dict
        self.detected_commands = detected_commands
        self.lock = lock
        self.model = Model(lang="en-us")
        self.is_listening = False
        self.name = name
        self.socketio = socketio

    def process_command(self, text):
        """Process recognized text and check for commands"""
        text = text.lower().strip()

        for phrase, command in self.COMMANDS.items():
            if phrase in text:
                with self.lock:
                    self.detected_commands.append({
                        'text': text,
                        'command': command
                    })
                    self.socketio.emit('command', {
                        'commands': self.detected_commands,
                        'count': len(self.detected_commands)
                    })
                print(f"Command detected: {command} from '{text}'")
                return command
        return None

    def voice_recognition_thread(self):
        """Background thread for continuous voice recognition"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000
        )
        stream.start_stream()
        grammar = json.dumps(list(self.COMMANDS.keys()))
        rec = KaldiRecognizer(self.model, 16000, grammar)

        print("Voice recognition started...")

        try:
            while self.is_listening:
                data = stream.read(4096, exception_on_overflow=False)

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    if self.name in text:
                        command = text.split(' ',1)[1]
                        print(f"Recognized: {command}")
                        self.process_command(command)
                else:
                    partial = json.loads(rec.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"Partial: {partial_text}", end='\r')

        except Exception as e:
            print(f"Error in voice recognition: {e}")

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Voice recognition stopped.")

    def start(self):
        """Start listening"""
        self.is_listening = True
        self.socketio.emit('status',{'listening': True})

    def stop(self):
        """Stop listening"""
        self.is_listening = False
        self.socketio.emit('status',{'listening': False})

    def is_active(self):
        """Check if currently listening"""
        return self.is_listening
