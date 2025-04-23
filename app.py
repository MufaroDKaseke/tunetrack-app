from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import subprocess
import tempfile
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import numpy as np
from scipy.io import wavfile
import hashlib
from dejavu import Dejavu
from dejavu.logic.recognizer import FileRecognizer
from dejavu.logic.decoder import get_audio_name_from_path
from dejavu.database.mysql import MySQLDatabase
from dejavu.config.settings import DEJAVU_DEFAULT_CONFIG
import traceback

app = Flask(__name__)
app.secret_key = 'tunetrack_secret_key'  # for session management
app.config['UPLOAD_FOLDER'] = 'static/songs'
app.config['SAMPLE_FOLDER'] = 'static/samples'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the uploads folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAMPLE_FOLDER'], exist_ok=True)

# Path to the song stats and fingerprint database JSON files
SONG_STATS_FILE = 'song_stats.json'
FINGERPRINT_DB_FILE = 'fingerprint_db.json'

# Configure Dejavu
DEJAVU_CONFIG = DEJAVU_DEFAULT_CONFIG
# Update database settings as needed
DEJAVU_CONFIG["database"] = {
    "host": "127.0.0.1",
    "user": "dejavu",
    "password": "dejavu",
    "database": "dejavu"
}

# Initialize Dejavu
djv = None
try:
    djv = Dejavu(DEJAVU_CONFIG)
