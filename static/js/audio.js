let recorder, audioContext, sourceNode, analyser, animationId;

function startRecording(onData) {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      audioContext = new AudioContext();
      sourceNode = audioContext.createMediaStreamSource(stream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      sourceNode.connect(analyser);
      visualize();

      recorder = new RecordRTC(stream, {
        type: 'audio',
        mimeType: 'audio/wav',
        recorderType: StereoAudioRecorder,
        desiredSampRate: 16000,
        numberOfAudioChannels: 1,
        timeSlice: 500,
        ondataavailable: function(blob) {
          const reader = new FileReader();
          reader.onloadend = function () {
            const base64String = reader.result.split(',')[1]; // remove "data:audio/wav;base64," part
            onData(base64String); // send to server or handler
          };
          reader.readAsDataURL(blob); // this converts blob to base64
        }
      });
      recorder.startRecording();
    });
}

function stopRecording() {
  if (recorder) recorder.stopRecording();
  if (animationId) cancelAnimationFrame(animationId);
}

function isSilent(samples, threshold = 0.01) {
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    let val = samples[i] / 32768;
    sum += val * val;
  }
  return Math.sqrt(sum / samples.length) < threshold;
}

function visualize() {
  const canvas = document.getElementById('visualizer');
  const ctx = canvas.getContext('2d');
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    animationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const barWidth = canvas.width / bufferLength;
    for (let i = 0; i < bufferLength; i++) {
      const barHeight = dataArray[i];
      ctx.fillStyle = '#0f0';
      ctx.fillRect(i * barWidth, canvas.height - barHeight, barWidth, barHeight);
    }
  }
  draw();
}

export { startRecording, stopRecording };
