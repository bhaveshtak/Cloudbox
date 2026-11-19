
import os
import mimetypes
from functools import wraps
from io import BytesIO

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, g
)
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
CALLBACK_URL = os.getenv(
    "CALLBACK_URL",
    "http://127.0.0.1:5000/auth/callback"
)

BUCKET_NAME = "cloudbox_files"
MAX_FILE_BYTES = 5 * 1024 * 1024
STORAGE_LIMIT_BYTES = 100 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "txt",
    "docx", "xlsx", "csv"
}

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY missing in .env")

if not FLASK_SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY missing in .env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=FLASK_SECRET_KEY,
    MAX_CONTENT_LENGTH=MAX_FILE_BYTES,
    SESSION_TYPE="filesystem",
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv(
        "SESSION_COOKIE_SECURE", "false"
    ).lower() == "true",
    SESSION_FILE_DIR=os.path.join(app.instance_path, "flask_session")
)

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

Session(app)
csrf = CSRFProtect(app)


def new_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_login_session(auth_session):
    session.clear()
    session["access_token"] = auth_session.access_token
    session["refresh_token"] = auth_session.refresh_token


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        access_token = session.get("access_token")
        refresh_token = session.get("refresh_token")

        if not access_token or not refresh_token:
            session.clear()
            return redirect(url_for("login"))

        try:
            client = new_supabase_client()
            client.auth.set_session(access_token, refresh_token)
            user_response = client.auth.get_user()
            user = user_response.user

            if not user:
                session.clear()
                return redirect(url_for("login"))

            current_session = client.auth.get_session()
            if current_session:
                save_login_session(current_session)

            g.supabase = client
            g.user = user

        except Exception:
            session.clear()
            flash("Your session expired. Please log in again.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def get_user_files():
    user_id = str(g.user.id)
    response = g.supabase.storage.from_(BUCKET_NAME).list(user_id)

    files = []
    total_bytes = 0

    for item in response or []:
        name = item.get("name")
        if not name:
            continue

        metadata = item.get("metadata") or {}
        size = int(metadata.get("size") or 0)
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""

        files.append({
            "name": name,
            "size": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "extension": extension
        })
        total_bytes += size

    files.sort(key=lambda item: item["name"].lower())
    return files, total_bytes


def unique_filename(filename, existing_names):
    if filename not in existing_names:
        return filename

    base, extension = os.path.splitext(filename)
    counter = 1

    while True:
        candidate = f"{base} ({counter}){extension}"
        if candidate not in existing_names:
            return candidate
        counter += 1


@app.route("/")
@login_required
def home():
    try:
        all_files, used_bytes = get_user_files()
        total_files = len(all_files)

        search_query = request.args.get("q", "").strip().lower()
        files = [
            item for item in all_files
            if search_query in item["name"].lower()
        ] if search_query else all_files

        remaining_bytes = max(0, STORAGE_LIMIT_BYTES - used_bytes)
        usage_percent = min(
            100, round((used_bytes / STORAGE_LIMIT_BYTES) * 100, 1)
        )

        return render_template(
            "index.html",
            files=files,
            total_files=total_files,
            used_bytes=used_bytes,
            used_mb=round(used_bytes / (1024 * 1024), 2),
            remaining_mb=round(remaining_bytes / (1024 * 1024), 2),
            usage_percent=usage_percent,
            user=g.user,
            search_query=search_query
        )

    except Exception as error:
        app.logger.exception("Dashboard error: %s", error)
        flash("Unable to load your files. Please refresh the page.", "error")
        return render_template(
            "index.html",
            files=[],
            total_files=0,
            used_bytes=0,
            used_mb=0,
            remaining_mb=100,
            usage_percent=0,
            user=g.user,
            search_query=""
        )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or len(password) < 6:
            flash("Enter a valid email and password of at least 6 characters.", "error")
            return redirect(url_for("signup"))

        try:
            client = new_supabase_client()
            response = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": CALLBACK_URL
                }
            })

            if response.session:
                save_login_session(response.session)
                return redirect(url_for("home"))

            flash("Signup successful! Verify your email, then log in.", "success")
            return redirect(url_for("login"))

        except Exception as error:
            app.logger.exception("Signup error: %s", error)
            flash("Signup failed. Check your details or try another email.", "error")

    return render_template("auth.html", page="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        try:
            client = new_supabase_client()
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                save_login_session(response.session)
                return redirect(url_for("home"))

            flash("Login failed. Please try again.", "error")

        except Exception as error:
            app.logger.exception("Login error: %s", error)
            flash("Invalid email or password, or email not verified.", "error")

    return render_template("auth.html", page="login")


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")

    if not code:
        flash("Verification callback is missing its code. Please log in.", "error")
        return redirect(url_for("login"))

    try:
        client = new_supabase_client()
        response = client.auth.exchange_code_for_session({
            "auth_code": code
        })

        if response.session:
            save_login_session(response.session)
            flash("Email verified successfully!", "success")
            return redirect(url_for("home"))

    except Exception as error:
        app.logger.exception("Auth callback error: %s", error)
        flash("Verification link expired or invalid. Please try again.", "error")

    return redirect(url_for("login"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    try:
        g.supabase.auth.sign_out(scope="local")
    except Exception:
        app.logger.warning("Supabase sign-out could not be completed.")
    finally:
        session.clear()

    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please select a file first.", "error")
        return redirect(url_for("home"))

    filename = secure_filename(uploaded_file.filename)

    if not filename or not allowed_file(filename):
        flash("This file type is not supported.", "error")
        return redirect(url_for("home"))

    file_data = uploaded_file.read()

    if not file_data:
        flash("The selected file is empty.", "error")
        return redirect(url_for("home"))

    if len(file_data) > MAX_FILE_BYTES:
        flash("Maximum file size is 5 MB.", "error")
        return redirect(url_for("home"))

    try:
        files, used_bytes = get_user_files()

        if used_bytes + len(file_data) > STORAGE_LIMIT_BYTES:
            flash("Storage limit reached. Delete files to free up space.", "error")
            return redirect(url_for("home"))

        filename = unique_filename(
            filename, {item["name"] for item in files}
        )

        user_path = f"{g.user.id}/{filename}"
        content_type = (
            uploaded_file.mimetype
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        g.supabase.storage.from_(BUCKET_NAME).upload(
            user_path,
            file_data,
            {"content-type": content_type, "upsert": "false"}
        )

        flash(f"{filename} uploaded successfully!", "success")

    except Exception as error:
        app.logger.exception("Upload error: %s", error)
        flash("Upload failed. Please try again.", "error")

    return redirect(url_for("home"))


@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    filename = secure_filename(filename)

    if not filename:
        flash("Invalid file name.", "error")
        return redirect(url_for("home"))

    try:
        user_path = f"{g.user.id}/{filename}"
        data = g.supabase.storage.from_(BUCKET_NAME).download(user_path)

        return send_file(
            BytesIO(data),
            as_attachment=True,
            download_name=filename,
            mimetype=(
                mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            )
        )

    except Exception as error:
        app.logger.exception("Download error: %s", error)
        flash("Unable to download this file.", "error")
        return redirect(url_for("home"))


@app.route("/delete/<path:filename>", methods=["POST"])
@login_required
def delete_file(filename):
    filename = secure_filename(filename)

    if not filename:
        flash("Invalid file name.", "error")
        return redirect(url_for("home"))

    try:
        user_path = f"{g.user.id}/{filename}"
        g.supabase.storage.from_(BUCKET_NAME).remove([user_path])
        flash(f"{filename} deleted successfully.", "success")

    except Exception as error:
        app.logger.exception("Delete error: %s", error)
        flash("Unable to delete this file.", "error")

    return redirect(url_for("home"))


@app.route("/rename/<path:filename>", methods=["POST"])
@login_required
def rename_file(filename):
    old_name = secure_filename(filename)
    new_name = secure_filename(request.form.get("new_name", "").strip())

    if not old_name or not new_name:
        flash("Please enter a valid file name.", "error")
        return redirect(url_for("home"))

    if not allowed_file(new_name):
        flash("This file type is not supported.", "error")
        return redirect(url_for("home"))

    old_ext = os.path.splitext(old_name)[1].lower()
    new_ext = os.path.splitext(new_name)[1].lower()

    if old_ext != new_ext:
        flash("Keep the original file extension when renaming.", "error")
        return redirect(url_for("home"))

    if old_name == new_name:
        return redirect(url_for("home"))

    try:
        files, _ = get_user_files()
        existing_names = {item["name"] for item in files}

        if new_name in existing_names:
            flash("A file with that name already exists.", "error")
            return redirect(url_for("home"))

        old_path = f"{g.user.id}/{old_name}"
        new_path = f"{g.user.id}/{new_name}"

        file_data = g.supabase.storage.from_(BUCKET_NAME).download(old_path)
        content_type = (
            mimetypes.guess_type(new_name)[0]
            or "application/octet-stream"
        )

        g.supabase.storage.from_(BUCKET_NAME).upload(
            new_path,
            file_data,
            {"content-type": content_type, "upsert": "false"}
        )

        try:
            g.supabase.storage.from_(BUCKET_NAME).remove([old_path])
        except Exception:
            # Keep the new copy if cleanup of the old copy fails.
            app.logger.exception("Old file cleanup failed after rename.")
            flash("New file created, but the old copy could not be removed.", "warning")
            return redirect(url_for("home"))

        flash("File renamed successfully.", "success")

    except Exception as error:
        app.logger.exception("Rename error: %s", error)
        flash("Unable to rename this file.", "error")

    return redirect(url_for("home"))


@app.route("/health")
def health():
    return {"status": "ok", "app": "CloudBox"}


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(error):
    flash("Maximum upload size is 5 MB.", "error")
    return redirect(url_for("home"))


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
