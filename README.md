# QR Code Attendance System (Flask)

A beginner-friendly student project using Flask, SQLite, QR code generation, and browser camera scanning.

## Requirements
- Python 3.10 or newer
- Internet connection for the QR scanner JavaScript library loaded from a CDN
- A webcam or phone camera if testing the scanner on a device

## Setup on Windows / PyCharm

1. Extract this ZIP file to a folder, for example `C:\Users\YourName\Projects\qr_attendance_flask`.
2. Open PyCharm and choose **Open**, then select the extracted `qr_attendance_flask` folder.
3. Open the PyCharm Terminal at the bottom.
4. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

5. Activate it:

   ```powershell
   .venv\Scripts\activate
   ```

   If PowerShell blocks activation, use Command Prompt in PyCharm terminal and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Start the application:

   ```bash
   python app.py
   ```

8. Open this address in your browser:

   `http://127.0.0.1:5000`

## Demo login
- Username: `admin`
- Password: `admin123`

These are demo credentials. Change them before using the app beyond a local classroom demonstration. You can set environment variables `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `FLASK_SECRET_KEY` before starting Flask.

## How to test
1. Log in.
2. Register a student with a unique student ID, name, and class.
3. Click **View QR** beside that student.
4. Open **Scan QR code** on the dashboard.
5. Allow camera access and scan the student QR code shown on another screen or printed paper.
6. Open **Attendance** to view records and export a CSV file.
7. Scan the same QR again that day; the system should reject the duplicate.

## Notes and limitations
- This is an educational prototype, not a hardened production attendance system.
- Attendance is limited to one record per student per calendar day. For multiple classes or sessions per day, add a session/class identifier to the attendance table and uniqueness rule.
- The scanner library is loaded from an internet CDN. The first page load needs internet access.
- Camera access generally works on `localhost` / `127.0.0.1` or HTTPS, not on an ordinary insecure remote HTTP site.
- The SQLite database `attendance.db` is created automatically next to `app.py`.
- QR image files are stored in `static/qrcodes/`.
- If testing on a shared computer, do not leave the admin session open.
