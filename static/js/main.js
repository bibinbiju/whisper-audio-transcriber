import { connectWebSocket, sendAudio, disconnectWebSocket } from './ws.js';
import { startRecording, stopRecording } from './audio.js';

let transcriptArea = document.getElementById('fullTranscript');
let captionArea = document.getElementById('liveCaption');
let timerSpan = document.getElementById('timer');
let startTime, timerInterval;

document.getElementById('startButton').onclick = () => {
  connectWebSocket(handleMessage);
  startRecording(sendAudio);
  startTime = Date.now();
  timerInterval = setInterval(updateTimer, 1000);
};

document.getElementById('stopButton').onclick = () => {
  disconnectWebSocket();
  stopRecording();
  clearInterval(timerInterval);
};

function handleMessage(text) {
  if(captionArea.textContent.length<= 100)
    captionArea.textContent += text;
  else
    captionArea.textContent = text;
  transcriptArea.value += text + " ";
}

function updateTimer() {
  let elapsed = Math.floor((Date.now() - startTime) / 1000);
  let mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
  let secs = String(elapsed % 60).padStart(2, '0');
  timerSpan.textContent = `${mins}:${secs}`;
}
