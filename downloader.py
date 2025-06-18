import os
import subprocess
import logging
import yt_dlp
import re

class YouTubeDownloader:
    def __init__(self, download_folder):
        self.download_folder = download_folder

    def download(self, url, format_type='mp4', progress_callback=None):
        try:
            if progress_callback:
                progress_callback({
                    'status': 'downloading',
                    'progress': 10,
                    'message': 'Fetching video information...'
                })

            ydl_opts = {
                'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                'format': 'best' if format_type == 'mp4' else 'bestaudio',
                'noplaylist': True,
                'progress_hooks': [lambda d: self._progress_hook(d, progress_callback)]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = self.sanitize_filename(info.get('title', 'video'))

                if progress_callback:
                    progress_callback({
                        'status': 'downloading',
                        'progress': 20,
                        'message': f'Starting download of: {video_title}'
                    })

                ydl.download([url])

                # Find the real downloaded file
                downloaded_file = self._find_downloaded_file(video_title)

                if not downloaded_file:
                    raise Exception("Download completed, but file not found")

                if format_type == 'mp3':
                    if progress_callback:
                        progress_callback({
                            'status': 'converting',
                            'progress': 95,
                            'message': 'Converting to MP3...'
                        })
                    output_file = self.convert_to_mp3(downloaded_file, video_title)
                    if os.path.exists(output_file):
                        try:
                            os.remove(downloaded_file)
                        except:
                            pass
                        return os.path.basename(output_file)

                return os.path.basename(downloaded_file)

        except Exception as e:
            logging.error(f"Download error: {str(e)}")
            raise Exception(f"Download failed: {str(e)}")

    def _find_downloaded_file(self, video_title):
        """Find the completed file by title, skipping .part and temp files"""
        for file in os.listdir(self.download_folder):
            if video_title in file and not file.endswith('.part'):
                return os.path.join(self.download_folder, file)

        # Fallback: most recent completed file
        files = [
            os.path.join(self.download_folder, f)
            for f in os.listdir(self.download_folder)
            if not f.endswith('.part')
        ]
        return max(files, key=os.path.getctime) if files else None

    def _progress_hook(self, d, callback):
        if callback and d['status'] == 'downloading':
            try:
                if 'total_bytes' in d and d['total_bytes']:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif '_percent_str' in d:
                    percent = float(d['_percent_str'].replace('%', ''))
                else:
                    percent = 50
                callback({
                    'status': 'downloading',
                    'progress': min(int(percent), 90),
                    'message': f'Downloading video... {percent:.1f}%'
                })
            except:
                pass

    def convert_to_mp3(self, input_file, title):
        try:
            output_file = os.path.join(self.download_folder, f"{title}.mp3")
            cmd = [
                'ffmpeg', '-i', input_file,
                '-vn', '-acodec', 'libmp3lame',
                '-ab', '192k', '-ar', '44100',
                '-y', output_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"FFmpeg error: {result.stderr}")
                raise Exception("Audio conversion failed")
            return output_file
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg.")
        except Exception as e:
            logging.error(f"Conversion error: {str(e)}")
            raise Exception(f"Conversion failed: {str(e)}")

    def sanitize_filename(self, filename):
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename)
        return filename.strip()[:50]