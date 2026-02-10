from pymongo import MongoClient
import sys

# The connection string currently in use
uri = "mongodb+srv://vinayaitm273209_db_user:NIET273209@cluster0.gjw99vq.mongodb.net/"

print("------------------------------------------------")
print("Testing MongoDB Connection...")
print(f"User: vinayaitm273209_db_user")
print("------------------------------------------------")

try:
    client = MongoClient(uri, tlsAllowInvalidCertificates=True)
    # Trigger a command to test authentication
    client.admin.command('ismaster')
    print("✅ SUCCESS! Authentication verified.")
    
    # Check for the specific database
    print("Checking databases...")
    dbs = client.list_database_names()
    print(f"Databases found: {dbs}")
    
    if "student_event" in dbs:
        print("✅ Found 'student_event' database.")
        cols = client["student_event"].list_collection_names()
        print(f"Collections in 'student_event': {cols}")
    else:
        print("⚠️ 'student_event' database NOT found in the list.")
        
except Exception as e:
    print("❌ FAILED: Authentication Error")
    print(f"Error Details: {e}")
    print("\nPossible fixes:")
    print("1. Go to MongoDB Atlas -> Database Access")
    print("2. Click 'Edit' on your user")
    print("3. Check the username spelling")
    print("4. Reset the password and update it here")