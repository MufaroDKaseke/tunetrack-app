document.addEventListener('DOMContentLoaded', function() {
    const audioPlayer = document.getElementById('audio-player');
    const playBtn = document.getElementById('play-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const nowPlayingTitle = document.getElementById('now-playing-title');
    const progressBar = document.querySelector('.progress');
    const currentTimeEl = document.getElementById('current-time');
    const durationEl = document.getElementById('duration');
    const visualizerBars = document.querySelectorAll('#visualizer .bar');
    const playButtons = document.querySelectorAll('.play-button');
    const songRows = document.querySelectorAll('.songs-table tr[data-song]');
    
    let isPlaying = false;
    let currentSongIndex = -1;
    const songs = Array.from(songRows).map(row => ({
        url: row.dataset.song,
        name: row.dataset.songName
    }));

    // Initialize with animation paused
    visualizerBars.forEach(bar => {
        bar.style.animationPlayState = 'paused';
        // Random heights for aesthetics
        bar.style.animationDuration = (Math.random() * 1.5 + 0.5) + 's';
    });

    // Format time in minutes and seconds
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Update progress bar and time
    audioPlayer.addEventListener('timeupdate', () => {
        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
        progressBar.style.width = `${progress}%`;
        currentTimeEl.textContent = formatTime(audioPlayer.currentTime);
        
        // Animate visualizer bars based on play state
        if (!audioPlayer.paused) {
            visualizerBars.forEach(bar => {
                bar.style.animationPlayState = 'running';
            });
        }
    });

    // Update duration when metadata is loaded
    audioPlayer.addEventListener('loadedmetadata', () => {
        durationEl.textContent = formatTime(audioPlayer.duration);
    });

    // Song ended - play next
    audioPlayer.addEventListener('ended', () => {
        playNextSong();
    });

    // Play/Pause toggle
    playBtn.addEventListener('click', () => {
        if (isPlaying) {
            pauseSong();
        } else {
            if (currentSongIndex === -1 && songs.length > 0) {
                playSong(0);
            } else {
                resumeSong();
            }
        }
    });

    // Previous song
    prevBtn.addEventListener('click', () => {
        playPrevSong();
    });

    // Next song
    nextBtn.addEventListener('click', () => {
        playNextSong();
    });

    // Play selected song
    playButtons.forEach((button, index) => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            playSong(index);
        });
    });

    // Row click to play song
    songRows.forEach((row, index) => {
        row.addEventListener('click', () => {
            playSong(index);
        });
    });

    // Play song function
    function playSong(index) {
        if (index >= 0 && index < songs.length) {
            // Reset previous active row
            if (currentSongIndex !== -1) {
                songRows[currentSongIndex].classList.remove('active');
            }
            
            currentSongIndex = index;
            audioPlayer.src = songs[index].url;
            nowPlayingTitle.textContent = songs[index].name;
            
            // Mark current row as active
            songRows[currentSongIndex].classList.add('active');
            
            audioPlayer.play()
                .then(() => {
                    isPlaying = true;
                    playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                    
                    // Start visualizer animation
                    visualizerBars.forEach(bar => {
                        bar.style.animationPlayState = 'running';
                    });
                })
                .catch(err => console.error('Error playing audio:', err));
        }
    }

    // Pause song
    function pauseSong() {
        audioPlayer.pause();
        isPlaying = false;
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
        
        // Pause visualizer animation
        visualizerBars.forEach(bar => {
            bar.style.animationPlayState = 'paused';
        });
    }

    // Resume song
    function resumeSong() {
        audioPlayer.play()
            .then(() => {
                isPlaying = true;
                playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                
                // Resume visualizer animation
                visualizerBars.forEach(bar => {
                    bar.style.animationPlayState = 'running';
                });
            })
            .catch(err => console.error('Error resuming audio:', err));
    }

    // Play next song
    function playNextSong() {
        let nextIndex = currentSongIndex + 1;
        if (nextIndex >= songs.length) {
            nextIndex = 0; // Loop back to the first song
        }
        playSong(nextIndex);
    }

    // Play previous song
    function playPrevSong() {
        let prevIndex = currentSongIndex - 1;
        if (prevIndex < 0) {
            prevIndex = songs.length - 1; // Loop to the last song
        }
        playSong(prevIndex);
    }
});
