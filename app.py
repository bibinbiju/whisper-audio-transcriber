from flask import Flask, render_template
from flask_sockets import Sockets
from werkzeug.routing import Rule
import whisper
import tempfile
import traceback
import numpy as np
import os
import ffmpeg
import base64
import noisereduce as nr

app = Flask(__name__)
sockets = Sockets(app)

# Load Whisper model
model = whisper.load_model('tiny.en')

# Silence detection
def is_silent(audio, threshold=0.005):
    rms = np.sqrt(np.mean(audio**2))
    print(f"[Debug] RMS: {rms:.6f}")
    return rms < threshold

# Convert webm bytes to wav and load audio tensor
def process_wav_bytes(webm_bytes: bytes, sample_rate: int = 16000):
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(webm_bytes)
        temp_file.flush()
        temp_file_path = temp_file.name

    wav_path = temp_file_path + ".wav"

    try:
        # Convert to WAV using ffmpeg
        ffmpeg.input(temp_file_path).output(
            wav_path,
            format='wav',
            ar=sample_rate,
            ac=1,
            loglevel='quiet'
        ).run(overwrite_output=True)

        # Load audio as mono waveform
        audio = whisper.load_audio(wav_path, sr=sample_rate)

        # Apply noise reduction
        reduced_audio = nr.reduce_noise(y=audio, sr=sample_rate)
        return reduced_audio

    except Exception:
        traceback.print_exc()
        print("[Error] Failed to convert/process audio.")
        return None

    finally:
        os.remove(temp_file_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

# WebSocket transcription endpoint
def transcribe_socket(ws):
    while not ws.closed:
        try:
            message = ws.receive()
            if not message:
                continue

            # If message is a string, try Base64 decode
            if isinstance(message, str):
                try:
                    message = base64.b64decode(message)
                    print(f"[Info] Received Base64-encoded audio: {len(message)} bytes after decode")
                except Exception:
                    print("[Warning] Invalid Base64 string received.")
                    ws.send("<ERROR: Invalid Base64 data>")
                    continue
            else:
                print(f"[Received] {len(message)} bytes (raw binary)")

            # Process audio
            audio = process_wav_bytes(message)
            if audio is None:
                ws.send("<ERROR: Audio conversion failed>")
                continue

            audio = whisper.pad_or_trim(audio)

            if is_silent(audio):
                print("[Info] Silent audio detected, skipping transcription.")
                ws.send("")
                continue

            if len(audio) / 16000 < 1.0:
                print("[Info] Audio too short, skipping.")
                ws.send("")
                continue

            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            options = whisper.DecodingOptions(language='en', fp16=False)
            result = whisper.decode(model, mel, options)

            # Optional: Discard likely hallucinated results
            # if result.no_speech_prob > 0.5:  # adjust as needed
            #     print(f"[Info] Whisper thinks there's no speech (prob={result.no_speech_prob:.2f})")
            #     ws.send("")
            #     continue
            text = result.text.strip()
            print(f"[Transcribed] {text}")
            ws.send(text or "<NO SPEECH DETECTED>")

        except Exception:
            traceback.print_exc()
            ws.send("<ERROR>")

# WebSocket route
sockets.url_map.add(Rule('/transcribe', endpoint=transcribe_socket, websocket=True))

@app.route('/')
def index():
    return render_template('index.html')

# Run server
if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    print("Server running on ws://127.0.0.1:5003/transcribe")
    server = pywsgi.WSGIServer(('127.0.0.1', 5003), app, handler_class=WebSocketHandler)
    server.serve_forever()
