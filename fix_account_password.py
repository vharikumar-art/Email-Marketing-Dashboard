"""
One-time fix: Re-encrypts the password for a specific user account
using the current ENCRYPTION_KEY from .env
"""

import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from pymongo import MongoClient

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
TARGET_EMAIL    = "vharikumar.art@gmail.com"   # the broken account
KNOWN_PASSWORD  = "Hari@1234"                  # the correct plain-text password
# ──────────────────────────────────────────────────────────────────────────────

MONGO_URI      = os.getenv("MONGO_URI")
DB_NAME        = os.getenv("DB_NAME")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    print("[ERR]  ENCRYPTION_KEY not found in .env")
    exit(1)

# Connect
client = MongoClient(MONGO_URI)
db     = client[DB_NAME]
users  = db["users"]

# Find user
user = users.find_one({"email": TARGET_EMAIL})
if not user:
    print(f"[ERR]  User '{TARGET_EMAIL}' not found in the database.")
    exit(1)

print(f"[OK]  Found user: {user.get('email')}  (role: {user.get('role')})")
print(f"   Current stored password (raw): {user.get('password', '<empty>')[:60]}...")

# Encrypt with current key
fernet           = Fernet(ENCRYPTION_KEY.encode("utf-8"))
new_encrypted_pw = fernet.encrypt(KNOWN_PASSWORD.encode("utf-8")).decode("utf-8")

# Verify it round-trips correctly before writing
decrypted_check = fernet.decrypt(new_encrypted_pw.encode("utf-8")).decode("utf-8")
assert decrypted_check == KNOWN_PASSWORD, "Round-trip check failed!"

# Update
result = users.update_one(
    {"email": TARGET_EMAIL},
    {"$set": {"password": new_encrypted_pw}}
)

if result.modified_count == 1:
    print(f"\n[OK]  Password for '{TARGET_EMAIL}' has been re-encrypted and updated successfully.")
    print(f"   New encrypted value starts with: {new_encrypted_pw[:40]}...")
    print("\n-->  You can now log in with:")
    print(f"   Email   : {TARGET_EMAIL}")
    print(f"   Password: {KNOWN_PASSWORD}")
else:
    print("[WARN]  Update ran but no document was modified (already correct?)")

client.close()
