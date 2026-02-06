from flask import Flask, render_template, request, jsonify
import pandas as pd
import datetime
import os
from sheets_db import GoogleSheetsDB

app = Flask(__name__)

# --- Database Configuration ---
# Check if Google Sheets credentials exist
GOOGLE_CREDS = 'credentials.json'
SHEET_NAME = 'Fresher Induction 2026' # Name of your Google Sheet
USE_GOOGLE_SHEETS = os.path.exists(GOOGLE_CREDS)

# --- In-Memory Database ---
# Load Student Data
STUDENT_DB = {}
google_db = None

if USE_GOOGLE_SHEETS:
    try:
        print("Found credentials.json! Connecting to Google Sheets...")
        google_db = GoogleSheetsDB(GOOGLE_CREDS, SHEET_NAME)
        STUDENT_DB = google_db.load_students()
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        print("Falling back to Excel file...")
        USE_GOOGLE_SHEETS = False

if not USE_GOOGLE_SHEETS:
    try:
        df = pd.read_excel('Students_Data_500.xlsx')
        # Clean columns: strip spaces
        df.columns = [c.strip() for c in df.columns]
        # Expected columns: NAME, EMAIL-ID, BRANCH, UUID
        for _, row in df.iterrows():
            uid = str(row.get('UUID', '')).strip()
            if uid:
                STUDENT_DB[uid] = {
                    'name': row.get('NAME', 'Unknown'),
                    'branch': row.get('BRANCH', 'Unknown'),
                    'email': row.get('EMAIL-ID', ''),
                    'id': uid,
                    'status': 'pending',
                    'time': None
                }
        print(f"Loaded {len(STUDENT_DB)} students.")
    except Exception as e:
        print(f"Error loading Excel: {e}")

# Set to store scanned IDs for the current session
SCANNED_IDS = set()
SCAN_LOGS = []

# Initialize SCANNED_IDS and SCAN_LOGS from loaded DB
if STUDENT_DB:
    print("Initializing session from database...")
    for uid, data in STUDENT_DB.items():
        if data.get('status') in ['present', 'checked_in']:
            SCANNED_IDS.add(uid)
            # Add to logs if time exists
            if data.get('time'):
                SCAN_LOGS.append({
                    "name": data['name'],
                    "id": uid,
                    "branch": data['branch'],
                    "time": data['time']
                })
    
    # Sort logs by time (if possible, otherwise keeping order is hard without full timestamp)
    # For now, let's just assume database order is roughly chronological or just list them.
    # To be safe, we reverse it so recent might be at top if sheet is ordered? 
    # Actually, sheet is usually ordered by ID. 
    # We can't easily sort by '12:00 PM' string without date, but this populates the list at least.
    print(f"Restored {len(SCANNED_IDS)} check-ins from database.")

# Event Details (Hardcoded for now, can be moved to config)
EVENT_DETAILS = {
    "name": "Fresher Induction 2026",
    "venue": "Main Auditorium",
    "date": datetime.date.today().strftime("%B %d, %Y")
}

@app.route('/')
def index():
    return render_template('index.html', event=EVENT_DETAILS)

@app.route('/students')
def students_page():
    # Calculate stats
    total = len(STUDENT_DB)
    checked_in = len(SCANNED_IDS)
    remaining = total - checked_in
    
    # Convert DB to list for template
    students_list = list(STUDENT_DB.values())
    
    return render_template('students.html', 
                           event=EVENT_DETAILS, 
                           students=students_list,
                           stats={'total': total, 'checked_in': checked_in, 'remaining': remaining})

@app.route('/scan', methods=['POST'])
def scan_qr():
    data = request.json
    qr_content = data.get('content', '')

    if not qr_content:
        return jsonify({"status": "error", "message": "No content"}), 400

    # Parse QR Data
    # Expected: "Name: XXX\nID: XXX\nBranch: XXX"
    info = {}
    try:
        lines = qr_content.split('\n')
        for line in lines:
            if ": " in line:
                key, val = line.split(": ", 1)
                info[key.strip()] = val.strip()
    except:
        return jsonify({"status": "error", "message": "Invalid QR Format"}), 400

    student_id = info.get('ID')
    name = info.get('Name', 'Unknown')
    branch = info.get('Branch', 'Unknown')

    if not student_id:
        return jsonify({"status": "error", "message": "ID not found in QR"}), 400

    # Check Duplicates
    if student_id in SCANNED_IDS:
        # Retrieve original check-in time
        original_time = "Unknown"
        if student_id in STUDENT_DB and STUDENT_DB[student_id].get('time'):
            original_time = STUDENT_DB[student_id]['time']
            
        return jsonify({
            "status": "duplicate",
            "message": "ALREADY SCANNED",
            "student": {
                "name": name, 
                "id": student_id, 
                "branch": branch,
                "time": original_time  # Send original scan time
            }
        })

    # New Scan
    SCANNED_IDS.add(student_id)
    timestamp = datetime.datetime.now().strftime("%I:%M:%S %p") # 12-hour format
    
    # Update Main DB if exists
    if student_id in STUDENT_DB:
        STUDENT_DB[student_id]['status'] = 'checked_in'
        STUDENT_DB[student_id]['time'] = timestamp
        
        # Sync with Google Sheets if enabled
        if USE_GOOGLE_SHEETS and google_db:
            google_db.mark_present(student_id)

    log_entry = {
        "name": name,
        "id": student_id,
        "branch": branch,
        "time": timestamp
    }
    SCAN_LOGS.insert(0, log_entry) # Add to top

    return jsonify({
        "status": "success",
        "message": "Verified",
        "student": log_entry
    })

@app.route('/reset', methods=['POST'])
def reset_session():
    SCANNED_IDS.clear()
    SCAN_LOGS.clear()
    # Reset DB status
    for uid in STUDENT_DB:
        STUDENT_DB[uid]['status'] = 'pending'
        STUDENT_DB[uid]['time'] = None
        
    return jsonify({"status": "success", "message": "Session Reset"})

@app.route('/history')
def get_history():
    return jsonify(SCAN_LOGS)

if __name__ == '__main__':
    # Host on 0.0.0.0 to allow access from mobile on same network
    # Run with SSL (adhoc) to allow camera permissions on mobile
    app.run(debug=True, host='0.0.0.0', port=5001, ssl_context='adhoc')
