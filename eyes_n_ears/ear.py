from vosk import Model, KaldiRecognizer
import pyaudio
import json


class Ear:
    def __init__(self, wake_word, commands_dict, on_command):
        self.wake_word = wake_word
        self.COMMANDS = commands_dict
        self.on_command = on_command
        self.model = Model(lang="en-us")
        self.is_listening = False
        self.sample_rate = 44100

    def process_command(self, text):
        """Process recognized text only if wake word is present."""
        text = text.lower().strip()
        words = text.split()

        if not words or words[0] != self.wake_word:
            return None

        for phrase, command in self.COMMANDS.items():
            if phrase in text:
                self.on_command({
                    'text': text,
                    'command': command
                })
                print(f"[EAR] Command detected: {command} from '{text}'")
                return command

        print(f"[EAR] Wake word detected but no known command in: '{text}'")
        return None

    def start(self):
        self.is_listening = True
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=4096
        )
        stream.start_stream()

        # Single grammar: wake word + all command phrases
        full_grammar = json.dumps([self.wake_word] + list(self.COMMANDS.keys()))
        rec = KaldiRecognizer(self.model, self.sample_rate, full_grammar)

        print("[EAR] Listening...")

        try:
            while self.is_listening:
                data = stream.read(4096, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '')
                    if text:
                        print(f"[EAR] Heard: '{text}'")
                        self.process_command(text)
                else:
                    partial = json.loads(rec.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"[EAR] Partial: {partial_text}", end='\r')
        except Exception as e:
            print(f"[EAR] Error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("[EAR] Stopped.")

    def stop(self):
        self.is_listening = False