except Exception as e:
    print(f"Failed to initialize Dejavu: {e}")
    print(traceback.format_exc())

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_song_stats():
    if os.path.exists(SONG_STATS_FILE):
        with open(SONG_STATS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_song_stats(stats):
    with open(SONG_STATS_FILE, 'w') as f:
        json.dump(stats, f)

def get_song_list():
    songs = []
    stats = get_song_stats()
    
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            song_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            song_info = {
                'filename': filename,
                'name': os.path.splitext(filename)[0],
                'path': song_path.replace('\\', '/'),
                'url': url_for('static', filename=f'songs/{filename}'),
                'plays': stats.get(filename, {}).get('plays', 0),
                'uploaded': stats.get(filename, {}).get('uploaded', 'Unknown')
            }
            songs.append(song_info)
    
    # Sort by plays in descending order
    songs.sort(key=lambda x: x['plays'], reverse=True)
    return songs

def get_fingerprint_db():
    if os.path.exists(FINGERPRINT_DB_FILE):
        with open(FINGERPRINT_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_fingerprint_db(db):
    with open(FINGERPRINT_DB_FILE, 'w') as f:
        json.dump(db, f)

def extract_fingerprint(audio_path):
    """Extract audio fingerprint using Dejavu and log output to file"""
    # Create a unique log filename
    log_filename = f"fingerprint_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    log_path = os.path.join('logs', log_filename)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Log the operation
    with open(log_path, 'w') as log_file:
        log_file.write(f"Fingerprinting file: {audio_path}\n")
        
        try:
            if djv is None:
                log_file.write("Error: Dejavu is not initialized\n")
                return {"filename": os.path.basename(audio_path), "fingerprint": None}
            
            # Get song name from path
            song_name = os.path.splitext(os.path.basename(audio_path))[0]
            
            # Add song fingerprint to Dejavu
            djv.fingerprint_file(audio_path, song_name)
            
            # Create a fingerprint record
            fingerprint_data = {
                "filename": os.path.basename(audio_path),
                "fingerprint": song_name,  # Use song name as identifier
                "dejavu_id": song_name
            }
            
            log_file.write(f"Fingerprinting successful: {song_name}\n")
            return fingerprint_data
            
        except Exception as e:
            log_file.write(f"Error during fingerprinting: {e}\n")
            log_file.write(traceback.format_exc())
            return {"filename": os.path.basename(audio_path), "fingerprint": None}

def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format using ffmpeg"""
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_file, "-ar", "44100", "-ac", "2", output_file],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.SubprocessError as e:
        print(f"Error converting audio: {e}")
        return False

def calculate_fingerprint_similarity(fp1, fp2):
    """For Dejavu, we rely on its confidence score rather than binary comparison"""
    # This function is mainly for backwards compatibility
    # Dejavu provides its own confidence score during recognition
    return 1.0 if fp1.get('dejavu_id') == fp2.get('dejavu_id') else 0.0

def match_audio_sample(sample_path):
    """Match an audio sample against the Dejavu database"""
    if djv is None:
        print("Error: Dejavu is not initialized")
        return None
        
    try:
        # Use Dejavu to recognize the file
        results = djv.recognize(FileRecognizer, sample_path)
        
        if results and results["matches"]:
            # Get the best match
            best_match = results["matches"][0]
            song_name = best_match["song_name"]
            confidence = best_match["confidence"]
            
            # Find the filename corresponding to this song
            song_files = os.listdir(app.config['UPLOAD_FOLDER'])
            song_id = None
            
            for filename in song_files:
                if os.path.splitext(filename)[0] == song_name:
                    song_id = filename
                    break
            
            if not song_id:
                print(f"Song name {song_name} found in database but no file exists")
                song_id = f"{song_name}.mp3"  # Default filename
                
            return {
                'song_id': song_id,
                'confidence': confidence / 100.0  # Normalize to 0-1 range
            }
        
        return None
        
    except Exception as e:
        print(f"Error during audio matching: {e}")
        print(traceback.format_exc())
        return None

def fingerprint_all_songs():
    """Generate fingerprints for all songs in the library using Dejavu"""
    if djv is None:
        print("Error: Dejavu is not initialized")
        return 0
        
    songs = get_song_list()
    fingerprint_db = get_fingerprint_db()
    count = 0
    
    for song in songs:
        filename = song['filename']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if filename not in fingerprint_db:
            fingerprint = extract_fingerprint(filepath)
            if fingerprint and fingerprint.get('fingerprint'):
                fingerprint_db[filename] = fingerprint
                count += 1
    
    save_fingerprint_db(fingerprint_db)
    return count

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Simple validation - in a real app you'd validate against a database
        if request.form['username'] == 'demo' and request.form['password'] == 'password':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    songs = get_song_list()
    # Get stats for total matches
    total_matches = sum(song['plays'] for song in songs)
    most_matched = songs[0] if songs else None
    
    return render_template('dashboard.html', 
                          songs=songs, 
                          total_matches=total_matches,
                          most_matched=most_matched)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Check if a file was submitted
        if 'song' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file = request.files['song']
        
        # If user submits without selecting a file
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Add/update the song info in stats
            stats = get_song_stats()
            if filename not in stats:
                stats[filename] = {
                    'plays': 0, 
                    'uploaded': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            save_song_stats(stats)
            
            # Generate fingerprint for the new song
            fingerprint = extract_fingerprint(filepath)
            if fingerprint:
                db = get_fingerprint_db()
                db[filename] = fingerprint
                save_fingerprint_db(db)
                flash('Song uploaded and fingerprinted successfully!')
            else:
                flash('Song uploaded but fingerprinting failed. Please try again.')
                
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type. Allowed types are mp3, wav, ogg.')
            
    return render_template('upload.html')

@app.route('/play/<filename>')
def play_song(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # Increment play count
    stats = get_song_stats()
    if filename in stats:
        stats[filename]['plays'] += 1
    else:
        stats[filename] = {
            'plays': 1, 
            'uploaded': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    save_song_stats(stats)
    
    return redirect(url_for('static', filename=f'songs/{filename}'))

@app.route('/sample', methods=['GET', 'POST'])
def sample():
    """Handle audio sample submission for matching"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    result = None
    match_details = None
    
    if request.method == 'POST':
        # Check if recording or file upload
        if 'sample' in request.files:
            file = request.files['sample']
            
            if file and allowed_file(file.filename):
                # Save the sample file
                filename = secure_filename(f"sample_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
                sample_path = os.path.join(app.config['SAMPLE_FOLDER'], filename)
                file.save(sample_path)
                
                # Convert to WAV if needed
                if not sample_path.lower().endswith('.wav'):
                    wav_path = os.path.splitext(sample_path)[0] + '.wav'
                    if convert_to_wav(sample_path, wav_path):
                        sample_path = wav_path
                
                # Match the sample against the database
                match_result = match_audio_sample(sample_path)
                
                if match_result:
                    song_id = match_result['song_id']
                    confidence = match_result['confidence']
                    
                    # Get song details
                    stats = get_song_stats()
                    if song_id in stats:
                        # Increment play count
                        stats[song_id]['plays'] += 1
                        save_song_stats(stats)
                    
                    # Get song info for display
                    song_name = os.path.splitext(song_id)[0]
                    result = f"Match found: {song_name} (Confidence: {confidence:.2%})"
                    
                    # Get additional song details
                    match_details = {
                        'filename': song_id,
                        'name': song_name,
                        'confidence': f"{confidence:.2%}",
                        'plays': stats.get(song_id, {}).get('plays', 1)
                    }
                else:
                    result = "No match found. Try with a different sample or longer duration."
            else:
                result = "Invalid file. Please upload a supported audio format."
                
    # Get fingerprint stats
    fingerprint_count = len(get_fingerprint_db())
    
    return render_template('sample.html', 
                          result=result, 
                          match_details=match_details,
                          fingerprint_count=fingerprint_count)

@app.route('/api/record-match', methods=['POST'])
def record_match():
    """API endpoint for recording matches from browser audio recording"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or 'sample_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400
    
    # Save audio data to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Process base64 encoded audio data (implementation depends on how audio is sent)
        # ...

        # Match the sample
        match_result = match_audio_sample(temp_path)
        
        if match_result:
            song_id = match_result['song_id']
            confidence = match_result['confidence']
            
            # Increment play count
            stats = get_song_stats()
            if song_id in stats:
                stats[song_id]['plays'] += 1
                save_song_stats(stats)
            
            song_name = os.path.splitext(song_id)[0]
            return jsonify({
                'success': True,
                'match': {
                    'song_id': song_id,
                    'name': song_name,
                    'confidence': confidence
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No match found'
            })
            
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.route('/fingerprint-all', methods=['POST'])
def fingerprint_all():
    """Force fingerprinting of all songs in the library"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    count = fingerprint_all_songs()
    flash(f'Successfully fingerprinted {count} songs')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Initialize database on startup
    if djv is None:
        print("WARNING: Dejavu could not be initialized. Fingerprinting will not work.")
    app.run(host='0.0.0.0', port=80, debug=True)
