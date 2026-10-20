
from flask import Flask, request, jsonify, send_file
import os
import uuid
import hmac
import shutil
import subprocess
import yt_dlp
import imageio_ffmpeg

app = Flask(__name__)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

API_KEY = os.environ.get("DOWNLOAD_API_KEY", "")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

@app.get("/")
def home():
    return jsonify({"status": "ok", "service": "Youtube-Downloader"})

@app.post("/download")
def download():
    supplied_key = request.headers.get("X-API-Key", "")
    if not API_KEY or not hmac.compare_digest(supplied_key, API_KEY):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    fmt = str(data.get("format", "mp3")).lower()

    if fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Format must be mp3 or mp4"}), 400
    if not url.startswith(("https://www.youtube.com/", "https://youtube.com/",
                           "https://youtu.be/", "https://m.youtube.com/")):
        return jsonify({"error": "Invalid YouTube URL"}), 400

    job_dir = os.path.join(DOWNLOAD_DIR, uuid.uuid4().hex)
    os.makedirs(job_dir, exist_ok=True)

    try:
        opts = {
            "outtmpl": os.path.join(job_dir, "media.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "ffmpeg_location": FFMPEG,
            "max_filesize": 100 * 1024 * 1024,
            "socket_timeout": 20,
            "retries": 1,
        }

        if fmt == "mp3":
            opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            opts.update({
                "format": "best[ext=mp4][height<=720]/best[height<=720]",
                "merge_output_format": "mp4",
            })

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        candidates = [
            os.path.join(job_dir, f)
            for f in os.listdir(job_dir)
            if os.path.isfile(os.path.join(job_dir, f))
        ]
        if not candidates:
            return jsonify({"error": "No file was created"}), 500

        filepath = max(candidates, key=os.path.getsize)
        mimetype = "audio/mpeg" if fmt == "mp3" else "video/mp4"
        extension = "mp3" if fmt == "mp3" else "mp4"

        response = send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"youtube-{uuid.uuid4().hex[:8]}.{extension}",
        )
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response

    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        app.logger.exception("Download failed")
        return jsonify({"error": "Download failed; check server logs"}), 500
