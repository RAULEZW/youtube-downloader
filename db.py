import sqlite3
import threading

_lock = threading.Lock()
_conn = None

def get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect('downloads.db', check_same_thread=False)
        _conn.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT,
                status TEXT,
                progress INTEGER,
                message TEXT,
                filename TEXT,
                error TEXT
            )
        ''')
        _conn.commit()
    return _conn

def insert_download(download_id, url):
    conn = get_conn()
    with _lock:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO downloads (id, url, status, progress, message) VALUES (?, ?, ?, ?, ?)",
            (download_id, url, 'starting', 0, 'Initializing download...')
        )
        conn.commit()

def update_download(download_id, **kwargs):
    conn = get_conn()
    with _lock:
        cursor = conn.cursor()
        columns = ', '.join(f"{k}=?" for k in kwargs.keys())
        values = list(kwargs.values()) + [download_id]
        sql = f"UPDATE downloads SET {columns} WHERE id=?"
        cursor.execute(sql, values)
        conn.commit()

def get_download(download_id):
    conn = get_conn()
    with _lock:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM downloads WHERE id=?", (download_id,))
        row = cursor.fetchone()
        if row:
            keys = ['id', 'url', 'status', 'progress', 'message', 'filename', 'error']
            return dict(zip(keys, row))
        return None