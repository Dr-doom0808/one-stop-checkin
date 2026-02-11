from flask import Flask, render_template, request, jsonify
import datetime
import os
import secrets
import qrcode
import io
import base64
import smtplib
from email.message import EmailMessage
from mongo_db import MongoDB

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for sessions

# --- Email Configuration ---
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SENDER_EMAIL = "abhyudaya1@niet.co.in"
APP_PASSWORD = "niet@1234"

def send_invitation_email(name, email, branch, uuid, qr_img_bytes):
    try:
        msg = EmailMessage()
        msg["Subject"] = "🎉 Fresher Party Invitation 2026 🎉"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email

        msg.set_content(f"""
Dear {name},

You are cordially invited to the Fresher Party Abhiyudaya - The Freshers🎉

📅 Date: 12 Febuary 2026
📍 Venue: NIET Plot no 19, Play Ground
⏰ Entry Time: 2:30 to 5:00 PM

Your unique entry QR code is attached with this email.
Please carry this QR code and Identity Card for entry verification.

Warm Regards,

Organizing Committee
""")

        # Attach QR Code from memory bytes
        msg.add_attachment(
            qr_img_bytes,
            maintype="image",
            subtype="png",
            filename="Entry_QR.png"
        )

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# --- Admin Configuration ---
ADMIN_PASSWORD = "admin" # Change this!

# --- Database Configuration ---
# MongoDB Connection String
MONGO_URI = "mongodb+srv://NIET_Event:NIET0000@cluster0.u9owtey.mongodb.net/"
DB_NAME = "student_event"
COLLECTION_NAME = "student_verify"

# --- In-Memory Database ---
# Load Student Data
STUDENT_DB = {}
SCANNED_IDS = set()
SCAN_LOGS = []
mongo_db = None

def load_data():
    global STUDENT_DB, mongo_db
    
    STUDENT_DB = {} # Clear existing
    
    try:
        print("Connecting to MongoDB Atlas...")
        if not mongo_db:
            mongo_db = MongoDB(MONGO_URI, DB_NAME, COLLECTION_NAME)
        STUDENT_DB = mongo_db.load_students()
        # Debug: Print first 5 keys to verify format
        print("DEBUG: Sample loaded UUIDs:", list(STUDENT_DB.keys())[:5])
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to connect to MongoDB: {e}")
        print("Please check your internet connection and connection string.")

def initialize_session():
    global SCANNED_IDS, SCAN_LOGS
    
    # Reload Data
    load_data()
    
    # Reset Session
    SCANNED_IDS.clear()
    SCAN_LOGS.clear()
    
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
        
        # Reverse logs so most recent (bottom of sheet) are first
        SCAN_LOGS.reverse()
        print(f"Restored {len(SCANNED_IDS)} check-ins from database.")

# Initial Load
initialize_session()

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

    # --- Simplified Logic ---
    # 1. Extract UUID
    raw_id = qr_content.strip()
    
    # 2. Clean/Normalize ID
    # Try exact match first
    student_id = raw_id
    
    # If not found, try stripping potential suffix (e.g., _g80v)
    if student_id not in STUDENT_DB:
        # Try removing the last part after underscore
        if '_' in raw_id:
            candidate_id = raw_id.rsplit('_', 1)[0]
            if candidate_id in STUDENT_DB:
                print(f"DEBUG: Matched via suffix stripping: {raw_id} -> {candidate_id}")
                student_id = candidate_id

    # 3. Match with Database
    if student_id not in STUDENT_DB:
         print(f"DEBUG: Failed match for {raw_id}. Available keys sample: {list(STUDENT_DB.keys())[:3]}")
         return jsonify({
            "status": "error", 
            "message": "Not Registered",
            "student": {
                "id": raw_id,
                "name": "Unknown Student",
                "branch": "Unknown"
            }
        }), 404

    # Get Student Details
    student_info = STUDENT_DB[student_id]
    name = student_info['name']
    branch = student_info['branch']

    # 4. Check Duplicates
    if student_id in SCANNED_IDS:
        original_time = student_info.get('time', "Unknown")
        return jsonify({
            "status": "duplicate",
            "message": "ALREADY SCANNED",
            "student": {
                "name": name, 
                "id": student_id, 
                "branch": branch,
                "time": original_time
            }
        })

    # 5. Success: Mark as Verified
    SCANNED_IDS.add(student_id)
    timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
    
    # Update Local DB
    STUDENT_DB[student_id]['status'] = 'checked_in'
    STUDENT_DB[student_id]['time'] = timestamp
    
    # Update MongoDB
    if mongo_db:
        mongo_db.mark_present(student_id)

    log_entry = {
        "name": name,
        "id": student_id,
        "branch": branch,
        "time": timestamp
    }
    SCAN_LOGS.insert(0, log_entry)

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

