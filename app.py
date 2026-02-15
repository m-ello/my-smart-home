from flask import Flask, render_template, request,url_for
from threading import Thread, Lock
from vosk import Model,KaldiRecognizer

app = Flask(__name__)

commands = []
lock = Lock()

COMMANDS = {
    "lights on": "LIGHTS_ON",
    "lights off": "LIGHTS_OFF",
    "play music": "MUSIC_ON",
    "pause": "MUSIC_PAUSE",
    "stop music": "MUSIC_OFF"
}

model = Model()


@app.route('/',methods=['GET'])
def main():
    if request.method == 'GET':
        return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
