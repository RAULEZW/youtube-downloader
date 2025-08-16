import os
import re
import logging
import uuid
import threading
from flask import (
    render_template,
    request,
    jsonify,
    send_file,
    flash,
    redirect,
    url_for,
    make_response
)
from app import app
from downloader import YouTubeDownloader
from db import insert_download, update_download, get_download

# --- Helpers ---

def is_valid_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL."""
    pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')
    return bool(pattern.match(url))

def with_ngrok_headers(response):
    """Attach ngrok skip-warning headers to the response."""
    if not hasattr(response, 'headers'):
        response = make_response(response)
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# --- Routes ---

@app.route('/')
def index():
    """Home page."""
    return with_ngrok_headers(render_template('index.html'))

@app.route('/download', methods=['POST'])
def download_video():
    """Handle video download request."""
    url = request.form.get('url', '').strip()
    format_type = request.form.get('format', 'mp4').lower()

    if not url:
        flash('Please enter a YouTube URL', 'error')
        return redirect(url_for('index'))

    if not is_valid_youtube_url(url):
        flash('Please enter a valid YouTube URL', 'error')
        return redirect(url_for('index'))

    download_id = str(uuid.uuid4())
    insert_download(download_id, url)

    downloader = YouTubeDownloader(app.config['UPLOAD_FOLDER'])

    # Run download in a background thread
    thread = threading.Thread(
        target=download_worker,
        args=(downloader, url, format_type, download_id),
        daemon=True
    )
    thread.start()

    # Immediately return download page
    return with_ngrok_headers(render_template('download.html', download_id=download_id))

@app.route('/progress/<download_id>')
def get_progress(download_id):
    """Return download progress."""
    data = get_download(download_id)
    if data:
        return jsonify(data)
    return jsonify({'status': 'not_found', 'error': 'Download not found'}), 404

@app.route('/download_file/<download_id>')
def download_file(download_id):
    """Serve completed file for download."""
    data = get_download(download_id)
    if not data or data['status'] != 'completed' or not data.get('filename'):
        flash('File not ready for download', 'error')
        return redirect(url_for('index'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], data['filename'])
    if not os.path.exists(file_path):
        flash('File not found on server', 'error')
        return redirect(url_for('index'))

    return send_file(file_path, as_attachment=True, download_name=data['filename'])

# --- Background Worker ---

def download_worker(downloader, url, format_type, download_id):
    """Handles downloading and progress updates in background."""
    def progress_callback(progress_info):
        update_download(download_id, **progress_info)

    try:
        update_download(download_id, status='downloading', progress=5, message='Starting download...')
        filename = downloader.download(url, format_type, progress_callback)
        update_download(download_id, status='completed', progress=100, message='Download completed!', filename=filename)
    except Exception as e:
        logging.error(f"Download worker error [{download_id}]: {str(e)}")
        update_download(download_id, status='error', error=str(e), message=f'Download failed: {str(e)}')

# --- Error Handlers ---

@app.errorhandler(404)
def not_found_error(error):
    return with_ngrok_headers(render_template('index.html')), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal Server Error: {str(error)}")
    return with_ngrok_headers(render_template('index.html')), 500