@app.route('/sync', methods=['POST'])
def sync_data():
    try:
        initialize_session()
        return jsonify({"status": "success", "message": "Synced with MongoDB"})
    except Exception as e:
        print(f"Sync error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/history')
def get_history():
    return jsonify(SCAN_LOGS)

# --- Admin Routes ---

@app.route('/admin')
def admin_page():
    # In a real app, check session here
    return render_template('admin.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid Password"}), 401

@app.route('/admin/search', methods=['POST'])
def admin_search():
    query = request.json.get('query', '').lower()
    
    results = []
    for uid, data in STUDENT_DB.items():
        if (query in data['name'].lower() or 
            query in data['id'].lower() or 
            query in data['branch'].lower()):
            results.append(data)
            
    # Sort by status (present first) then name
    results.sort(key=lambda x: (x['status'] != 'present', x['name']))
    
    return jsonify(results[:50]) # Limit to 50 results for performance

@app.route('/admin/add', methods=['POST'])
def admin_add_student():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    branch = data.get('branch')
    
    import random
    import string

    if not name or not branch or not email:
        return jsonify({"status": "error", "message": "Name, Email and Branch are required"}), 400
        
    # Generate UUID: name_emailprefix_branch_random
    # 1. Name: Lowercase, remove spaces
    clean_name = name.lower().replace(" ", "")
    
    # 2. Email Prefix: Part before @, trimmed
    email_prefix = email.split('@')[0].strip()
    
    # 3. Branch: Lowercase, remove spaces
    clean_branch = branch.lower().replace(" ", "")
    
    # 4. Random Suffix: Char(A-Z) + Digit(0-9) + Digit(0-9) + Char(A-Z)
    rand_char1 = random.choice(string.ascii_uppercase)
    rand_digit1 = str(random.randint(0, 9))
    rand_digit2 = str(random.randint(0, 9))
    rand_char2 = random.choice(string.ascii_uppercase)
    random_suffix = f"{rand_char1}{rand_digit1}{rand_digit2}{rand_char2}"
    
    uuid = f"{clean_name}_{email_prefix}_{clean_branch}_{random_suffix}"
    
    # Create Student Object
    student_data = {
        "NAME": name,
        "EMAIL": email,
        "BRANCH": branch,
        "UUID": uuid,
        "status": "pending",
        "Entry_time": None
    }
    
    # 1. Add to MongoDB
    if mongo_db:
        success = mongo_db.add_student(student_data)
        if not success:
             return jsonify({"status": "error", "message": "Database Error"}), 500
    
    # 2. Add to Local DB (for immediate search)
    STUDENT_DB[uuid] = {
        'name': name,
        'branch': branch,
        'email': email,
        'id': uuid,
        'status': 'pending',
        'time': None
    }
    
    # 3. Generate QR Code
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uuid)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for display & bytes for email
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    qr_b64 = base64.b64encode(img_bytes).decode('ascii')
    
    # 4. Send Email (Optional)
    email_status = "Not Sent"
    if data.get('send_email'):
        if send_invitation_email(name, email, branch, uuid, img_bytes):
            email_status = "Sent Successfully"
        else:
            email_status = "Failed to Send"

    return jsonify({
        "status": "success", 
        "message": "Student Added",
        "email_status": email_status,
        "student": student_data,
        "qr_code": f"data:image/png;base64,{qr_b64}"
    })

if __name__ == '__main__':
    # Host on 0.0.0.0 to allow access from mobile on same network
    # Run with SSL (adhoc) to allow camera permissions on mobile
    app.run(debug=True, host='0.0.0.0', port=5001, ssl_context='adhoc')
