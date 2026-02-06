import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Configuration
EXCEL_FILE = 'Students_Data_500.xlsx'
GOOGLE_CREDS = 'credentials.json'
SHEET_NAME = 'Fresher Induction 2026'

def upload_data():
    print("--- Uploading Data to Google Sheets ---")
    
    # 1. Check files
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: '{EXCEL_FILE}' not found.")
        return
    if not os.path.exists(GOOGLE_CREDS):
        print(f"❌ Error: '{GOOGLE_CREDS}' not found.")
        return

    # 2. Read Excel
    print(f"Reading '{EXCEL_FILE}'...")
    try:
        df = pd.read_excel(EXCEL_FILE)
        # Clean columns
        df.columns = [c.strip() for c in df.columns]
        
        # Ensure required columns exist
        required_cols = ['NAME', 'EMAIL-ID', 'BRANCH', 'UUID']
        for col in required_cols:
            if col not in df.columns:
                print(f"❌ Error: Column '{col}' missing in Excel.")
                return
                
        # Add Status and CheckInTime columns if they don't exist
        if 'Status' not in df.columns:
            df['Status'] = 'pending'
        if 'CheckInTime' not in df.columns:
            df['CheckInTime'] = ''
            
        # Fill NaN with empty string for Google Sheets
        df = df.fillna('')
        
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return

    # 3. Connect to Google Sheets
    print("Connecting to Google Sheets...")
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
        return

    # 4. Upload Data
    print(f"Uploading {len(df)} records to '{SHEET_NAME}'...")
    print("This may take a minute...")
    
    try:
        # Clear existing data
        sheet.clear()
        
        # Update with new data (headers + rows)
        # Convert DataFrame to list of lists
        data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(data)
        
        print("✅ Upload Complete!")
        print("   The Google Sheet is now populated and ready for the app.")
        
    except Exception as e:
        print(f"❌ Error uploading data: {e}")

if __name__ == "__main__":
    upload_data()