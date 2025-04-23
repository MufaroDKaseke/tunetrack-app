document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Update active tab button
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show selected tab content
            tabContents.forEach(content => {
                content.classList.add('hidden');
                if (content.id === `${tabId}-tab`) {
                    content.classList.remove('hidden');
                }
            });
        });
    });
    
    // File input display
    const sampleFileInput = document.getElementById('sampleFile');
    const fileNameDisplay = document.getElementById('file-name-display');
    
    if (sampleFileInput) {
        sampleFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileNameDisplay.textContent = this.files[0].name;
            } else {
                fileNameDisplay.textContent = 'No file selected';
            }
        });
    }
    
    // Audio recording functionality
    const recordBtn = document.getElementById('record-btn');
    const recordTimer = document.getElementById('record-timer');
    const visualizer = document.getElementById('visualizer');
    let mediaRecorder;
    let audioChunks = [];
    let startTime;
    let timerInterval;
    let audioContext;
    let analyser;
    let canvasCtx;
    
    if (recordBtn && visualizer) {
        canvasCtx = visualizer.getContext('2d');
        
        // Set up canvas size
        function setupCanvas() {
            visualizer.width = visualizer.clientWidth;
            visualizer.height = visualizer.clientHeight;
        }
        
        setupCanvas();
        window.addEventListener('resize', setupCanvas);
        
        // Draw initial empty visualizer
        drawEmptyVisualizer();
        
        recordBtn.addEventListener('click', async function() {
            if (recordBtn.classList.contains('recording')) {
                // Stop recording
                stopRecording();
            } else {
                // Start recording
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    startRecording(stream);
                } catch (err) {
                    console.error('Error accessing microphone:', err);
                    alert('Could not access your microphone. Please make sure it is connected and you have given permission.');
                }
            }
        });
    }
    
    function startRecording(stream) {
        // Set up audio context for visualization
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        // Start recording
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.addEventListener('dataavailable', event => {
            audioChunks.push(event.data);
        });
        
        mediaRecorder.addEventListener('stop', async () => {
            // Create blob from recorded chunks
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            
            // Send the audio for matching
            await sendAudioForMatching(audioBlob);
            
            // Clean up
            stream.getTracks().forEach(track => track.stop());
            if (audioContext) {
                audioContext.close();
            }
        });
        
        // Start recording
        mediaRecorder.start();
        recordBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
        recordBtn.classList.add('recording');
        
        // Start timer
        startTime = Date.now();
        updateTimer();
        timerInterval = setInterval(updateTimer, 1000);
        
        // Start visualizer
        visualize();
    }
    
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            recordBtn.innerHTML = '<i class="fas fa-microphone"></i> Start Recording';
            recordBtn.classList.remove('recording');
            
            // Stop timer
            clearInterval(timerInterval);
            
            // Show loading state
            recordBtn.disabled = true;
            recordBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Processing...';
        }
    }
    
    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        recordTimer.textContent = `${minutes}:${seconds}`;
    }
    
    function visualize() {
        if (!analyser) return;
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        const width = visualizer.width;
        const height = visualizer.height;
        
        function draw() {
            if (!analyser) return;
            
            requestAnimationFrame(draw);
            
            analyser.getByteFrequencyData(dataArray);
            
            canvasCtx.fillStyle = 'rgb(30, 30, 47)';
            canvasCtx.fillRect(0, 0, width, height);
            
            const barWidth = (width / bufferLength) * 2.5;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * height;
                
                const gradient = canvasCtx.createLinearGradient(0, height, 0, 0);
                gradient.addColorStop(0, '#7d3cff');
                gradient.addColorStop(1, '#bb5bff');
                
                canvasCtx.fillStyle = gradient;
                canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        }
        
        draw();
    }
    
    function drawEmptyVisualizer() {
        if (!canvasCtx) return;
        
        const width = visualizer.width;
        const height = visualizer.height;
        
        canvasCtx.fillStyle = 'rgb(30, 30, 47)';
        canvasCtx.fillRect(0, 0, width, height);
        
        // Draw some placeholder bars
        const barCount = 20;
        const barWidth = width / barCount - 1;
        
        for (let i = 0; i < barCount; i++) {
            const barHeight = Math.random() * 10 + 5;
            const x = i * (barWidth + 1);
            
            const gradient = canvasCtx.createLinearGradient(0, height, 0, 0);
            gradient.addColorStop(0, 'rgba(125, 60, 255, 0.3)');
            gradient.addColorStop(1, 'rgba(187, 91, 255, 0.3)');
            
            canvasCtx.fillStyle = gradient;
            canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
        }
    }
    
    async function sendAudioForMatching(audioBlob) {
        // Create form data
        const formData = new FormData();
        formData.append('sample', audioBlob, 'recording.wav');
        
        try {
            // Send the form data
            const response = await fetch(window.location.href, {
                method: 'POST',
                body: formData
            });
            
            // Reload the page to show results
            window.location.reload();
        } catch (error) {
            console.error('Error sending audio for matching:', error);
            alert('Error processing your recording. Please try again.');
            
            // Reset button state
            recordBtn.disabled = false;
            recordBtn.innerHTML = '<i class="fas fa-microphone"></i> Start Recording';
        }
    }
});
