import os
from flask import Flask, render_template, request, redirect, flash, url_for, send_file
from werkzeug.utils import secure_filename

from encrypt_and_upload import encrypt_and_upload_web
from download_and_decrypt import decrypt_and_reconstruct_web
from utils.metadata import load_registry
from config import *

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for flash messages

# Ensure folders exist
os.makedirs("uploads", exist_ok=True)

@app.route("/")
def index():
    registry = load_registry()
    return render_template("index.html", files=list(registry.keys()))

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("No file selected")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    filepath = os.path.join("uploads", filename)
    file.save(filepath)

    try:
        encrypt_and_upload_web(filepath)
        flash(f"✅ File '{filename}' uploaded successfully")
    except Exception as e:
        flash(f"❌ Upload failed: {str(e)}")

    return redirect(url_for("index"))

@app.route("/download/<filename>")
def download_file(filename):
    try:
        reconstructed_path = decrypt_and_reconstruct_web(filename)
        return send_file(reconstructed_path, as_attachment=True)
    except Exception as e:
        flash(f"❌ Download failed: {str(e)}")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
