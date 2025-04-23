from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tunetrack_secret_key'  # for session management
app.config['UPLOAD_FOLDER'] = 'static/songs'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Path to the song stats JSON file
SONG_STATS_FILE = 'song_stats.json'

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
    return render_template('dashboard.html', songs=songs)

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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Add/update the song info in stats
            stats = get_song_stats()
            if filename not in stats:
                stats[filename] = {
                    'plays': 0, 
                    'uploaded': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            save_song_stats(stats)
            
            flash('Song uploaded successfully!')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
