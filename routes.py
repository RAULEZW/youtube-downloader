import os
import re
import redis
import logging
import uuid
from rq import Queue
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from app import app
from downloader import YouTubeDownloader
from db import insert_download, update_download, get_download

# ✅ Redis connection (works locally and on Render)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
conn = redis.from_url(redis_url)
q = Queue("default", connection=conn)

# ✅ Helper to check valid YouTube links
def is_valid_youtube_url(url):
    pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')
    return bool(pattern.match(url))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url', '').strip()
    format_type = request.form.get('format', 'mp4')

    if not url:
        flash('Please enter a YouTube URL', 'error')
        return redirect(url_for('index'))
    
    if not is_valid_youtube_url(url):
        flash('Please enter a valid YouTube URL', 'error')
        return redirect(url_for('index'))
    
    download_id = str(uuid.uuid4())
    insert_download(download_id, url)

    downloader = YouTubeDownloader(app.config['UPLOAD_FOLDER'])
    q.enqueue(download_worker, downloader, url, format_type, download_id)

    return render_template('download.html', download_id=download_id)

@app.route('/progress/<download_id>')
def get_progress(download_id):
    data = get_download(download_id)
    if data:
        return jsonify(data)
    else:
        return jsonify({'status': 'not_found', 'error': 'Download not found'}), 404

@app.route('/download_file/<download_id>')
def download_file(download_id):
    data = get_download(download_id)
    if not data or data['status'] != 'completed' or not data['filename']:
        flash('File not ready for download', 'error')
        return redirect(url_for('index'))
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], data['filename'])
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    return send_file(file_path, as_attachment=True, download_name=data['filename'])

def download_worker(downloader, url, format_type, download_id):
    def progress_callback(progress_info):
        update_download(download_id, **progress_info)

    try:
        update_download(download_id, status='downloading', progress=5, message='Starting download...')
        filename = downloader.download(url, format_type, progress_callback)
        update_download(download_id, status='completed', progress=100, message='Download completed!', filename=filename)
    except Exception as e:
        logging.error(f"Download worker error for {download_id}: {str(e)}")
        update_download(download_id, status='error', error=str(e), message=f'Download failed: {str(e)}')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {str(error)}")
    return render_template('index.html'), 500