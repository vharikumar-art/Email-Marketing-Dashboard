from database import db, client
from config import DB_NAME

def clear_database():
    print(f"Connecting to database: {DB_NAME}...")
    
    # Collections to keep
    keep_collections = ["users", "tokens"]
    
    # Get all collection names
    collections = db.list_collection_names()
    
    for coll_name in collections:
        if coll_name in keep_collections:
            print(f"Skipping collection: {coll_name}")
            continue
            
        print(f"Clearing collection: {coll_name}...")
        result = db[coll_name].delete_many({})
        print(f"Deleted {result.deleted_count} documents from {coll_name}.")

    print("\nDatabase cleanup complete (Users and Tokens preserved).")

if __name__ == "__main__":
    confirm = input("Are you sure you want to clear all data except users and tokens? (y/n): ")
    if confirm.lower() == 'y':
        clear_database()
    else:
        print("Cleanup cancelled.")
