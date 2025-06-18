let ws;
let messageCallback = () => {};

export function setMessageCallback(cb) {
  messageCallback = cb;
}

export function startWebSocket(onReady, onStreamReady) {
  ws = new WebSocket('ws://127.0.0.1:5003/transcribe');

  ws.onopen = () => {
    console.log('WebSocket opened');
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        onReady(ws);
        onStreamReady(stream);
      })
      .catch(err => {
        console.error('Microphone access denied:', err);
      });
  };

  ws.onmessage = (event) => {
    if (messageCallback) {
      messageCallback(event.data);
    }
  };

  ws.onclose = () => {
    console.log('WebSocket closed');
  };

  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
  };
}

export function stopWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
}
