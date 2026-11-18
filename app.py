
from flask import (
    Flask, render_template, request, redirect,
    url_for, send_file, flash, session, g
)
from werkzeug.utils import secure_filename
from supabase import create_client
from dotenv import load_dotenv
from flask_session import Session
from functools import wraps
from io import BytesIO
import os
from flask_wtf.csrf import CSRFProtect

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")

if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY missing in .env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "cloudbox_files"
CALLBACK_URL = os.getenv(
    "CALLBACK_URL",
    "http://127.0.0.1:5000/auth/callback"
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key missing in .env")

# Server-side sessions
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_FILE_DIR"] = os.path.join(
    app.instance_path, "flask_session"
)
# Local development: HTTP
app.config["SESSION_COOKIE_SECURE"] = False

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg",
    "txt", "docx", "xlsx", "csv"
}
csrf = CSRFProtect(app)


def new_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )



def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            access_token = session.get("access_token")
            refresh_token = session.get("refresh_token")

            if not access_token or not refresh_token:
                session.clear()
                flash("Please login first.")
                return redirect(url_for("login"))

            client = new_supabase_client()

            client.auth.set_session(
                access_token,
                refresh_token
            )

            result = client.auth.get_user()

            if not result or not result.user:
                session.clear()
                flash("Session expired. Please login again.")
                return redirect(url_for("login"))

            current_session = client.auth.get_session()

            if current_session:
                session["access_token"] = current_session.access_token
                session["refresh_token"] = current_session.refresh_token

            g.supabase = client
            g.user = result.user

        except Exception as error:
            print("AUTH ERROR:", error)
            session.clear()
            flash("Please login again.")
            return redirect(url_for("login"))

        # Run the protected route outside the authentication try block
        return function(*args, **kwargs)

    return wrapper



def save_login_session(auth_session):
    session.clear()
    session["access_token"] = auth_session.access_token
    session["refresh_token"] = auth_session.refresh_token



@app.route("/")
@login_required
def home():

    # App storage limit: 100 MB
    storage_limit_bytes = 100 * 1024 * 1024

    files = []
    storage_used_bytes = 0

    try:
        folder = str(g.user.id)

        response = g.supabase.storage.from_(BUCKET_NAME).list(
            path=folder
        )

        file_items = [
            item for item in response
            if item.get("name") and item.get("id")
        ]

        files = [item["name"] for item in file_items]

        files.sort(key=str.lower)

        # Calculate total file size
        for item in file_items:
            metadata = item.get("metadata") or {}
            size = metadata.get("size") or 0
            storage_used_bytes += int(size)

    except Exception as error:
        print("STORAGE ERROR:", error)
        flash("Could not load storage information.")

    # Storage calculations
    storage_remaining_bytes = max(
        0, storage_limit_bytes - storage_used_bytes
    )

    storage_percent = min(
        100,
        round((storage_used_bytes / storage_limit_bytes) * 100, 2)
    )

    storage_used_mb = round(
        storage_used_bytes / (1024 * 1024), 2
    )

    storage_remaining_mb = round(
        storage_remaining_bytes / (1024 * 1024), 2
    )

    return render_template(
        "index.html",
        files=files,
        user_email=g.user.email,
        total_files=len(files),
        storage_used_mb=storage_used_mb,
        storage_remaining_mb=storage_remaining_mb,
        storage_percent=storage_percent,
        storage_limit_mb=100
    )



@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Enter email and password.")
            return redirect(url_for("signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
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
                flash("Account created successfully!")
                return redirect(url_for("home"))

            flash("Signup successful! Check your email to verify your account.")
            return redirect(url_for("login"))

        except Exception as error:
            print("SIGNUP ERROR:", error)
            flash("Signup failed. Check email or try another account.")
            return redirect(url_for("signup"))

    return render_template("auth.html", page="signup")
@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")

    if not code:
        flash("Verification code missing. Please try again.")
        return redirect(url_for("login"))

    try:
        client = new_supabase_client()

        response = client.auth.exchange_code_for_session({
            "auth_code": code
        })

        if response.session:
            save_login_session(response.session)
            flash("Email verified successfully!")
            return redirect(url_for("home"))

        flash("Email verified! Please login.")
        return redirect(url_for("login"))

    except Exception as error:
        print("CALLBACK ERROR:", error)
        flash("Verification failed. Please try a fresh email link.")
        return redirect(url_for("login"))



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

            save_login_session(response.session)

            flash("Login successful!")
            return redirect(url_for("home"))

        except Exception as error:

            print("LOGIN ERROR:", repr(error))

            flash(f"Login failed: {str(error)}")

            return redirect(url_for("login"))

    return render_template("auth.html", page="login")


@app.route("/logout", methods=["POST"])
def logout():
    try:
        access_token = session.get("access_token")
        refresh_token = session.get("refresh_token")

        if access_token and refresh_token:
            client = new_supabase_client()

            client.auth.set_session(
                access_token,
                refresh_token
            )

            client.auth.sign_out(scope="local")

    except Exception as error:
        print("LOGOUT ERROR:", error)

    finally:
        session.clear()

    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():

    if "file" not in request.files:
        flash("Please select a file.")
        return redirect(url_for("home"))

    file = request.files["file"]

    if not file.filename:
        flash("No file selected.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename):
        flash("File type not allowed.")
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)

    if not filename:
        flash("Invalid filename.")
        return redirect(url_for("home"))

    try:
        folder = str(g.user.id)

        # Get existing filenames from user's folder
        response = g.supabase.storage.from_(BUCKET_NAME).list(
            path=folder
        )

        existing_names = {
            item.get("name", "").lower()
            for item in response
            if item.get("name")
        }

        # Separate filename and extension
        name, extension = os.path.splitext(filename)

        # Automatically rename duplicate files
        new_filename = filename
        counter = 1

        while new_filename.lower() in existing_names:
            new_filename = f"{name}({counter}){extension}"
            counter += 1

        user_path = f"{folder}/{new_filename}"

        # Upload file without overwriting existing files
        g.supabase.storage.from_(BUCKET_NAME).upload(
            path=user_path,
            file=file.read(),
            file_options={
                "content-type": file.mimetype or "application/octet-stream",
                "upsert": "false"
            }
        )

        flash(f"File uploaded successfully as {new_filename}!")

    except Exception as error:
        print("UPLOAD ERROR:", error)
        flash("Upload failed. Check Storage policies.")

    return redirect(url_for("home"))



@app.route("/download/<filename>")
@login_required
def download_file(filename):
    filename = secure_filename(filename)

    try:
        user_path = f"{g.user.id}/{filename}"

        data = g.supabase.storage.from_(BUCKET_NAME).download(
            user_path
        )

        return send_file(
            BytesIO(data),
            as_attachment=True,
            download_name=filename
        )

    except Exception as error:
        print("DOWNLOAD ERROR:", error)
        flash("Could not download file.")
        return redirect(url_for("home"))


@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_file(filename):
    filename = secure_filename(filename)

    try:
        user_path = f"{g.user.id}/{filename}"

        g.supabase.storage.from_(BUCKET_NAME).remove([user_path])
        flash("File deleted successfully!")

    except Exception as error:
        print("DELETE ERROR:", error)
        flash("Could not delete file.")

    return redirect(url_for("home"))


@app.errorhandler(413)
def file_too_large(error):
    flash("File must be smaller than 5 MB.")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
