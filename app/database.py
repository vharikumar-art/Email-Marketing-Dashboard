from pymongo import MongoClient
from app.config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
tokens_collection = db["tokens"]
clients_collection = db["clients"]
orders_collection = db["orders"]
manuscripts_collection = db["manuscripts"]
payments_collection = db["payments"]
payment_history_collection = db["payment_history"]
otps_collection = db["otps"]

# --- INDEXES FOR PERFORMANCE ---
users_collection.create_index("email", unique=True)
users_collection.create_index("full_name")
users_collection.create_index("role")
clients_collection.create_index("client_id", unique=True)
clients_collection.create_index("client_handler")
orders_collection.create_index("client_id")
orders_collection.create_index("order_id", unique=True)
orders_collection.create_index("reference_id")
orders_collection.create_index("s_no")  # For dashboard ordering
orders_collection.create_index("order_date")  # For dashboard filtering
orders_collection.create_index([("client_id", 1), ("order_id", 1)])  # Compound for aggregation lookup
payments_collection.create_index([("order_id", 1), ("phase", 1)])
payments_collection.create_index("client_id")
payments_collection.create_index("order_id")  # Separate index for lookups
payments_collection.create_index("phase")  # For phase filtering in aggregation

# Payment History Indexes
payment_history_collection.create_index("client_id")
payment_history_collection.create_index("order_id") # Removed unique=True to allow append-only history
payment_history_collection.create_index("payment_date")

# Token Indexes
tokens_collection.create_index("token", unique=True)
tokens_collection.create_index("created_at", expireAfterSeconds=36000) # 10 hours (matches ACCESS_TOKEN_EXPIRE_MINUTES)
