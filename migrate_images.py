"""
One-time migration script: MongoDB binary blobs → filesystem files
==================================================================
Run this ONCE to move existing photo_data / receipt_phase_N_data binary
blobs out of MongoDB and into static/uploads/ on disk.

Usage (from project root):
    python migrate_images.py

What it does:
  - Reads users with photo_data → saves to static/uploads/users/
  - Reads clients with photo_data → saves to static/uploads/clients/
  - Reads orders with receipt_phase_N_data → saves to static/uploads/receipts/
  - Updates MongoDB documents with the new path fields
  - Removes (unsets) the old binary fields
"""

import os
import uuid
from pymongo import MongoClient
from app.config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
clients_col = db["clients"]
orders_col = db["orders"]


def save_bytes(content: bytes, mime: str, subfolder: str) -> str:
    ext = ".jpg" if "jpeg" in mime else ".png" if "png" in mime else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dir_path = os.path.join("static", "uploads", subfolder)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return f"static/uploads/{subfolder}/{filename}"


def migrate_users():
    print("\n[1/3] Migrating user photos...")
    count = 0
    for user in users_col.find({"photo_data": {"$exists": True}}):
        raw = user.get("photo_data")
        if not raw:
            continue
        mime = user.get("photo_mime", "image/jpeg")
        try:
            photo_path = save_bytes(bytes(raw), mime, "users")
            users_col.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {"photo_path": photo_path},
                    "$unset": {"photo_data": ""}
                }
            )
            count += 1
        except Exception as e:
            print(f"  ERROR for user {user.get('email')}: {e}")
    print(f"  Migrated {count} user photo(s).")


def migrate_clients():
    print("\n[2/3] Migrating client photos...")
    count = 0
    for cli in clients_col.find({"photo_data": {"$exists": True}}):
        raw = cli.get("photo_data")
        if not raw:
            continue
        mime = cli.get("photo_mime", "image/jpeg")
        try:
            photo_path = save_bytes(bytes(raw), mime, "clients")
            clients_col.update_one(
                {"_id": cli["_id"]},
                {
                    "$set": {"photo_path": photo_path},
                    "$unset": {"photo_data": ""}
                }
            )
            count += 1
        except Exception as e:
            print(f"  ERROR for client {cli.get('client_id')}: {e}")
    print(f"  Migrated {count} client photo(s).")


def migrate_receipts():
    print("\n[3/3] Migrating order receipts...")
    count = 0
    # Find orders that have any receipt binary
    query = {"$or": [
        {f"receipt_phase_{p}_data": {"$exists": True}} for p in (1, 2, 3)
    ]}
    for order in orders_col.find(query):
        set_fields = {}
        unset_fields = {}
        for phase in (1, 2, 3):
            raw = order.get(f"receipt_phase_{phase}_data")
            if not raw:
                continue
            mime = order.get(f"receipt_phase_{phase}_mime", "image/jpeg")
            try:
                receipt_path = save_bytes(bytes(raw), mime, "receipts")
                set_fields[f"receipt_phase_{phase}_path"] = receipt_path
                unset_fields[f"receipt_phase_{phase}_data"] = ""
                count += 1
            except Exception as e:
                print(f"  ERROR for order {order.get('order_id')} phase {phase}: {e}")

        if set_fields:
            orders_col.update_one(
                {"_id": order["_id"]},
                {"$set": set_fields, "$unset": unset_fields}
            )
    print(f"  Migrated {count} receipt image(s).")


if __name__ == "__main__":
    print("=" * 60)
    print("  Image Migration: MongoDB Binary → Filesystem")
    print("=" * 60)
    migrate_users()
    migrate_clients()
    migrate_receipts()
    print("\nDone! All images migrated.")
    print("You can now restart the server and images will be served from disk.")
