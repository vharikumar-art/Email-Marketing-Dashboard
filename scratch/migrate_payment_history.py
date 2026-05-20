from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "email_dashboard")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def migrate_payment_history():
    print(f"Starting migration to payment_history collection in database: {DB_NAME}")
    
    payments_coll = db["payments"]
    clients_coll = db["clients"]
    orders_coll = db["orders"]
    history_coll = db["payment_history"]
    
    # Clear existing history to start fresh with correct data
    print("Clearing existing payment_history...")
    history_coll.delete_many({}) 
    
    # Get all payments
    payments = list(payments_coll.find({}))
    print(f"Found {len(payments)} payment records to migrate.")
    
    migrated_count = 0
    skipped_count = 0
    
    for p in payments:
        order_id = p.get("order_id")
        if not order_id:
            print(f"Skipping payment without order_id: {p.get('_id')}")
            skipped_count += 1
            continue
            
        # Fetch related client and order for denormalization
        order_doc = orders_coll.find_one({"order_id": order_id})
        
        if not order_doc:
            print(f"Order not found for payment: {order_id}")
            skipped_count += 1
            continue
            
        # Resolve client_id: first from payment, then from order
        client_id = p.get("client_id") or order_doc.get("client_id")
        client_doc = clients_coll.find_one({"client_id": client_id})
        
        history_item = {
            "client_name": client_doc.get("name") if client_doc else "Unknown Client",
            "client_id": client_id,
            "order_id": order_id,
            "reference_id": p.get("reference_id") or order_doc.get("reference_id"),
            "amount": p.get("amount") or order_doc.get("total_amount") or 0.0,
            "paid_amount": p.get("paid_amount") or 0.0,
            "payment_date": p.get("payment_date") or p.get("created_at") or datetime.utcnow(),
            "payment_received_account": p.get("payment_received_account"),
            "order_title": order_doc.get("title") or "Unknown Title",
            
            "phase_1_payment": p.get("phase_1_payment", 0.0),
            "phase_1_payment_date": p.get("phase_1_payment_date"),
            "phase_1_payment_details": p.get("phase_1_payment_details"),
            
            "phase_2_payment": p.get("phase_2_payment", 0.0),
            "phase_2_payment_date": p.get("phase_2_payment_date"),
            "phase_2_payment_details": p.get("phase_2_payment_details"),
            
            "phase_3_payment": p.get("phase_3_payment", 0.0),
            "phase_3_payment_date": p.get("phase_3_payment_date"),
            "phase_3_payment_details": p.get("phase_3_payment_details"),
            
            "created_at": p.get("created_at") or datetime.utcnow()
        }
        
        history_coll.insert_one(history_item)
        migrated_count += 1
        
        if migrated_count % 10 == 0:
            print(f"Migrated {migrated_count} records...")

    print(f"\nMigration complete!")
    print(f"Total Migrated: {migrated_count}")
    print(f"Total Skipped: {skipped_count}")

if __name__ == "__main__":
    migrate_payment_history()
