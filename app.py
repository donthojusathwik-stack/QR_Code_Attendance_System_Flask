import csv
import io
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

import qrcode
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
QR_DIR = os.path.join(BASE_DIR, "static", "qrcodes")
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-development-secret")

# Demo credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD environment variables for your own values.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(
    os.environ.get("ADMIN_PASSWORD", "admin123")
)

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                attendance_time TEXT NOT NULL,
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def make_qr(token, student_code):
    filename = f"{student_code}.png"
    path = os.path.join(QR_DIR, filename)
    image = qrcode.make(token)
    image.save(path)
    return filename

@app.route("/")
def index():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as db:
        total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        today_count = db.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?", (today,)
        ).fetchone()[0]
        students = db.execute("SELECT * FROM students ORDER BY name").fetchall()
    return render_template(
        "dashboard.html", total_students=total_students,
        today_count=today_count, students=students, recent=recent, today=today
    )

@app.route("/students/add", methods=["POST"])
@login_required
def add_student():
    student_code = request.form.get("student_id", "").strip()
    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip()

    if not student_code or not name or not class_name:
        flash("Please fill in every student field.", "error")
        return redirect(url_for("dashboard"))

    token = secrets.token_urlsafe(24)
    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO students (student_id, name, class_name, token, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (student_code, name, class_name, token, datetime.now().isoformat(timespec="seconds")))
        make_qr(token, student_code)
        flash(f"Student {name} registered and QR code created.", "success")
    except sqlite3.IntegrityError:
        flash("That student ID is already registered. Use a unique ID.", "error")
    return redirect(url_for("dashboard"))

@app.route("/students/<int:student_pk>/qr")
@login_required
def student_qr(student_pk):
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE id = ?", (student_pk,)).fetchone()
    if student is None:
        abort(404)
    qr_filename = f"{student['student_id']}.png"
    qr_path = os.path.join(QR_DIR, qr_filename)
    if not os.path.exists(qr_path):
        make_qr(student["token"], student["student_id"])
    return render_template("student_qr.html", student=student, qr_filename=qr_filename)

@app.route("/scan")
@login_required
def scan():
    return render_template("scan.html")

@app.route("/api/attendance", methods=["POST"])
@login_required
def record_attendance():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    if not token:
        return jsonify(ok=False, message="No QR code data was received."), 400

    now = datetime.now()
    date_text = now.strftime("%Y-%m-%d")
    time_text = now.strftime("%H:%M:%S")
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE token = ?", (token,)).fetchone()
        if student is None:
            return jsonify(ok=False, message="This QR code is not registered in the system."), 404
        try:
            db.execute("""
                INSERT INTO attendance (student_id, attendance_date, attendance_time)
                VALUES (?, ?, ?)
            """, (student["id"], date_text, time_text))
        except sqlite3.IntegrityError:
            return jsonify(
                ok=False,
                message=f"{student['name']} already has attendance recorded for today."
            ), 409

    return jsonify(
        ok=True,
        message=f"Attendance recorded for {student['name']} ({student['student_id']}) at {time_text}."
    )

@app.route("/attendance")
@login_required
def attendance():
    date_filter = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    with get_db() as db:
        records = db.execute("""
            SELECT a.attendance_date, a.attendance_time,
                   s.student_id AS student_code, s.name, s.class_name
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.attendance_date = ?
            ORDER BY a.attendance_time DESC
        """, (date_filter,)).fetchall()
    return render_template("attendance.html", records=records, date_filter=date_filter)

@app.route("/attendance/export")
@login_required
def export_attendance():
    date_filter = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    with get_db() as db:
        records = db.execute("""
            SELECT s.student_id, s.name, s.class_name,
                   a.attendance_date, a.attendance_time
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.attendance_date = ?
            ORDER BY s.name
        """, (date_filter,)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Class", "Date", "Time"])
    for row in records:
        writer.writerow([row["student_id"], row["name"], row["class_name"],
                         row["attendance_date"], row["attendance_time"]])
    memory_file = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    memory_file.seek(0)
    return send_file(
        memory_file, mimetype="text/csv", as_attachment=True,
        download_name=f"attendance_{date_filter}.csv"
    )

@app.route("/students/<int:student_pk>/delete", methods=["POST"])
@login_required
def delete_student(student_pk):
    with get_db() as db:
        student = db.execute("SELECT student_id FROM students WHERE id = ?", (student_pk,)).fetchone()
        if student:
            db.execute("DELETE FROM students WHERE id = ?", (student_pk,))
            qr_path = os.path.join(QR_DIR, f"{student['student_id']}.png")
            if os.path.exists(qr_path):
                os.remove(qr_path)
            flash("Student and their attendance records were deleted.", "success")
        else:
            flash("Student not found.", "error")
    return redirect(url_for("dashboard"))

init_db()

if __name__ == "__main__":
    app.run(debug=True)
