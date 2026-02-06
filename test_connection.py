from sheets_db import GoogleSheetsDB
import os

GOOGLE_CREDS = 'credentials.json'
SHEET_NAME = 'Fresher Induction 2026'

print("--- Google Sheets Connection Test ---")

if not os.path.exists(GOOGLE_CREDS):
    print(f"❌ Error: '{GOOGLE_CREDS}' file not found.")
    print("   Please ensure you have placed the credentials.json file in the project folder.")
    exit(1)

print(f"✅ Found '{GOOGLE_CREDS}'.")
print(f"Attempting to connect to Sheet: '{SHEET_NAME}'...")

try:
    db = GoogleSheetsDB(GOOGLE_CREDS, SHEET_NAME)
    print("✅ Connection Successful!")
    
    print("Attempting to load students to verify permissions...")
    students = db.load_students()
    print(f"✅ Successfully loaded {len(students)} students.")
    print("\n🎉 You are ready to run the main application!")
    
except Exception as e:
    print("\n❌ Connection Failed!")
    print(f"Error details: {e}")
    print("\nTroubleshooting:")
    print("1. Share the sheet with: niet-fresher@niet-fresher-26.iam.gserviceaccount.com")
    print("2. Ensure the sheet name is EXACTLY 'Fresher Induction 2026'.")
    print("3. Ensure dependencies are installed: pip install gspread oauth2client")