from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "email_dashboard")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def migrate_orders():
    print(f"Connecting to database: {DB_NAME}")
    orders_collection = db["orders"]
    
    # Update all existing orders that don't have is_new_order field
    result = orders_collection.update_many(
        {"is_new_order": {"$exists": False}},
        {"$set": {"is_new_order": "no"}}
    )
    
    print(f"Migration complete. Updated {result.modified_count} orders.")

if __name__ == "__main__":
    migrate_orders()
