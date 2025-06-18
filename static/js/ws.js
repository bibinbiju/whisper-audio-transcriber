let ws;
export function connectWebSocket(onMessage) {
  ws = new WebSocket('ws://127.0.0.1:5003/transcribe');
  ws.onopen = () => console.log('WebSocket opened');
  ws.onmessage = event => onMessage(event.data);
  ws.onclose = () => console.log('WebSocket closed');
}

export function sendAudio(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(data);
  }
}

export function disconnectWebSocket() {
  if (ws) ws.close();
}
