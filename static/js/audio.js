document.addEventListener('DOMContentLoaded', function() {
    const audioElement = document.getElementById('background-music');
    const toggleButton = document.getElementById('toggle-audio');
    const volumeControl = document.getElementById('volume-control');
    const bars = document.querySelectorAll('.bar');
    
    // Set initial volume
    audioElement.volume = volumeControl.value;
    
    // Toggle play/pause
    toggleButton.addEventListener('click', function() {
        if (audioElement.paused) {
            audioElement.play();
            toggleButton.textContent = 'Pause Music';
            animateBars(true);
        } else {
            audioElement.pause();
            toggleButton.textContent = 'Play Music';
            animateBars(false);
        }
    });
    
    // Volume control
    volumeControl.addEventListener('input', function() {
        audioElement.volume = this.value;
    });
    
    // Function to control bar animations
    function animateBars(isPlaying) {
        bars.forEach(bar => {
            if (isPlaying) {
                bar.style.animationPlayState = 'running';
            } else {
                bar.style.animationPlayState = 'paused';
            }
        });
    }
    
    // Initialize bars as paused
    animateBars(false);
});
