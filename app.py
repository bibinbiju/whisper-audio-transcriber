from flask import Flask, render_template
from flask_sockets import Sockets
from werkzeug.routing import Rule
import whisper
import base64
import tempfile
import traceback
import numpy as np
import os
import ffmpeg

app = Flask(__name__)
sockets = Sockets(app)

# Load Whisper model
model = whisper.load_model('base.en')

# Function to detect silence
def is_silent(audio, threshold=0.001):
    rms = np.sqrt(np.mean(audio**2))
    print(f"[Debug] RMS: {rms:.6f}")
    return rms < threshold

# Convert webm bytes to WAV and return audio tensor
def process_wav_bytes(webm_bytes: bytes, sample_rate: int = 16000):
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(webm_bytes)
        temp_file.flush()
        temp_file_path = temp_file.name

    wav_path = temp_file_path + ".wav"

    try:
        # Convert using ffmpeg-python
        ffmpeg.input(temp_file_path).output(
            wav_path,
            format='wav',
            ar=sample_rate,
            ac=1,
            loglevel='quiet'
        ).run(overwrite_output=True)

        audio = whisper.load_audio(wav_path, sr=sample_rate)
        return audio

    except Exception as e:
        traceback.print_exc()
        print("[Error] Failed to convert/process audio.")
        return None

    finally:
        os.remove(temp_file_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

# WebSocket transcription handler
def transcribe_socket(ws):
    while not ws.closed:
        try:
            message = ws.receive()
            if not message:
                continue

            print(f"[Received] {len(message)} bytes")

            if isinstance(message, str):
                try:
                    message = base64.b64decode(message, validate=True)
                except base64.binascii.Error:
                    print("[Warning] Invalid base64 data received, skipping...")
                    continue

            audio = process_wav_bytes(message)
            if audio is None:
                ws.send("<ERROR: Audio conversion failed>")
                continue

            audio = whisper.pad_or_trim(audio)

            if is_silent(audio):
                print("[Info] Silent audio detected, skipping transcription.")
                ws.send("")  # Send empty or skip
                continue

            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            options = whisper.DecodingOptions(language='en', fp16=False)
            result = whisper.decode(model, mel, options)
            text = result.text.strip()

            print(f"[Transcribed] {text}")
            ws.send(text if text else "<NO SPEECH DETECTED>")

        except Exception as e:
            traceback.print_exc()
            ws.send("<UNKNOWN SAMPLE>")
            ws.send("[Error] Failed to process audio.")

# Register the websocket endpoint
sockets.url_map.add(Rule('/transcribe', endpoint=transcribe_socket, websocket=True))

# Basic index route
@app.route('/')
def index():
    return render_template('index.html')

# Start server
if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    print("Server running on ws://127.0.0.1:5003/transcribe")
    server = pywsgi.WSGIServer(('127.0.0.1', 5003), app, handler_class=WebSocketHandler)
    server.serve_forever()
