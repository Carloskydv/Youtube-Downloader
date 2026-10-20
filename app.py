
from flask import Flask, request, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "Youtube-Downloader"
    })

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    fmt = data.get("format", "mp3").lower()

    if not url or fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Indica una URL y el formato mp3 o mp4"}), 400

    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "Solo se admiten enlaces de YouTube"}), 400

    filename = str(uuid.uuid4())
    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/{filename}.%(ext)s",
        "noplaylist": True,
        "quiet": True,
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
            "format": "best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if fmt == "mp3":
                filepath = os.path.splitext(filepath)[0] + ".mp3"
            if not os.path.isfile(filepath):
                return jsonify({"error": "No se encontró el archivo generado"}), 500
        return jsonify({
            "status": "downloaded",
            "filename": os.path.basename(filepath),
            "message": "Descarga completada"
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
