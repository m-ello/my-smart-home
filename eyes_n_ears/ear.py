from vosk import Model, KaldiRecognizer
import pyaudio
import json

class Ear:
    def __init__(self, wake_word, commands_dict, on_command):
        self.wake_word = wake_word
        self.COMMANDS = commands_dict
        self.on_command = on_command  # callback to synapse.py
        self.model = Model(lang="en-us")
        self.is_listening = False

    def process_command(self, text):
        text = text.lower().strip()
        for phrase, command in self.COMMANDS.items():
            if phrase in text:
                self.on_command({
                    'text': text,
                    'command': command
                })
                print(f"Command detected: {command} from '{text}'")
                return command
        return None

    def start(self):
        self.is_listening = True
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
        print("Ear started...")

        try:
            while self.is_listening:
                data = stream.read(4096, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    if self.wake_word in text:
                        command = text.split(' ', 1)[1]
                        print(f"Recognized: {command}")
                        self.process_command(command)
                else:
                    partial = json.loads(rec.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"Partial: {partial_text}", end='\r')
        except Exception as e:
            print(f"Error in ear: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Ear stopped.")

    def stop(self):
        self.is_listening = False

