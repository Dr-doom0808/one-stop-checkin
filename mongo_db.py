from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import datetime

class MongoDB:
    def __init__(self, connection_string, db_name="fresher_db", collection_name="students"):
        self.connection_string = connection_string
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        
        try:
            # Fix SSL Certificate Error by allowing invalid certificates (common in some environments)
            self.client = MongoClient(connection_string, tlsAllowInvalidCertificates=True)
            # The ismaster command is cheap and does not require auth.
            self.client.admin.command('ismaster')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            print(f"Successfully connected to MongoDB: {db_name}")
        except ConnectionFailure as e:
            print(f"MongoDB Connection Error: {e}")
            raise e

    def load_students(self):
        """
        Fetches all records from MongoDB and converts them to the app's dictionary format.
        """
        print("Fetching data from MongoDB...")
        student_db = {}
        try:
            # Find all documents, excluding the internal _id field
            cursor = self.collection.find({})
            
            for doc in cursor:
                uid = str(doc.get('UUID', '')).strip()
                if uid:
                    # Determine status
                    status = doc.get('status', 'pending')
                    if not status: status = 'pending'
                    
                    check_in_time = doc.get('Entry_time', None)
                    
                    student_db[uid] = {
                        'name': doc.get('NAME', 'Unknown'),
                        'branch': doc.get('BRANCH', 'Unknown'),
                        'email': doc.get('EMAIL', ''),
                        'id': uid,
                        'status': status.lower(),
                        'time': check_in_time
                    }
            
            print(f"Loaded {len(student_db)} students from MongoDB.")
            return student_db
        except Exception as e:
            print(f"Error loading students from MongoDB: {e}")
            return {}

    def mark_present(self, uid):
        """
        Updates the student's status to 'present' in MongoDB.
        """
        timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
        
        try:
            result = self.collection.update_one(
                {'UUID': uid},
                {'$set': {
                    'status': 'present',
                    'Entry_time': timestamp
                }}
            )
            
            if result.modified_count > 0:
                print(f"Updated MongoDB for {uid}")
            else:
                print(f"No document updated for {uid} (might not exist).")
                
        except Exception as e:
            print(f"Error updating MongoDB for {uid}: {e}")

    def add_student(self, student_data):
        """
        Adds a new student to MongoDB.
        student_data: {'NAME': ..., 'EMAIL': ..., 'BRANCH': ..., 'UUID': ..., 'status': 'pending'}
        """
        try:
            self.collection.insert_one(student_data)
            print(f"Successfully added student: {student_data.get('NAME')}")
            return True
        except Exception as e:
            print(f"Error adding student: {e}")
            return False