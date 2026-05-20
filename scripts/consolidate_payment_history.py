#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Setup paths to import from app
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "app"))

from pymongo import MongoClient
from app.config import MONGO_URI, DB_NAME

def consolidate_history():
    print("Starting payment history consolidation...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    payment_history_collection = db["payment_history"]
    orders_collection = db["orders"]
    clients_collection = db["clients"]
    payments_collection = db["payments"]
    
    # 1. Group existing history by order_id
    all_history = list(payment_history_collection.find({}))
    print(f"Found {len(all_history)} total history records.")
    
    history_by_order = {}
    for record in all_history:
        order_id = record.get("order_id")
        if not order_id:
            continue
        if order_id not in history_by_order:
            history_by_order[order_id] = []
        history_by_order[order_id].append(record)
        
    print(f"Grouped into {len(history_by_order)} unique orders.")
    
    consolidated_count = 0
    
    for order_id, records in history_by_order.items():
        # Retrieve the source of truth documents
        order = orders_collection.find_one({"order_id": order_id})
        if not order:
            print(f"Order {order_id} not found in orders collection. Skipping consolidation.")
            continue
            
        client_doc = clients_collection.find_one({"client_id": order["client_id"]})
        client_name = client_doc.get("name") if client_doc else "Unknown Client"
        
        payment = payments_collection.find_one({"order_id": order_id})
        
        # Merge all historical records (newest values override oldest)
        records_sorted = sorted(records, key=lambda x: x.get("created_at") or datetime.min)
        
        merged = {}
        for r in records_sorted:
            clean_r = {k: v for k, v in r.items() if k not in ["_id", "created_at", "updated_at"]}
            merged.update(clean_r)
            
        # Ensure latest metadata from main collections
        merged.update({
            "client_name": client_name,
            "client_id": order["client_id"],
            "order_id": order_id,
            "reference_id": order.get("reference_id"),
            "order_title": order.get("title") or "Unknown Title",
            "amount": order.get("total_amount", 0.0),
        })
        
        # Populate any missing payment fields from payments collection if available
        if payment:
            payment_fields = [
                "paid_amount", "payment_date", "payment_received_account",
                "phase_1_payment", "phase_1_payment_date", "phase_1_payment_details",
                "phase_2_payment", "phase_2_payment_date", "phase_2_payment_details",
                "phase_3_payment", "phase_3_payment_date", "phase_3_payment_details"
            ]
            for field in payment_fields:
                if field in payment and merged.get(field) is None:
                    merged[field] = payment[field]
                    
        merged["updated_at"] = datetime.utcnow()
        created_times = [r.get("created_at") for r in records if r.get("created_at")]
        merged["created_at"] = min(created_times) if created_times else datetime.utcnow()
        
        # Delete old records and insert single consolidated record
        payment_history_collection.delete_many({"order_id": order_id})
        payment_history_collection.insert_one(merged)
        consolidated_count += 1
        
    print(f"Successfully consolidated into {consolidated_count} payment history records.")
    client.close()

if __name__ == "__main__":
    consolidate_history()
