import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import threading

class GoogleSheetsDB:
    def __init__(self, credentials_file, sheet_name):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, self.scope)
        self.client = gspread.authorize(self.creds)
        try:
            self.sheet = self.client.open(sheet_name).sheet1
            print(f"Successfully connected to Google Sheet: {sheet_name}")
        except Exception as e:
            print(f"Error opening sheet '{sheet_name}': {e}")
            raise e
        
        # Cache to store UUID -> Row Number mapping for faster updates
        self.uuid_row_map = {}

    def load_students(self):
        """
        Fetches all records from the Google Sheet and converts them to the app's dictionary format.
        """
        print("Fetching data from Google Sheets... (This might take a few seconds)")
        records = self.sheet.get_all_records()
        
        student_db = {}
        # Clean keys (strip spaces)
        cleaned_records = []
        
        # We need to find which column holds the UUID to build our map
        # Assuming column headers are in the first row (get_all_records handles this)
        # But we need to know the index for cell updates.
        # get_all_records returns list of dicts.
        
        # Let's build the DB and the Row Map
        # Row 1 is headers. Data starts at Row 2.
        for idx, row in enumerate(records, start=2):
            # specific logic to handle the keys as they might have spaces
            clean_row = {k.strip(): v for k, v in row.items()}
            
            uid = str(clean_row.get('UUID', '')).strip()
            if uid:
                self.uuid_row_map[uid] = idx
                
                # Determine status based on 'Status' column if it exists, else default
                status = clean_row.get('Status', 'pending')
                if not status: status = 'pending'
                
                check_in_time = clean_row.get('CheckInTime', None)
                if not check_in_time: check_in_time = None

                student_db[uid] = {
                    'name': clean_row.get('NAME', 'Unknown'),
                    'branch': clean_row.get('BRANCH', 'Unknown'),
                    'email': clean_row.get('EMAIL-ID', ''),
                    'id': uid,
                    'status': status.lower(),
                    'time': check_in_time
                }
                
        print(f"Loaded {len(student_db)} students from Google Sheets.")
        return student_db

    def mark_present(self, uid):
        """
        Updates the student's status to 'present' in the Google Sheet.
        Runs in a background thread to avoid blocking the scanner.
        """
        if uid not in self.uuid_row_map:
            print(f"Error: UUID {uid} not found in row map.")
            return

        row_num = self.uuid_row_map[uid]
        timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
        
        def update_task():
            try:
                # Assuming 'Status' is column 5 and 'CheckInTime' is column 6
                # We should dynamically find columns, but for now let's assume standard format
                # Or safer: find the cell by header.
                
                # Better approach: find column index by header name
                headers = self.sheet.row_values(1)
                headers = [h.strip() for h in headers]
                
                try:
                    status_col = headers.index('Status') + 1
                    time_col = headers.index('CheckInTime') + 1
                except ValueError:
                    # If columns don't exist, we might need to add them or hardcode
                    # Let's fallback to hardcoded if specific headers aren't found
                    # Assuming: NAME, EMAIL-ID, BRANCH, UUID, Status, CheckInTime
                    status_col = 5
                    time_col = 6
                
                self.sheet.update_cell(row_num, status_col, 'present')
                self.sheet.update_cell(row_num, time_col, timestamp)
                print(f"Updated Google Sheet for {uid}")
            except Exception as e:
                print(f"Failed to update Google Sheet: {e}")

        # Start the background thread
        thread = threading.Thread(target=update_task)
        thread.start()
