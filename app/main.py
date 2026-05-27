from typing import Optional, Any
import re
import os

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from app.schemas import (
    UserCreate, 
    UserResponse, 
    UserDetailResponse,
    LoginRequest, 
    Token, 
    UserRole, 
    PasswordUpdate, 
    AdminPasswordUpdate,
    ClientCreate,
    ClientResponse,
    ManuscriptCreate,
    ManuscriptResponse,
    OrderCreate,
    OrderResponse,
    PaymentCreate,
    PaymentResponse,
    DashboardOrderResponse,
    LoginResponse,
    OTPVerifyRequest,
    PermissionUpdate,
    ProfileUpdate,
    UserProfileUpdate,
    DashboardUpdate,
    ApiResponse,
    ClientAssignRequest,
    UnifiedCreateRequest,
    PaymentHistoryItem,
    PendingSummaryResponse,
    PendingClientDetail,
    ORDER_TYPE_OPTIONS,
    CurrencyConvertRequest,
    ClientFullResponse,
    ClientOrderSummary,
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse
)
import random
import smtplib
from email.message import EmailMessage
import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import (
    SMTP_SERVER, 
    SMTP_PORT, 
    SMTP_USERNAME, 
    SMTP_PASSWORD, 
    EMAIL_FROM,
    ALLOWED_ORIGINS,
    OTP_ENABLED
)
from app.auth import (
    encrypt_password,
    decrypt_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    require_manager_or_higher,
    oauth2_scheme
)
from app.database import (
    users_collection, 
    tokens_collection,
    clients_collection,
    manuscripts_collection,
    orders_collection,
    payments_collection, 
    payment_history_collection,
    otps_collection,
    settings_collection,
    bank_accounts_collection
)

from app.currency_converter import convert_inr_to_usd, convert_usd_to_inr, get_current_rate_info, convert_currency
from bson import ObjectId
from bson.binary import Binary


app = FastAPI(title="Email Dashboard API")

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# --- PERFORMANCE MONITORING MIDDLEWARE ---
class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log slow requests (>1 second)
        if process_time > 1.0:
            print(f"[SLOW] SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}s")
        elif process_time > 0.5:
            print(f"[WARNING] MEDIUM REQUEST: {request.method} {request.url.path} took {process_time:.2f}s")
        
        return response

app.add_middleware(PerformanceMiddleware)


# --- CUSTOM EXCEPTION HANDLERS ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "status": "error",
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "status": "error",
            "message": "Internal Server Error",
            "data": str(exc) if "DEV" in str(request.headers) else None
        }
    )

# --- HELPER ---
def is_otp_enabled() -> bool:
    """
    Check if OTP authentication is enabled.
    Checks database settings first, then falls back to SMTP / config settings.
    """
    setting = settings_collection.find_one({"key": "otp_enabled"})
    if setting is not None:
        return bool(setting.get("value", True))
    return OTP_ENABLED

async def send_otp_email(to_email: str, otp: str):
    """
    Sends an OTP email via SMTP asynchronously.
    """
    msg = EmailMessage()
    msg.set_content(f"Your OTP for login is: {otp}\n\nThis OTP is valid for 5 minutes.")
    msg["Subject"] = "Login OTP - Email Dashboard"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    # DEBUG: Print OTP for testing purposes
    print(f"\n[SECURE] [TEST OTP] For email {to_email}: {otp}")
    print("[WARNING] This OTP is printed for testing only!\n")

    print(f"\n[OTP DEBUG] Attempting to send email to {to_email} via {SMTP_SERVER}:{SMTP_PORT}\n")
    try:
        import aiosmtplib
    except ImportError as e:
        print(f"AIOSMTPLIB_MISSING: {e}")
        return False

    try:
        if SMTP_PORT == 465:
            # Port 465 requires SMTP_SSL from the start
            server = aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT, use_tls=True)
            await server.connect()
            await server.login(SMTP_USERNAME, SMTP_PASSWORD)
            await server.send_message(msg)
            await server.quit()
        else:
            # Port 587 (and others) typically use STARTTLS
            server = aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT)
            await server.connect()
            await server.start_tls()
            await server.login(SMTP_USERNAME, SMTP_PASSWORD)
            await server.send_message(msg)
            await server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def format_mongo_id(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def parse_date(date_str: Any) -> Optional[datetime]:
    """Helper to convert string dates to datetime objects for MongoDB."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    try:
        # Handle simple date strings like "2024-01-01"
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d")
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return None

def resolve_client_handler(client: dict) -> dict:
    """
    Resolves client_handler (email) to client_handler_name (full_name) for display.
    client_handler stores the employee's email for uniqueness.
    client_handler_name is the human-readable full name shown on the frontend.
    """
    handler_email = client.get("client_handler")
    if handler_email:
        handler_user = users_collection.find_one({"email": handler_email})
        client["client_handler_name"] = handler_user.get("full_name") if handler_user else handler_email
    else:
        client["client_handler_name"] = None
    return client

def resolve_client_handler_bulk(clients: list[dict]) -> list[dict]:
    """Resolve handler names for many clients with a single DB query."""
    emails = {client.get("client_handler") for client in clients if client.get("client_handler")}
    if not emails:
        for client in clients:
            client["client_handler_name"] = None
        return clients

    handlers = users_collection.find({"email": {"$in": list(emails)}}, {"email": 1, "full_name": 1, "phone_number": 1})
    email_to_handler = {handler["email"]: handler for handler in handlers}
    for client in clients:
        handler_email = client.get("client_handler")
        if handler_email and handler_email in email_to_handler:
            client["client_handler_name"] = email_to_handler[handler_email].get("full_name", handler_email)
            client["client_handler_phone_number"] = email_to_handler[handler_email].get("phone_number")
        else:
            client["client_handler_name"] = None
            client["client_handler_phone_number"] = None
    return clients

def get_user_email_by_name(name_or_email: str) -> str:
    """
    Finds a user's email by their full name or returns the input if it's already an email.
    """
    if not name_or_email:
        return name_or_email
        
    # If it looks like an email, return as is
    if "@" in name_or_email:
        return name_or_email
        
    # Try to find user by full name
    user = users_collection.find_one({"full_name": name_or_email})
    if user:
        return user.get("email")
        
    return name_or_email


def generate_custom_id(prefix: str, collection, current_user: dict):
    """
    Generates a unique ID based on the user's assigned range.
    Format: {prefix}-{YYYY}-{num}
    """
    year = datetime.utcnow().strftime("%Y")
    
    # 1. Determine range
    if current_user["role"] == UserRole.ADMIN:
        start, end = 1, 9999
    else:
        # Default range if not set
        start = current_user.get("id_range_start", 100)
        end = current_user.get("id_range_end", 200)
    
    # 2. Find existing IDs in this range for this year
    field_name = "client_id" if prefix == "CL" else "reference_id"
    pattern = f"^{prefix}-{year}-(\\d+)$"
    
    cursor = collection.find({
        field_name: {"$regex": pattern}
    })
    
    existing_nums = []
    for doc in cursor:
        val = doc.get(field_name)
        match = re.search(f"{prefix}-{year}-(\\d+)", val)
        if match:
            num = int(match.group(1))
            if start <= num <= end:
                existing_nums.append(num)
    
    # 3. Find next available number
    if not existing_nums:
        next_num = start
    else:
        next_num = max(existing_nums) + 1
        
    if next_num > end:
        raise HTTPException(
            status_code=400,
            detail=f"Limit reached for your assigned ID range ({start}-{end}). Please contact Admin."
        )
        
    return f"{prefix}-{year}-{next_num:04d}"

def is_id_range_overlapping(start: int, end: int, exclude_email: Optional[str] = None):
    """
    Checks if a given ID range overlaps with any existing user's range.
    """
    if start is None or end is None:
        return False
        
    query = {
        "role": UserRole.EMPLOYEE,
        "id_range_start": {"$exists": True},
        "id_range_end": {"$exists": True}
    }
    if exclude_email:
        query["email"] = {"$ne": exclude_email}
        
    existing_users = users_collection.find(query)
    
    for user in existing_users:
        e_start = user.get("id_range_start")
        e_end = user.get("id_range_end")
        
        if e_start is None or e_end is None:
            continue
            
        # Check for overlap: (StartA <= EndB) and (EndA >= StartB)
        if (start <= e_end) and (end >= e_start):
            return user.get("email")
            
    return None



@app.get("/", response_model=ApiResponse[dict])
def read_root():
    return {
        "status_code": 200,
        "status": "success",
        "message": "Welcome to Email Dashboard API",
        "data": None
    }

# --- CURRENCY CONVERSION ---

@app.get("/currency/exchange-rate", response_model=ApiResponse[dict])
def get_exchange_rate():
    """
    Get current INR to USD exchange rate with caching.
    """
    rate_info = get_current_rate_info()
    if not rate_info:
        raise HTTPException(
            status_code=503,
            detail="Exchange rate service unavailable"
        )
    return {
        "status_code": 200,
        "status": "success",
        "message": "Exchange rate fetched successfully",
        "data": rate_info
    }

@app.post("/currency/inr-to-usd", response_model=ApiResponse[dict])
def convert_inr_to_usd_endpoint(amount: dict):
    """
    Convert amount from INR to USD.
    Request: {"amount_inr": 1000}
    Response includes current rate and converted amount.
    """
    amount_inr = amount.get("amount_inr")
    if amount_inr is None or amount_inr < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid amount_inr. Must be a positive number."
        )
    
    result = convert_inr_to_usd(float(amount_inr))
    if not result:
        raise HTTPException(
            status_code=503,
            detail="Exchange rate service unavailable"
        )
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Conversion completed successfully",
        "data": result
    }

@app.post("/currency/usd-to-inr", response_model=ApiResponse[dict])
def convert_usd_to_inr_endpoint(amount: dict):
    """
    Convert amount from USD to INR.
    Request: {"amount_usd": 15}
    Response includes current rate and converted amount.
    """
    amount_usd = amount.get("amount_usd")
    if amount_usd is None or amount_usd < 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid amount_usd. Must be a positive number."
        )
    
    result = convert_usd_to_inr(float(amount_usd))
    if not result:
        raise HTTPException(
            status_code=503,
            detail="Exchange rate service unavailable"
        )
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Conversion completed successfully",
        "data": result
    }

@app.post("/currency/convert", response_model=ApiResponse[dict])
def convert_currency_endpoint(request: CurrencyConvertRequest):
    """
    Convert amount between any supported currencies (USD, INR, CNY, AED, SAR).
    """
    result = convert_currency(request.amount, request.from_currency, request.to_currency)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Currency conversion failed. Verify the input parameters."
        )
    return {
        "status_code": 200,
        "status": "success",
        "message": "Conversion completed successfully",
        "data": result
    }

# --- INITIALIZATION ---

@app.post("/init-super-admin", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def init_super_admin(user: UserCreate):
    """
    Endpoint to initialize the first super admin users. 
    Works if fewer than 5 admins exist in the database.
    """
    admin_count = users_collection.count_documents({"role": UserRole.ADMIN})
    if admin_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Maximum of 5 Admins already exist"
        )
    
    user_dict = user.model_dump()
    user_dict["password"] = encrypt_password(user.password)
    user_dict["role"] = UserRole.ADMIN
    users_collection.insert_one(user_dict)
    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Super Admin created successfully",
        "data": None
    }

# --- LOGIN ---

@app.post("/login", response_model=ApiResponse[LoginResponse])
async def login(request: LoginRequest):
    """
    Shared login endpoint. Admins and Managers require OTP.
    Employees login directly.
    """
    user = users_collection.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if role requires OTP (Admin and Manager)
    if is_otp_enabled() and user["role"] in [UserRole.ADMIN, UserRole.MANAGER]:
        otp = str(random.randint(100000, 999999))
        
        # Store OTP
        otps_collection.update_one(
            {"email": user["email"]},
            {"$set": {
                "otp": otp,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        # Send OTP asynchronously
        sent = await send_otp_email(user["email"], otp)
        
        return {
            "status_code": 200,
            "status": "success",
            "message": "OTP required move to verify-otp",
            "data": LoginResponse(otp_required=True, email=user["email"])
        }

    # Regular login for Employee
    access_token = create_access_token(data={"sub": user["email"]})
    
    # Store token
    tokens_collection.insert_one({
        "user_email": user["email"],
        "token": access_token,
        "created_at": datetime.utcnow()
    })
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Login successful",
        "data": LoginResponse(access_token=access_token, token_type="bearer")
    }

@app.post("/verify-otp", response_model=ApiResponse[Token])
def verify_otp(request: OTPVerifyRequest):
    """
    Verify OTP for Admin/Manager login.
    """
    # Check OTP record
    otp_record = otps_collection.find_one({"email": request.email})
    
    if not otp_record or otp_record["otp"] != request.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # OTP is valid, check expiration (e.g., 5 minutes)
    if datetime.utcnow() - otp_record["created_at"] > timedelta(minutes=5):
        otps_collection.delete_one({"email": request.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP has expired"
        )
    
    # OTP verified, issue token
    user = users_collection.find_one({"email": request.email})
    access_token = create_access_token(data={"sub": user["email"]})
    
    # Store token
    tokens_collection.insert_one({
        "user_email": user["email"],
        "token": access_token,
        "created_at": datetime.utcnow()
    })
    
    # Clear OTP
    otps_collection.delete_one({"email": request.email})
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "OTP verified successfully",
        "data": {"access_token": access_token, "token_type": "bearer"}
    }

@app.post("/logout", response_model=ApiResponse[dict])
async def logout(token: str = Depends(oauth2_scheme), current_user: dict = Depends(get_current_user)):
    """
    Logout the current user by invalidating their token.
    """
    tokens_collection.delete_one({"token": token})
    return {
        "status_code": 200,
        "status": "success",
        "message": "Logged out successfully",
        "data": None
    }

@app.get("/otp-status", response_model=ApiResponse[dict])
def get_otp_status():
    """
    Get the current status of OTP verification (enabled/disabled).
    """
    enabled = is_otp_enabled()
    return {
        "status_code": 200,
        "status": "success",
        "message": f"OTP verification is {'enabled' if enabled else 'disabled'}",
        "data": {"otp_enabled": enabled}
    }

@app.post("/toggle-otp", response_model=ApiResponse[dict])
def toggle_otp(enabled: bool):
    """
    Enable or disable OTP verification globally.
    """
    settings_collection.update_one(
        {"key": "otp_enabled"},
        {"$set": {"value": enabled}},
        upsert=True
    )
    return {
        "status_code": 200,
        "status": "success",
        "message": f"OTP verification has been {'enabled' if enabled else 'disabled'}",
        "data": {"otp_enabled": enabled}
    }

# --- USER & ADMIN CREATION ---

@app.post("/users", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, current_user: dict = Depends(require_manager_or_higher)):
    """
    Create a new User (Admin, Manager, or Employee).
    Restricted to Super Admin and Manager. 
    One additional Admin is allowed (total 2).
    """
    # Check if user already exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Check for ID range overlap
    if user.id_range_start is not None and user.id_range_end is not None:
        overlapping_user = is_id_range_overlapping(user.id_range_start, user.id_range_end)
        if overlapping_user:
            raise HTTPException(
                status_code=400, 
                detail=f"ID range {user.id_range_start}-{user.id_range_end} overlaps with user: {overlapping_user}"
            )
    
    # Logic for Admin role restriction
    if user.role == UserRole.ADMIN:
        # Only existing Admin can create another Admin
        if current_user["role"] != UserRole.ADMIN:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can create another Admin"
            )
             
        admin_count = users_collection.count_documents({"role": UserRole.ADMIN})
        if admin_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 5 Admins allowed"
            )
            
    user_dict = user.model_dump()
    user_dict["password"] = encrypt_password(user.password)
    result = users_collection.insert_one(user_dict)
    
    user_dict["_id"] = str(result.inserted_id)
    user_dict["password"] = user.password
    return {
        "status_code": 201,
        "status": "success",
        "message": "User created successfully",
        "data": user_dict
    }

@app.post("/managers", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
def create_manager(user: UserCreate, current_user: dict = Depends(require_manager_or_higher)):
    """
    Create a new Manager.
    Restricted to Admin and Manager only.
    """
    # Check if user already exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Enforce role to be Manager
    user_dict = user.model_dump()
    user_dict["role"] = UserRole.MANAGER
    user_dict["password"] = encrypt_password(user.password)
    result = users_collection.insert_one(user_dict)
    
    user_dict["_id"] = str(result.inserted_id)
    user_dict["password"] = user.password
    return {
        "status_code": 201,
        "status": "success",
        "message": "Manager created successfully",
        "data": user_dict
    }

# --- PASSWORD MANAGEMENT ---

@app.put("/users/me/password", response_model=ApiResponse[dict])
def update_own_password(data: PasswordUpdate, current_user: dict = Depends(get_current_user)):
    """
    Update own password. Available to all roles.
    """
    hashed_password = encrypt_password(data.new_password)
    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"password": hashed_password}}
    )
    return {
        "status_code": 200,
        "status": "success",
        "message": "Password updated successfully",
        "data": None
    }

@app.put("/users/password", response_model=ApiResponse[dict])
def update_user_password(data: AdminPasswordUpdate, current_user: dict = Depends(require_manager_or_higher)):
    """
    Update a User's password. Restricted to Admin and Super Admin.
    Admins can only change USER role passwords.
    Super Admins can change ADMIN and USER role passwords.
    """
    target_user = users_collection.find_one({"email": data.email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Admin can only change EMPLOYEE passwords
    if current_user["role"] == UserRole.MANAGER:
        if target_user["role"] != UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only change Employee passwords"
            )
    
    # Super Admin can change Admin or Manager passwords
    if current_user["role"] == UserRole.ADMIN:
         if target_user["role"] == UserRole.ADMIN and target_user["email"] != current_user["email"]:
              raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot change other Admin passwords"
            )

    hashed_password = encrypt_password(data.new_password)
    users_collection.update_one(
        {"email": data.email},
        {"$set": {"password": hashed_password}}
    )
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Password for {data.email} updated successfully",
        "data": None
    }

# --- VISIBILITY ---

@app.get("/users", response_model=ApiResponse[list[UserResponse]])
def get_all_users(current_user: dict = Depends(require_manager_or_higher)):
    """
    Get all regular Users. Accessible to Admin and Super Admin.
    """
    import base64

    users = list(users_collection.find({"role": UserRole.EMPLOYEE}))
    for u in users:
        u["_id"] = str(u["_id"])
        # Decrypt password for display
        u["password"] = decrypt_password(u.get("password", ""))
        raw_photo = u.pop("photo_data", None)
        if raw_photo:
            u["photo_base64"] = base64.b64encode(bytes(raw_photo)).decode("utf-8")
            u["photo_mime"] = u.get("photo_mime", "image/png")
        else:
            u["photo_base64"] = None
            u["photo_mime"] = None
    return {
        "status_code": 200,
        "status": "success",
        "message": "Users fetched successfully",
        "data": users
    }

@app.get("/admins", response_model=ApiResponse[list[UserResponse]])
def get_all_admins(current_user: dict = Depends(require_admin)):
    """
    Get all Admins and Super Admins. Accessible to Super Admin only.
    """
    import base64

    admins = list(users_collection.find({"role": {"$in": [UserRole.MANAGER, UserRole.ADMIN]}}))
    for a in admins:
        a["_id"] = str(a["_id"])
        # Decrypt password for display
        a["password"] = decrypt_password(a.get("password", ""))
        raw_photo = a.pop("photo_data", None)
        if raw_photo:
            a["photo_base64"] = base64.b64encode(bytes(raw_photo)).decode("utf-8")
            a["photo_mime"] = a.get("photo_mime", "image/png")
        else:
            a["photo_base64"] = None
            a["photo_mime"] = None
    return {
        "status_code": 200,
        "status": "success",
        "message": "Admins fetched successfully",
        "data": admins
    }

@app.put("/users/permissions", response_model=ApiResponse[dict])
def update_user_permissions(data: PermissionUpdate, current_user: dict = Depends(require_manager_or_higher)):
    """
    Update an Employee's column-level permissions. 
    Restricted to Admin and Manager.
    """
    target_user = users_collection.find_one({"email": data.email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if target is indeed an employee
    if target_user["role"] != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permissions can only be set for Employees"
        )

    # Check for ID range overlap
    if data.id_range_start is not None and data.id_range_end is not None:
        overlapping_user = is_id_range_overlapping(data.id_range_start, data.id_range_end, exclude_email=data.email)
        if overlapping_user:
            raise HTTPException(
                status_code=400, 
                detail=f"ID range {data.id_range_start}-{data.id_range_end} overlaps with user: {overlapping_user}"
            )

    users_collection.update_one(
        {"email": data.email},
        {"$set": {
            "id_range_start": data.id_range_start,
            "id_range_end": data.id_range_end
        }}
    )

    return {
        "status_code": 200,
        "status": "success",
        "message": f"ID range updated for {data.email}",
        "data": None
    }


@app.put("/users/profile", response_model=ApiResponse[UserResponse])
@app.put("/users/{email}/profile", response_model=ApiResponse[UserResponse])
async def update_user_profile(
    full_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    personal_email: Optional[str] = Form(None),
    personal_number: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    email: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    target_email = email or current_user["email"]
    
    # Check permissions
    if current_user["role"] != UserRole.ADMIN and current_user["email"] != target_email:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")
        
    update_dict = {}
    if full_name is not None: update_dict["full_name"] = full_name
    if phone_number is not None: update_dict["phone_number"] = phone_number
    if personal_email is not None: update_dict["personal_email"] = personal_email
    if personal_number is not None: update_dict["personal_number"] = personal_number
    if branch is not None: update_dict["branch"] = branch
    
    # Handle optional photo upload
    if photo is not None:
        if not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        content = await photo.read()
        if len(content) > 500 * 1024:  # 500KB limit
            raise HTTPException(status_code=400, detail="Image size must be less than 500KB")
        update_dict["photo_data"] = Binary(content)
        update_dict["photo_mime"] = photo.content_type
        update_dict["has_photo"] = True
        
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    users_collection.update_one({"email": target_email}, {"$set": update_dict})
    updated_user = users_collection.find_one({"email": target_email})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Remove binary data from JSON response to prevent serialization error
    if "photo_data" in updated_user:
        updated_user.pop("photo_data")
        
    # Decrypt password for schema consistency
    if "password" in updated_user:
        try:
            updated_user["password"] = decrypt_password(updated_user.get("password", ""))
        except Exception:
            pass
        
    return {
        "status_code": 200,
        "status": "success",
        "message": "Profile updated successfully",
        "data": format_mongo_id(updated_user)
    }

@app.get("/users/{email}/photo")
def get_user_photo(email: str):
    user = users_collection.find_one({"email": email})
    if user and user.get("photo_data"):
        return Response(content=user["photo_data"], media_type=user.get("photo_mime", "image/png"))
        
    # Fallback to static default avatar
    default_path = "static/default_user.png"
    if os.path.exists(default_path):
        with open(default_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    return Response(content=b"", status_code=404)

@app.post("/users/{email}/photo", status_code=200)
async def upload_user_photo(
    email: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload or update a user's profile photo.
    The authenticated user can update their own photo.
    Admin and Manager can update any user's photo.
    """
    # Allow self-update OR manager/admin updating any user
    if current_user["email"] != email and current_user.get("role") not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorised to update this user's photo")
    
    target = users_collection.find_one({"email": email})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > 500 * 1024:  # 500 KB limit
        raise HTTPException(status_code=400, detail="Image size must be less than 500 KB")

    users_collection.update_one(
        {"email": email},
        {"$set": {
            "photo_data": Binary(content),
            "photo_mime": file.content_type,
            "has_photo": True
        }}
    )
    return {"status": "success", "message": f"Photo updated for {email}"}

@app.post("/clients/{client_id}/photo", status_code=200)
async def upload_client_photo(
    client_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_manager_or_higher)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    content = await file.read()
    if len(content) > 500 * 1024:  # 500KB limit
        raise HTTPException(status_code=400, detail="Image size must be less than 500KB")
        
    clients_collection.update_one(
        {"client_id": client_id},
        {"$set": {
            "photo_data": Binary(content),
            "photo_mime": file.content_type,
            "has_photo": True
        }}
    )
    return {"status": "success", "message": "Client photo uploaded successfully"}

@app.get("/clients/{client_id}/photo")
def get_client_photo(client_id: str):
    client_doc = clients_collection.find_one({"client_id": client_id})
    if client_doc and client_doc.get("photo_data"):
        return Response(content=client_doc["photo_data"], media_type=client_doc.get("photo_mime", "image/png"))
        
    # Fallback to static default client avatar
    default_path = "static/default_client.png"
    if os.path.exists(default_path):
        with open(default_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    return Response(content=b"", status_code=404)

# --- RECEIPT SCREENSHOT ENDPOINTS ---

@app.post("/orders/{order_db_id}/receipt/{phase}", status_code=200)
async def upload_receipt_screenshot(
    order_db_id: str,
    phase: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_manager_or_higher)
):
    """
    Upload a payment receipt screenshot for an order phase (1, 2, or 3).
    - Validates image MIME type, enforces 2 MB size limit
    - Stores as Binary blob + MIME type in orders collection
    - Clears dashboard cache after successful upload
    """
    from app.cache import clear_dashboard_cache
    
    # Validate phase
    if phase not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Phase must be 1, 2, or 3")
    
    # Validate image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="Image size must be less than 2MB")
    
    # Verify order exists
    try:
        order = orders_collection.find_one({"_id": ObjectId(order_db_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order_db_id format")
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Store receipt
    orders_collection.update_one(
        {"_id": ObjectId(order_db_id)},
        {"$set": {
            f"receipt_phase_{phase}_data": Binary(content),
            f"receipt_phase_{phase}_mime": file.content_type
        }}
    )
    
    # Clear cache
    clear_dashboard_cache()
    
    return {
        "status": "success",
        "message": f"Receipt screenshot for phase {phase} uploaded successfully"
    }

@app.get("/orders/{order_db_id}/receipt/{phase}")
def get_receipt_screenshot(order_db_id: str, phase: int):
    """
    Download/serve a payment receipt screenshot for an order phase.
    Returns binary image with appropriate MIME type, or 404 if not found.
    """
    # Validate phase
    if phase not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Phase must be 1, 2, or 3")
    
    try:
        order = orders_collection.find_one({"_id": ObjectId(order_db_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order_db_id format")
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    receipt_data = order.get(f"receipt_phase_{phase}_data")
    if not receipt_data:
        raise HTTPException(status_code=404, detail=f"No receipt found for phase {phase}")
    
    receipt_mime = order.get(f"receipt_phase_{phase}_mime", "image/png")
    return Response(content=receipt_data, media_type=receipt_mime)

@app.delete("/orders/{order_db_id}/receipt/{phase}", status_code=200)
def delete_receipt_screenshot(
    order_db_id: str,
    phase: int,
    current_user: dict = Depends(require_manager_or_higher)
):
    """
    Delete a payment receipt screenshot from an order phase.
    Removes both the binary data and MIME type fields.
    """
    from app.cache import clear_dashboard_cache
    
    # Validate phase
    if phase not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Phase must be 1, 2, or 3")
    
    # Verify order exists
    try:
        order = orders_collection.find_one({"_id": ObjectId(order_db_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order_db_id format")
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Delete receipt
    orders_collection.update_one(
        {"_id": ObjectId(order_db_id)},
        {"$unset": {
            f"receipt_phase_{phase}_data": "",
            f"receipt_phase_{phase}_mime": ""
        }}
    )
    
    # Clear cache
    clear_dashboard_cache()
    
    return {
        "status": "success",
        "message": f"Receipt screenshot for phase {phase} deleted successfully"
    }



@app.post("/users/profiles/append", response_model=ApiResponse[dict])
def append_profile_name(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Append a new profile name to a user's list."""
    target_user = users_collection.find_one({"email": data.email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_collection.update_one(
        {"email": data.email},
        {"$addToSet": {"profile_names": data.profile_name}}
    )
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Profile '{data.profile_name}' added to {data.email}",
        "data": None
    }

# @app.put("/users/profiles/update", response_model=ApiResponse[dict])
# def update_profile_name(data: ProfileUpdate, current_user: dict = Depends(require_manager_or_higher)):
#     """Update an existing profile name in a user's list."""
#     if not data.new_profile_name:
#         raise HTTPException(status_code=400, detail="new_profile_name is required for update")
        
#     target_user = users_collection.find_one({"email": data.email})
#     if not target_user:
#         raise HTTPException(status_code=404, detail="User not found")
        
#     # Atomic update of specific element in array
#     result = users_collection.update_one(
#         {"email": data.email, "profile_names": data.profile_name},
#         {"$set": {"profile_names.$": data.new_profile_name}}
#     )
    
#     if result.matched_count == 0:
#         raise HTTPException(status_code=404, detail=f"Profile '{data.profile_name}' not found for this user")

#     return {
#         "status_code": 200,
#         "status": "success",
#         "message": f"Profile '{data.profile_name}' updated to '{data.new_profile_name}'",
#         "data": None
#     }

# @app.delete("/users/profiles/remove", response_model=ApiResponse[dict])
# def remove_profile_name(data: ProfileUpdate, current_user: dict = Depends(require_manager_or_higher)):
#     """Remove a profile name from a user's list."""
#     target_user = users_collection.find_one({"email": data.email})
#     if not target_user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     users_collection.update_one(
#         {"email": data.email},
#         {"$pull": {"profile_names": data.profile_name}}
#     )
#     return {
#         "status_code": 200,
#         "status": "success",
#         "message": f"Profile '{data.profile_name}' removed from {data.email}",
#         "data": None
#     }


def get_user_dashboard_data(client_match: dict):
    """
    Common logic to fetch dashboard stats, country stats, and order status details
    based on a client filter (e.g., all clients for Admin, or specific handler for Employee).
    """
    from app.currency_converter import get_all_inr_rates
    rates = get_all_inr_rates()
    usd_rate = rates.get("USD", 0.012)
    cny_rate = rates.get("CNY", 0.087)
    aed_rate = rates.get("AED", 0.044)
    sar_rate = rates.get("SAR", 0.045)
    
    multipliers = {
        "USD": 1.0,
        "INR": usd_rate,
        "CNY": usd_rate / cny_rate if cny_rate else 0.14,
        "AED": usd_rate / aed_rate if aed_rate else 0.272,
        "SAR": usd_rate / sar_rate if sar_rate else 0.267,
    }

    # 2. Aggregation Pipeline to fetch clients and their stats in ONE go
    pipeline = [
        {"$match": client_match},
        {
            "$lookup": {
                "from": "orders",
                "let": {"cid": "$client_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$client_id", "$$cid"]}}},
                    {
                        "$lookup": {
                            "from": "payments",
                            "localField": "order_id",
                            "foreignField": "order_id",
                            "as": "order_payments"
                        }
                    },
                    {
                        "$addFields": {
                            "order_total_usd": {
                                "$switch": {
                                    "branches": [
                                        {"case": {"$eq": [{"$toUpper": "$currency"}, "INR"]}, "then": {"$multiply": ["$total_amount", multipliers["INR"]]}},
                                        {"case": {"$eq": [{"$toUpper": "$currency"}, "CNY"]}, "then": {"$multiply": ["$total_amount", multipliers["CNY"]]}},
                                        {"case": {"$eq": [{"$toUpper": "$currency"}, "AED"]}, "then": {"$multiply": ["$total_amount", multipliers["AED"]]}},
                                        {"case": {"$eq": [{"$toUpper": "$currency"}, "SAR"]}, "then": {"$multiply": ["$total_amount", multipliers["SAR"]]}}
                                    ],
                                    "default": "$total_amount"
                                }
                            },
                            "order_paid": {
                                "$sum": {
                                    "$map": {
                                        "input": "$order_payments",
                                        "as": "p",
                                        "in": {
                                            "$switch": {
                                                "branches": [
                                                    {"case": {"$eq": [{"$toUpper": "$currency"}, "INR"]}, "then": {"$multiply": [{"$ifNull": ["$$p.paid_amount", 0.0]}, multipliers["INR"]]}},
                                                    {"case": {"$eq": [{"$toUpper": "$currency"}, "CNY"]}, "then": {"$multiply": [{"$ifNull": ["$$p.paid_amount", 0.0]}, multipliers["CNY"]]}},
                                                    {"case": {"$eq": [{"$toUpper": "$currency"}, "AED"]}, "then": {"$multiply": [{"$ifNull": ["$$p.paid_amount", 0.0]}, multipliers["AED"]]}},
                                                    {"case": {"$eq": [{"$toUpper": "$currency"}, "SAR"]}, "then": {"$multiply": [{"$ifNull": ["$$p.paid_amount", 0.0]}, multipliers["SAR"]]}}
                                                ],
                                                "default": {"$ifNull": ["$$p.paid_amount", 0.0]}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "total_amount": {"$sum": "$order_total_usd"},
                            "paid_amount": {"$sum": "$order_paid"},
                            "order_count": {"$sum": 1},
                            "payment_status": {"$first": "$payment_status"},
                            "paid_order_count": {
                                "$sum": {
                                    "$cond": [
                                        {"$gte": ["$order_paid", "$order_total_usd"]},
                                        1, 0
                                    ]
                                }
                            },
                            "pending_order_count": {
                                "$sum": {
                                    "$cond": [
                                        {
                                            "$and": [
                                                {"$lt": ["$order_paid", "$order_total_usd"]},
                                                {"$ne": ["$order_status", "Inactive"]}
                                            ]
                                        },
                                        1, 0
                                    ]
                                }
                            },
                            "reject_order_count": {
                                "$sum": {"$cond": [{"$eq": ["$order_status", "Inactive"]}, 1, 0]}
                            },
                            "orders_list": {
                                "$push": {
                                    "client_id": "$client_id",
                                    "reference_id": "$reference_id",
                                    "order_status": "$order_status",
                                    "total_amount": "$order_total_usd",
                                    "paid_amount": "$order_paid",
                                    "is_new_order": "$is_new_order",
                                    "payment_status": {
                                        "$cond": [
                                            {"$gte": ["$order_paid", "$order_total_usd"]},
                                            "Paid",
                                            {
                                                "$cond": [
                                                    {"$gt": ["$order_paid", 0]},
                                                    "Partial Paid",
                                                    "Pending"
                                                ]
                                            }
                                        ]
                                    },
                                    "created_at": "$created_at",
                                    "order_date": "$order_date"
                                }
                            }
                        }
                    }
                ],
                "as": "stats"
            }
        },
        {"$unwind": {"path": "$stats", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "total_amount": {"$ifNull": ["$stats.total_amount", 0.0]},
                "paid_amount": {"$ifNull": ["$stats.paid_amount", 0.0]},
                "order_count": {"$ifNull": ["$stats.order_count", 0]},
                "paid_order_count": {"$ifNull": ["$stats.paid_order_count", 0]},
                "pending_order_count": {"$ifNull": ["$stats.pending_order_count", 0]},
                "reject_order_count": {"$ifNull": ["$stats.reject_order_count", 0]},
                "orders_list": {"$ifNull": ["$stats.orders_list", []]}
            }
        },
        {"$project": {"stats": 0}}
    ]
    
    clients_with_stats = list(clients_collection.aggregate(pipeline))
    
    country_stats_map = {}
    order_status_details = []
    
    total_system_amount = 0.0
    total_system_paid = 0.0
    total_system_orders = 0
    total_system_pending = 0
    total_system_rejects = 0
    
    for c in clients_with_stats:
        country = c.get("country") or "Unknown"
        if country not in country_stats_map:
            country_stats_map[country] = {
                "country_name": country,
                "client_count": 0,
                "order_count": 0,
                "paid_count": 0,
                "paid_amount": 0.0,
                "pending_count": 0,
                "reject_count": 0
            }
        
        country_stats_map[country]["client_count"] += 1
        country_stats_map[country]["order_count"] += c.get("order_count", 0)
        country_stats_map[country]["paid_count"] += c.get("paid_order_count", 0)
        country_stats_map[country]["paid_amount"] = round(country_stats_map[country]["paid_amount"] + c.get("paid_amount", 0.0), 2)
        country_stats_map[country]["pending_count"] += c.get("pending_order_count", 0)
        country_stats_map[country]["reject_count"] += c.get("reject_order_count", 0)
        
        for order in c.get("orders_list", []):
            order_status_details.append({
                "client_name": c.get("name"),
                "client_id": order.get("client_id"),
                "reference_id": order.get("reference_id"),
                "order_status": order.get("order_status"),
                "payment_status": order.get("payment_status"),
                "country": c.get("country"),        
                "total_amount": round(order.get("total_amount", 0.0), 2),
                "paid_amount": round(order.get("paid_amount", 0.0), 2),
                "is_new_order": order.get("is_new_order", "yes"),
                "created_at": order.get("created_at"),
                "order_date": order.get("order_date")
            })
            
        total_system_amount += c.get("total_amount", 0.0)
        total_system_paid += c.get("paid_amount", 0.0)
        total_system_orders += c.get("order_count", 0)
        total_system_pending += c.get("pending_order_count", 0)
        total_system_rejects += c.get("reject_order_count", 0)

    total_clients_count = len(clients_with_stats)
    pending_pct = (total_system_pending / total_system_orders * 100) if total_system_orders > 0 else 0.0
    
    dashboard_stats = {
        "total_amount": round(total_system_amount, 2),
        "paid_amount": round(total_system_paid, 2),
        "remaining_amount": round(total_system_amount - total_system_paid, 2),
        "total_clients": total_clients_count,
        "total_clients_percentage": 100.0, 
        "pending_count": total_system_pending,
        "pending_count_percentage": round(pending_pct, 1),
        "reject_count": total_system_rejects, 
        "reject_count_percentage": round((total_system_rejects / total_system_orders * 100), 1) if total_system_orders > 0 else 0.0
    }
    
    country_based_details = list(country_stats_map.values())
    country_split = {c["country_name"]: c["paid_amount"] for c in country_based_details}
    
    return {
        "dashboard_stats": dashboard_stats,
        "country_based_details": country_based_details,
        "country_split": country_split,
        "order_status_details": order_status_details
    }


@app.get("/users/me/details", response_model=ApiResponse[UserDetailResponse])
def get_own_details(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile details including country stats and order statuses.
    """
    # 1. Determine client filter (Admin/Manager see all, Employee see only their own)
    client_match = {}
    if current_user["role"] not in [UserRole.ADMIN, UserRole.MANAGER]:
        client_match = {"client_handler": current_user.get("email")}

    # 2. Fetch data using helper
    dashboard_data = get_user_dashboard_data(client_match)
    
    # 3. Format user profile — strip raw binary before JSON serialisation
    import base64
    user_data = format_mongo_id(current_user.copy())
    user_data["password"] = decrypt_password(user_data.get("password", ""))
    raw_photo = user_data.pop("photo_data", None)
    if raw_photo:
        user_data["photo_base64"] = base64.b64encode(bytes(raw_photo)).decode("utf-8")
        user_data["photo_mime"] = user_data.get("photo_mime", "image/png")
    else:
        user_data["photo_base64"] = None
        user_data["photo_mime"] = None
    
    # 4. Merge dashboard data into user response
    user_data.update(dashboard_data)
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "User details fetched successfully",
        "data": user_data
    }

@app.get("/users/{email}/details", response_model=ApiResponse[UserDetailResponse])
def get_user_details(email: str, current_user: dict = Depends(require_manager_or_higher)):
    """
    Get profile details of any user including country stats and order statuses.
    Restricted to Admin and Manager.
    """
    target_user = users_collection.find_one({"email": email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # 1. Determine client filter (Admin/Manager viewing an employee - filter by that employee's clients)
    client_match = {"client_handler": target_user.get("email")}

    # 2. Fetch data using helper
    dashboard_data = get_user_dashboard_data(client_match)
    
    # 3. Format target user profile — strip raw binary before JSON serialisation
    import base64
    user_data = format_mongo_id(target_user)
    user_data["password"] = decrypt_password(user_data.get("password", ""))
    raw_photo = user_data.pop("photo_data", None)
    if raw_photo:
        user_data["photo_base64"] = base64.b64encode(bytes(raw_photo)).decode("utf-8")
        user_data["photo_mime"] = user_data.get("photo_mime", "image/png")
    else:
        user_data["photo_base64"] = None
        user_data["photo_mime"] = None
    
    # 4. Merge dashboard data into user response
    user_data.update(dashboard_data)
    
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Details for {email} fetched successfully",
        "data": user_data
    }

# --- CLIENTS ---

@app.post("/clients", response_model=ApiResponse[ClientResponse], status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, current_user: dict = Depends(get_current_user)):
    # Auto-generate client_id if not provided
    if not client.client_id:
        client.client_id = generate_custom_id("CL", clients_collection, current_user)
    elif clients_collection.find_one({"client_id": client.client_id}):
        raise HTTPException(status_code=400, detail="Client ID already exists")


    client_dict = client.model_dump()
    
    # Dynamic Client Handler logic — store EMAIL for uniqueness
    if client_dict.get("client_handler"):
        client_dict["client_handler"] = get_user_email_by_name(client_dict["client_handler"])
    else:
        if current_user["role"] == UserRole.EMPLOYEE:
            client_dict["client_handler"] = current_user.get("email")
        else:
            client_dict["client_handler"] = None
    # Remove display-only field before saving to DB
    client_dict.pop("client_handler_name", None)
            
    client_dict["created_at"] = datetime.utcnow()
    result = clients_collection.insert_one(client_dict)
    client_dict["_id"] = str(result.inserted_id)
    

    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Client created successfully",
        "data": client_dict
    }

@app.get("/clients", response_model=ApiResponse[list[ClientResponse]])
def get_clients(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        query = {"client_handler": current_user.get("email")}

    # Dynamic aggregation to pull order_type from associated orders
    pipeline = [
        {"$match": query},
        {
            "$lookup": {
                "from": "orders",
                "localField": "client_id",
                "foreignField": "client_id",
                "as": "client_orders"
            }
        },
        {
            "$addFields": {
                "order_type": {
                    "$reduce": {
                        "input": {
                            "$setUnion": {
                                "$filter": {
                                    "input": "$client_orders.order_type",
                                    "as": "ot",
                                    "cond": { "$and": [ { "$ne": ["$$ot", None] }, { "$ne": ["$$ot", ""] } ] }
                                }
                            }
                        },
                        "initialValue": "",
                        "in": {
                            "$cond": [
                                { "$eq": ["$$value", ""] },
                                "$$this",
                                { "$concat": ["$$value", ", ", "$$this"] }
                            ]
                        }
                    }
                },
                "order_id_db": {
                    "$map": {
                        "input": "$client_orders",
                        "as": "order",
                        "in": {"$toString": "$$order._id"}
                    }
                }
            }
        },
        {"$project": {"client_orders": 0}}
    ]
    
    clients = [format_mongo_id(c) for c in clients_collection.aggregate(pipeline)]
    resolved = resolve_client_handler_bulk(clients)
    
    if current_user["role"] == UserRole.EMPLOYEE:
        employee_names = {current_user.get("full_name")}
        profile_names = set(current_user.get("profile_names", []))
    else:
        # Optimized retrieval of employee and profile names using projection and efficient sets
        employees_data = list(users_collection.find(
            {"role": UserRole.EMPLOYEE}, 
            {"full_name": 1, "profile_names": 1, "_id": 0}
        ))
        employee_names = {emp["full_name"] for emp in employees_data if emp.get("full_name")}
        profile_names = {
            p for emp in employees_data 
            if isinstance(emp.get("profile_names"), list) 
            for p in emp["profile_names"]
        }
                
    detail = {
        "employee_names": list(employee_names),
        "profile_names": list(profile_names),
        "order_type_options": ORDER_TYPE_OPTIONS
    }

    return {
        "status_code": 200,
        "status": "success",
        "message": "Clients fetched successfully",
        "data": resolved,
        "detail": detail
    }

@app.get("/clients/{client_id}", response_model=ApiResponse[ClientFullResponse])
def get_client(client_id: str, current_user: dict = Depends(require_manager_or_higher)):
    """
    Fetch full client profile including:
    - All client fields
    - Full order list with payment phase details
    - Client photo embedded as base64 (photo_base64 + photo_mime)
    """
    import base64

    # --- 1. Fetch client ---
    client = clients_collection.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # --- 2. Embed photo as base64 (strip raw binary before serialisation) ---
    raw_photo = client.pop("photo_data", None)
    if raw_photo:
        client["photo_base64"] = base64.b64encode(bytes(raw_photo)).decode("utf-8")
        client["photo_mime"] = client.get("photo_mime", "image/png")
    else:
        client["photo_base64"] = None
        client["photo_mime"] = None

    # --- 3. Fetch all orders for this client ---
    raw_orders = list(orders_collection.find({"client_id": client_id}))
    orders_out = []
    for order in raw_orders:
        order_id = order.get("order_id")

        # Fetch the payment record linked to this order (if any)
        payment = payments_collection.find_one({"order_id": order_id}) or {}

        # Build order dict with all standard fields
        order_dict = {
            "order_id":                  order.get("order_id"),
            "reference_id":              order.get("reference_id"),
            "order_date":                order.get("order_date"),
            "profile_name":              order.get("profile_name"),
            "title":                     order.get("title"),
            "journal_name":              order.get("journal_name"),
            "order_type":                order.get("order_type"),
            "index":                     order.get("index"),
            "rank":                      order.get("rank"),
            "currency":                  order.get("currency", "USD"),
            "total_amount":              order.get("total_amount", 0.0),
            "writing_amount":            order.get("writing_amount", 0.0),
            "modification_amount":       order.get("modification_amount", 0.0),
            "implementation_amount":     order.get("implementation_amount", 0.0),
            "po_amount":                 order.get("po_amount", 0.0),
            "paid_amount":               payment.get("paid_amount") or order.get("paid_amount", 0.0),
            "payment_status":            order.get("payment_status", "Pending"),
            "order_status":              order.get("order_status"),
            "remarks":                   order.get("remarks"),
            "clients_details":           order.get("clients_details"),
            "client_drive_link":         order.get("client_drive_link"),
            "payment_drive_link":        order.get("payment_drive_link"),
            "writing_start_date":        order.get("writing_start_date"),
            "writing_end_date":          order.get("writing_end_date"),
            "modification_start_date":   order.get("modification_start_date"),
            "modification_end_date":     order.get("modification_end_date"),
            "po_start_date":             order.get("po_start_date"),
            "po_end_date":               order.get("po_end_date"),
            "is_new_order":              order.get("is_new_order"),
            # Payment phases from the payment record
            "phase_1_payment":           payment.get("phase_1_payment", 0.0),
            "phase_1_payment_date":      payment.get("phase_1_payment_date"),
            "phase_1_payment_details":   payment.get("phase_1_payment_details"),
            "phase_2_payment":           payment.get("phase_2_payment", 0.0),
            "phase_2_payment_date":      payment.get("phase_2_payment_date"),
            "phase_2_payment_details":   payment.get("phase_2_payment_details"),
            "phase_3_payment":           payment.get("phase_3_payment", 0.0),
            "phase_3_payment_date":      payment.get("phase_3_payment_date"),
            "phase_3_payment_details":   payment.get("phase_3_payment_details"),
        }
        
        # Inject receipt screenshots for each phase (encoded as base64)
        for phase in (1, 2, 3):
            receipt_data = order.get(f"receipt_phase_{phase}_data")
            receipt_mime = order.get(f"receipt_phase_{phase}_mime", "image/png")
            
            if receipt_data:
                order_dict[f"receipt_phase_{phase}_base64"] = base64.b64encode(bytes(receipt_data)).decode("utf-8")
                order_dict[f"receipt_phase_{phase}_mime"] = receipt_mime
            else:
                order_dict[f"receipt_phase_{phase}_base64"] = None
                order_dict[f"receipt_phase_{phase}_mime"] = None
        
        orders_out.append(order_dict)

    client["orders"] = orders_out

    # --- 4. Resolve handler name and format _id ---
    client_data = resolve_client_handler(format_mongo_id(client))

    return {
        "status_code": 200,
        "status": "success",
        "message": "Client fetched successfully",
        "data": client_data
    }

@app.post("/clients/assign", response_model=ApiResponse[ClientResponse])
def assign_client(request: ClientAssignRequest, current_user: dict = Depends(require_manager_or_higher)):
    """
    Assign an Employee to a Client.
    Restricted to Admin and Manager.
    """
    # 1. Verify Employee
    employee = users_collection.find_one({"email": request.employee_email, "role": UserRole.EMPLOYEE})
    if not employee:
        raise HTTPException(
            status_code=404, 
            detail=f"Employee with email {request.employee_email} not found"
        )
    
    # 2. Verify Client
    client = clients_collection.find_one({"client_id": request.client_id})
    if not client:
        raise HTTPException(
            status_code=404, 
            detail=f"Client with ID {request.client_id} not found"
        )
    
    # 3. Update Client Handler — store email for uniqueness
    clients_collection.update_one(
        {"client_id": request.client_id},
        {"$set": {"client_handler": employee.get("email")}}
    )
    

    
    # Fetch updated client
    updated_client = clients_collection.find_one({"client_id": request.client_id})
    
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Client {request.client_id} assigned to {employee.get('full_name')}",
        "data": resolve_client_handler(format_mongo_id(updated_client))
    }

# --- MANUSCRIPTS ---

@app.post("/manuscripts", response_model=ApiResponse[ManuscriptResponse], status_code=status.HTTP_201_CREATED)
def create_manuscript(manuscript: ManuscriptCreate, current_user: dict = Depends(require_manager_or_higher)):
    # Verify client exists
    if not clients_collection.find_one({"client_id": manuscript.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    ms_dict = manuscript.model_dump()
    ms_dict["created_at"] = datetime.utcnow()
    result = manuscripts_collection.insert_one(ms_dict)
    ms_dict["_id"] = str(result.inserted_id)

    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Manuscript created successfully",
        "data": ms_dict
    }

@app.get("/manuscripts", response_model=ApiResponse[list[ManuscriptResponse]])
def get_manuscripts(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        my_client_ids = clients_collection.distinct("client_id", {"client_handler": current_user.get("email")})
        query = {"client_id": {"$in": my_client_ids}} if my_client_ids else {"client_id": {"$in": []}}
        
    ms = list(manuscripts_collection.find(query))
    return {
        "status_code": 200,
        "status": "success",
        "message": "Manuscripts fetched successfully",
        "data": [format_mongo_id(m) for m in ms]
    }

# --- ORDERS ---

@app.post("/orders", response_model=ApiResponse[OrderResponse], status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, current_user: dict = Depends(require_manager_or_higher)):
    # Verify client exists
    if not clients_collection.find_one({"client_id": order.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    # Manuscript is optional — only validate if provided
    if order.manuscript_id:
        if not manuscripts_collection.find_one({"manuscript_id": order.manuscript_id}):
            raise HTTPException(status_code=400, detail="Invalid manuscript_id")
    
    # Auto-generate reference_id if not provided
    if not order.reference_id:
        order.reference_id = generate_custom_id("REF", orders_collection, current_user)
    elif orders_collection.find_one({"reference_id": order.reference_id}):
        raise HTTPException(status_code=400, detail="This reference ID already exists")

    
    order_dict = order.model_dump()
    order_dict["created_at"] = datetime.utcnow()
    order_dict["updated_at"] = datetime.utcnow()
    result = orders_collection.insert_one(order_dict)
    order_dict["_id"] = str(result.inserted_id)
    

    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Order created successfully",
        "data": order_dict
    }

@app.get("/orders", response_model=ApiResponse[list[OrderResponse]])
def get_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        my_client_ids = clients_collection.distinct("client_id", {"client_handler": current_user.get("email")})
        query = {"client_id": {"$in": my_client_ids}} if my_client_ids else {"client_id": {"$in": []}}
        
    orders = list(orders_collection.find(query))
    return {
        "status_code": 200,
        "status": "success",
        "message": "Orders fetched successfully",
        "data": [format_mongo_id(o) for o in orders]
    }

# --- PAYMENTS ---

@app.post("/payments", response_model=ApiResponse[PaymentResponse], status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate, current_user: dict = Depends(require_manager_or_higher)):
    if not clients_collection.find_one({"client_id": payment.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    pay_dict = payment.model_dump()
    pay_dict["created_at"] = datetime.utcnow()
    result = payments_collection.insert_one(pay_dict)
    pay_dict["_id"] = str(result.inserted_id)
    

    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Payment created successfully",
        "data": pay_dict
    }

@app.get("/payments", response_model=ApiResponse[list[PaymentResponse]])
def get_payments(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        my_client_ids = clients_collection.distinct("client_id", {"client_handler": current_user.get("email")})
        query = {"client_id": {"$in": my_client_ids}} if my_client_ids else {"client_id": {"$in": []}}
        
    payments = list(payments_collection.find(query))
    return {
        "status_code": 200,
        "status": "success",
        "message": "Payments fetched successfully",
        "data": [format_mongo_id(p) for p in payments]
    }

@app.get("/payments/history", response_model=ApiResponse[list[PaymentHistoryItem]])
def get_payment_history(client_id: Optional[str] = None, order_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """
    Detailed payment history from the flattened payment_history_collection.
    """
    query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        # Filter by clients handled by this employee
        my_client_ids = clients_collection.distinct("client_id", {"client_handler": current_user.get("email")})
        query["client_id"] = {"$in": my_client_ids}
    
    if client_id:
        query["client_id"] = client_id
    if order_id:
        query["order_id"] = order_id

    history = list(payment_history_collection.find(query).sort("created_at", -1))

    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Payment history fetched successfully",
        "data": history
    }

@app.get("/payments/pending-summary", response_model=ApiResponse[PendingSummaryResponse])
def get_pending_payment_summary(current_user: dict = Depends(require_manager_or_higher)):
    """
    Summary of pending payments across all clients and orders.
    Restricted to Manager and Admin.
    """
    from app.currency_converter import get_all_inr_rates
    rates = get_all_inr_rates()
    usd_rate = rates.get("USD", 0.012)
    cny_rate = rates.get("CNY", 0.087)
    aed_rate = rates.get("AED", 0.044)
    sar_rate = rates.get("SAR", 0.045)
    
    multipliers = {
        "USD": 1.0,
        "INR": usd_rate,
        "CNY": usd_rate / cny_rate if cny_rate else 0.14,
        "AED": usd_rate / aed_rate if aed_rate else 0.272,
        "SAR": usd_rate / sar_rate if sar_rate else 0.267,
    }

    pipeline = [
        {"$match": {"order_status": {"$ne": "Inactive"}}},
        {
            "$addFields": {
                "total_usd": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "INR"]}, "then": {"$multiply": ["$total_amount", multipliers["INR"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "CNY"]}, "then": {"$multiply": ["$total_amount", multipliers["CNY"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "AED"]}, "then": {"$multiply": ["$total_amount", multipliers["AED"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "SAR"]}, "then": {"$multiply": ["$total_amount", multipliers["SAR"]]}}
                        ],
                        "default": "$total_amount"
                    }
                },
                "paid_usd": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "INR"]}, "then": {"$multiply": [{"$ifNull": ["$paid_amount", 0.0]}, multipliers["INR"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "CNY"]}, "then": {"$multiply": [{"$ifNull": ["$paid_amount", 0.0]}, multipliers["CNY"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "AED"]}, "then": {"$multiply": [{"$ifNull": ["$paid_amount", 0.0]}, multipliers["AED"]]}},
                            {"case": {"$eq": [{"$toUpper": "$currency"}, "SAR"]}, "then": {"$multiply": [{"$ifNull": ["$paid_amount", 0.0]}, multipliers["SAR"]]}}
                        ],
                        "default": {"$ifNull": ["$paid_amount", 0.0]}
                    }
                }
            }
        },
        {
            "$addFields": {
                "remaining_usd": {"$subtract": ["$total_usd", "$paid_usd"]}
            }
        },
        {"$match": {"remaining_usd": {"$gt": 0}}},
        {
            "$group": {
                "_id": "$client_id",
                "pending_orders": {"$sum": 1},
                "total_pending_amount": {"$sum": "$remaining_usd"}
            }
        },
        {
            "$lookup": {
                "from": "clients",
                "localField": "_id",
                "foreignField": "client_id",
                "as": "client_info"
            }
        },
        {"$unwind": "$client_info"},
        {
            "$project": {
                "_id": 0,
                "client_id": "$_id",
                "client_name": "$client_info.name",
                "total_orders": "$client_info.total_orders",
                "pending_orders": 1,
                "total_pending_amount": 1
            }
        },
        {"$sort": {"total_pending_amount": -1}}
    ]
    
    pending_clients = list(orders_collection.aggregate(pipeline))
    
    total_pending_amount = sum(c["total_pending_amount"] for c in pending_clients)
    pending_orders_count = sum(c["pending_orders"] for c in pending_clients)
    pending_clients_count = len(pending_clients)
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Pending payment summary fetched successfully",
        "data": {
            "total_pending_amount": round(total_pending_amount, 2),
            "pending_orders_count": pending_orders_count,
            "pending_clients_count": pending_clients_count,
            "top_pending_clients": pending_clients[:10]  # Top 10 for overview
        }
    }

# --- BANK ACCOUNTS ---

@app.get("/bank-accounts", response_model=ApiResponse[list[BankAccountResponse]])
def get_bank_accounts(current_user: dict = Depends(get_current_user)):
    """Get all bank accounts."""
    accounts = list(bank_accounts_collection.find())
    for acc in accounts:
        acc["_id"] = str(acc["_id"])
    return {
        "status_code": 200,
        "status": "success",
        "message": "Bank accounts fetched successfully",
        "data": accounts
    }

@app.post("/bank-accounts", response_model=ApiResponse[BankAccountResponse])
def create_bank_account(data: BankAccountCreate, current_user: dict = Depends(require_manager_or_higher)):
    """Create a new bank account."""
    if bank_accounts_collection.find_one({"account_number": data.account_number}):
        raise HTTPException(status_code=400, detail="Bank account already exists")
    
    acc_dict = data.model_dump()
    acc_dict["created_at"] = datetime.utcnow()
    result = bank_accounts_collection.insert_one(acc_dict)
    
    acc_dict["_id"] = str(result.inserted_id)
    return {
        "status_code": 201,
        "status": "success",
        "message": "Bank account created successfully",
        "data": acc_dict
    }

@app.put("/bank-accounts/{account_id}", response_model=ApiResponse[BankAccountResponse])
def update_bank_account(account_id: str, data: BankAccountUpdate, current_user: dict = Depends(require_manager_or_higher)):
    """Update a bank account."""
    if not ObjectId.is_valid(account_id):
        raise HTTPException(status_code=400, detail="Invalid bank account ID")
        
    existing = bank_accounts_collection.find_one({"_id": ObjectId(account_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Bank account not found")
        
    # Check if new number already exists
    if existing["account_number"] != data.account_number:
        if bank_accounts_collection.find_one({"account_number": data.account_number}):
            raise HTTPException(status_code=400, detail="Bank account number already exists")
            
    bank_accounts_collection.update_one(
        {"_id": ObjectId(account_id)},
        {"$set": {"account_number": data.account_number}}
    )
    
    updated = bank_accounts_collection.find_one({"_id": ObjectId(account_id)})
    updated["_id"] = str(updated["_id"])
    return {
        "status_code": 200,
        "status": "success",
        "message": "Bank account updated successfully",
        "data": updated
    }

@app.delete("/bank-accounts/{account_id}", response_model=ApiResponse[dict])
def delete_bank_account(account_id: str, current_user: dict = Depends(require_manager_or_higher)):
    """Delete a bank account."""
    if not ObjectId.is_valid(account_id):
        raise HTTPException(status_code=400, detail="Invalid bank account ID")
        
    result = bank_accounts_collection.delete_one({"_id": ObjectId(account_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bank account not found")
        
    return {
        "status_code": 200,
        "status": "success",
        "message": "Bank account deleted successfully",
        "data": None
    }

# --- DASHBOARD ---

@app.get("/dashboard/orders", response_model=ApiResponse[list[DashboardOrderResponse]])
def get_dashboard_orders(current_user: dict = Depends(get_current_user)):
    """
    Unified endpoint for the frontend dashboard.
    Optimized with MongoDB Aggregation Pipeline ($lookup + $unwind).
    Shows clients even if no orders exist.
    Includes caching for improved performance.
    """
    # 1. Get filtered clients query
    client_match = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        client_match = {"client_handler": current_user.get("email")}
        
    # 2. Aggregation Pipeline
    pipeline = [
        {"$match": client_match},
        {
            "$lookup": {
                "from": "orders",
                "localField": "client_id",
                "foreignField": "client_id",
                "as": "order"
            }
        },
        # Join clients with their orders; keep clients with 0 orders (placeholder row)
        {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "payments",
                "localField": "order.order_id",
                "foreignField": "order_id",
                "as": "p_list"
            }
        },
        {
            "$project": {
                "_id": 0,
                "order_db_id": {"$cond": [{"$ifNull": ["$order._id", False]}, {"$toString": "$order._id"}, None]},
                "order_id": "$order.order_id",
                "s_no": "$order.s_no",
                "order_date": "$order.order_date",
                "client_id": "$client_id",
                "client_name": "$name",
                "client_country": "$country",
                "client_Email": "$email",
                "client_whatsapp_number": "$whatsapp_no",
                "reference_id": "$order.reference_id",
                "ref_no": {"$ifNull": ["$order.client_ref_no", "$client_ref_no"]},
                "manuscript_id": "$order.manuscript_id",
                "journal_name": "$order.journal_name",
                "title": "$order.title",
                "order_type": "$order.order_type",
                "index": "$order.index",
                "rank": "$order.rank",
                "currency": {"$ifNull": ["$order.currency", "USD"]},
                "total_amount": {"$ifNull": ["$order.total_amount", 0.0]},
                "writing_amount": {"$ifNull": ["$order.writing_amount", 0.0]},
                "modification_amount": {"$ifNull": ["$order.modification_amount", 0.0]},
                "implementation_amount": {"$ifNull": ["$order.implementation_amount", 0.0]},
                "po_amount": {"$ifNull": ["$order.po_amount", 0.0]},
                "writing_start_date": "$order.writing_start_date",
                "writing_end_date": "$order.writing_end_date",
                "modification_start_date": "$order.modification_start_date",
                "modification_end_date": "$order.modification_end_date",
                "po_start_date": "$order.po_start_date",
                "po_end_date": "$order.po_end_date",
                "phase": {"$literal": None},
                # All phase fields live in a single payment doc per order — read directly
                "phase_1_payment": {"$arrayElemAt": ["$p_list.phase_1_payment", 0]},
                "phase_1_payment_date": {"$arrayElemAt": ["$p_list.phase_1_payment_date", 0]},
                "phase_1_payment_details": {"$arrayElemAt": ["$p_list.phase_1_payment_details", 0]},
                "phase_2_payment": {"$arrayElemAt": ["$p_list.phase_2_payment", 0]},
                "phase_2_payment_date": {"$arrayElemAt": ["$p_list.phase_2_payment_date", 0]},
                "phase_2_payment_details": {"$arrayElemAt": ["$p_list.phase_2_payment_details", 0]},
                "phase_3_payment": {"$arrayElemAt": ["$p_list.phase_3_payment", 0]},
                "phase_3_payment_date": {"$arrayElemAt": ["$p_list.phase_3_payment_date", 0]},
                "phase_3_payment_details": {"$arrayElemAt": ["$p_list.phase_3_payment_details", 0]},
                "payment_status": {"$ifNull": ["$order.payment_status", "No Order"]},
                "paid_amount": {"$ifNull": ["$order.paid_amount", 0.0]},
                "client_link": "$client_link",
                "bank_account": "$bank_account",
                "receive_bank_account": "$order.receive_bank_account",
                "client_affiliations": "$affiliation",
                "client_handler": "$client_handler",
                "profile_name": "$order.profile_name",
                "remarks": "$order.remarks",
                "order_status": "$order.order_status",
                "clients_details": "$order.clients_details",
                "client_drive_link": {"$ifNull": ["$order.client_drive_link", "$client_drive_link"]},
                "payment_drive_link": {"$ifNull": ["$order.payment_drive_link", "$payment_drive_link"]},
                "is_new_order": {"$ifNull": ["$order.is_new_order", "yes"]}
            }
        }
    ]
    
    dashboard_data = list(clients_collection.aggregate(pipeline))
    
    # Resolve handler names for display in bulk
    resolve_client_handler_bulk(dashboard_data)

    # Attach client photo as base64 for each row
    import base64
    client_ids = list({row["client_id"] for row in dashboard_data if row.get("client_id")})
    photo_map = {}
    for client_doc in clients_collection.find(
        {"client_id": {"$in": client_ids}},
        {"client_id": 1, "photo_data": 1, "photo_mime": 1}
    ):
        raw = client_doc.get("photo_data")
        if raw:
            photo_map[client_doc["client_id"]] = {
                "photo_base64": base64.b64encode(bytes(raw)).decode("utf-8"),
                "photo_mime":   client_doc.get("photo_mime", "image/png")
            }
        else:
            photo_map[client_doc["client_id"]] = {"photo_base64": None, "photo_mime": None}

    # Attach receipt screenshots as base64 for each row
    # Collect all order_db_ids that have receipts
    order_db_ids = list({row["order_db_id"] for row in dashboard_data if row.get("order_db_id")})
    receipt_map = {}  # Maps order_db_id -> {phase -> {base64, mime}}
    
    if order_db_ids:
        # Convert string IDs back to ObjectId for querying
        order_object_ids = []
        for oid_str in order_db_ids:
            try:
                order_object_ids.append(ObjectId(oid_str))
            except:
                pass
        
        # Query orders for receipt fields
        for order_doc in orders_collection.find(
            {"_id": {"$in": order_object_ids}},
            {
                "_id": 1,
                "receipt_phase_1_data": 1, "receipt_phase_1_mime": 1,
                "receipt_phase_2_data": 1, "receipt_phase_2_mime": 1,
                "receipt_phase_3_data": 1, "receipt_phase_3_mime": 1
            }
        ):
            order_id_str = str(order_doc["_id"])
            receipt_map[order_id_str] = {}
            
            for phase in (1, 2, 3):
                receipt_data = order_doc.get(f"receipt_phase_{phase}_data")
                receipt_mime = order_doc.get(f"receipt_phase_{phase}_mime", "image/png")
                
                if receipt_data:
                    receipt_map[order_id_str][phase] = {
                        "base64": base64.b64encode(bytes(receipt_data)).decode("utf-8"),
                        "mime": receipt_mime
                    }
                else:
                    receipt_map[order_id_str][phase] = {
                        "base64": None,
                        "mime": None
                    }

    from app.currency_converter import get_all_inr_rates
    rates = get_all_inr_rates()
    usd_rate = rates.get("USD", 0.012)
    cny_rate = rates.get("CNY", 0.087)
    aed_rate = rates.get("AED", 0.044)
    sar_rate = rates.get("SAR", 0.045)
    
    multipliers = {
        "USD": 1.0,
        "INR": usd_rate,
        "CNY": usd_rate / cny_rate if cny_rate else 0.14,
        "AED": usd_rate / aed_rate if aed_rate else 0.272,
        "SAR": usd_rate / sar_rate if sar_rate else 0.267,
    }

    for row in dashboard_data:
        info = photo_map.get(row.get("client_id"), {})
        row["client_photo_base64"] = info.get("photo_base64")
        row["client_photo_mime"]   = info.get("photo_mime")
        
        # Inject receipt screenshots for this order
        order_id_str = row.get("order_db_id")
        if order_id_str and order_id_str in receipt_map:
            for phase in (1, 2, 3):
                phase_receipt = receipt_map[order_id_str].get(phase, {})
                row[f"receipt_phase_{phase}_base64"] = phase_receipt.get("base64")
                row[f"receipt_phase_{phase}_mime"] = phase_receipt.get("mime")
        else:
            # No receipts for this order
            for phase in (1, 2, 3):
                row[f"receipt_phase_{phase}_base64"] = None
                row[f"receipt_phase_{phase}_mime"] = None
        
        # Calculate USD equivalents dynamically
        curr = (row.get("currency") or "USD").upper().strip()
        multiplier = multipliers.get(curr, 1.0)
        
        raw_total = row.get("total_amount") or 0.0
        raw_paid = row.get("paid_amount") or 0.0
        
        row["total_amount_usd"] = round(raw_total * multiplier, 2)
        row["paid_amount_usd"] = round(raw_paid * multiplier, 2)

    
    return {
        "status_code": 200,
        "status": "success",
        "message": "Dashboard data fetched successfully",
        "data": dashboard_data
    }

@app.patch("/dashboard/orders/{order_db_id}", response_model=ApiResponse[dict])
def update_dashboard_order(order_db_id: str, update_data: DashboardUpdate, current_user: dict = Depends(get_current_user)):
    """
    Unified update endpoint for the dashboard using Order Database ID (Hex).
    Updates relevant collections based on provided fields.
    """
    # 1. Map fields to collections
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return {
            "status_code": 200,
            "status": "success",
            "message": "No changes provided",
            "data": None
        }

    # 2. Map fields to collections
    client_fields = ["client_id", "client_country", "client_Email", "client_whatsapp_number", "client_link", "bank_account", "client_affiliations"]
    order_fields = ["manuscript_id", "order_date", "reference_id", "ref_no", "journal_name", "title", "order_type", "index", "rank", "currency", "total_amount", "writing_amount", "modification_amount", "implementation_amount", "po_amount", "writing_start_date", "writing_end_date", "modification_start_date", "modification_end_date", "po_start_date", "po_end_date", "payment_status", "remarks", "order_status", "payment_drive_link", "paid_amount", "clients_details", "client_details", "client_drive_link", "is_new_order"]
    payment_fields = ["phase_1_payment", "phase_1_payment_date", "phase_1_payment_details", "phase_2_payment", "phase_2_payment_date", "phase_2_payment_details", "phase_3_payment", "phase_3_payment_date", "phase_3_payment_details","payment_status", "paid_amount"]

    # Get the order to verify it exists and find linked client
    try:
        order = orders_collection.find_one({"_id": ObjectId(order_db_id)})
    except Exception:
         raise HTTPException(status_code=400, detail="Invalid order_db_id format")
         
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_client_id = order["client_id"]
    order_custom_id = order["order_id"]

    # 3. Perform Updates
    
    # Update Clients & Handle client_id change
    client_updates = {f: update_dict[f] for f in client_fields if f in update_dict}
    if client_updates:
        # Check if client_id itself is changing
        new_client_id = client_updates.get("client_id")
        
        # Map dashboard field names back to client collection names
        mapped_client_updates = {}
        mapping = {
            "client_id": "client_id",
            "client_country": "country",
            "client_Email": "email",
            "client_whatsapp_number": "whatsapp_no",
            "client_link": "client_link",
            "bank_account": "bank_account",
            "client_affiliations": "affiliation",
            "client_affiliations": "affiliation"
        }
        for k, v in client_updates.items():
            mapped_client_updates[mapping.get(k, k)] = v

        # Update the client record
        clients_collection.update_one({"client_id": old_client_id}, {"$set": mapped_client_updates})

        # If client_id changed, ripple to all related collections
        if new_client_id and new_client_id != old_client_id:
            orders_collection.update_many({"client_id": old_client_id}, {"$set": {"client_id": new_client_id}})
            payments_collection.update_many({"client_id": old_client_id}, {"$set": {"client_id": new_client_id}})
            manuscripts_collection.update_many({"client_id": old_client_id}, {"$set": {"client_id": new_client_id}})
            # Update local variable for subsequent order updates in this same request
            old_client_id = new_client_id

    # Update Orders
    order_updates = {f: update_dict[f] for f in order_fields if f in update_dict}
    if order_updates:
        # Map dashboard field names back to order collection names if different
        mapped_order_updates = {}
        mapping = {"ref_no": "client_ref_no", "client_details": "clients_details"}
        for k, v in order_updates.items():
            mapped_order_updates[mapping.get(k, k)] = v
        mapped_order_updates["updated_at"] = datetime.utcnow()
        orders_collection.update_one({"_id": ObjectId(order_db_id)}, {"$set": mapped_order_updates})

    # Update Payments — direct field update (same pattern as orders/clients)
    payment_updates_raw = {f: update_dict[f] for f in payment_fields if f in update_dict}
    if payment_updates_raw:
        payments_collection.update_one(
            {"order_id": order_custom_id},
            {"$set": payment_updates_raw},
            upsert=True
        )
        
    # Sync with payment_history_collection if order, client, or payment fields were updated
    if client_updates or order_updates or payment_updates_raw:
        latest_order = orders_collection.find_one({"order_id": order_custom_id})
        if latest_order:
            latest_client = clients_collection.find_one({"client_id": latest_order["client_id"]})
            latest_payment = payments_collection.find_one({"order_id": order_custom_id})
            
            client_name = latest_client.get("name") if latest_client else "Unknown Client"
            
            history_record = {
                "client_name": client_name,
                "client_id": latest_order["client_id"],
                "order_id": order_custom_id,
                "reference_id": latest_order.get("reference_id"),
                "order_title": latest_order.get("title") or "Unknown Title",
                "amount": latest_order.get("total_amount", 0.0),
                "paid_amount": latest_payment.get("paid_amount", 0.0) if latest_payment else 0.0,
                "payment_date": latest_payment.get("payment_date") if latest_payment else None,
                "payment_received_account": latest_payment.get("payment_received_account") if latest_payment else None,
                "phase_1_payment": latest_payment.get("phase_1_payment", 0.0) if latest_payment else 0.0,
                "phase_1_payment_date": latest_payment.get("phase_1_payment_date") if latest_payment else None,
                "phase_1_payment_details": latest_payment.get("phase_1_payment_details") if latest_payment else None,
                "phase_2_payment": latest_payment.get("phase_2_payment", 0.0) if latest_payment else 0.0,
                "phase_2_payment_date": latest_payment.get("phase_2_payment_date") if latest_payment else None,
                "phase_2_payment_details": latest_payment.get("phase_2_payment_details") if latest_payment else None,
                "phase_3_payment": latest_payment.get("phase_3_payment", 0.0) if latest_payment else 0.0,
                "phase_3_payment_date": latest_payment.get("phase_3_payment_date") if latest_payment else None,
                "phase_3_payment_details": latest_payment.get("phase_3_payment_details") if latest_payment else None,
                "updated_at": datetime.utcnow()
            }
            
            payment_history_collection.update_one(
                {"order_id": order_custom_id},
                {
                    "$set": history_record,
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )



    return {
        "status_code": 200,
        "status": "success",
        "message": "Dashboard order updated successfully",
        "data": None
    }

# --- UNIFIED CREATE API ---

@app.post("/unified/create", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def create_unified_record(request: UnifiedCreateRequest, current_user: dict = Depends(get_current_user)):
    """
    Unified API to create client, order, manuscript, and payment records in one request.
    Accessible to all roles (Employee, Manager, Admin).

    Features:
    - Creates client if doesn't exist, updates if exists
    - Always creates order with unique reference_id
    - Optionally creates manuscript linked to client and order
    - Optionally creates payment record
    - payment_drive_link flows from client to order automatically
    """

    # Step 1: Handle Client ID and Reference ID Auto-generation
    if not request.client_id and not clients_collection.find_one({"name": request.client_name}):
        request.client_id = generate_custom_id("CL", clients_collection, current_user)
    
    if not request.reference_id:
        request.reference_id = generate_custom_id("REF", orders_collection, current_user)

    # Step 1: Handle Client Creation/Update
    existing_client = clients_collection.find_one({"client_id": request.client_id}) if request.client_id else clients_collection.find_one({"name": request.client_name})


    if not existing_client:
        # Create new client
        client_data = {
            "client_id": request.client_id,
            "name": request.client_name,
            "country": request.client_country,
            "email": request.client_email,
            "whatsapp_no": request.client_whatsapp_no,
            "client_ref_no": request.client_ref_no,
            "client_link": request.client_link,
            "bank_account": request.client_bank_account,
            "affiliation": request.client_affiliation,
            "payment_drive_link": request.payment_drive_link,
            "client_drive_link": request.client_drive_link,
            "client_drive_link": request.client_drive_link,
            "total_orders": 0,
            "client_handler": current_user.get("email") if current_user["role"] == UserRole.EMPLOYEE else get_user_email_by_name(request.client_handler),
            "created_at": datetime.utcnow()
        }
        clients_collection.insert_one(client_data)
        client_id = request.client_id
        client_payment_drive_link = request.payment_drive_link
    else:
        # Use existing client, do not update fields
        client_id = existing_client["client_id"]
        
        # Get the current payment_drive_link from existing client
        client_payment_drive_link = existing_client.get("payment_drive_link")

    # Step 2: Create Manuscript (Optional)
    manuscript_id = None
    if request.create_manuscript and request.manuscript_title:
        manuscript_data = {
            "manuscript_id": f"MS-{client_id}-{request.reference_id}",
            "title": request.manuscript_title,
            "journal_name": request.manuscript_journal_name or request.journal_name,
            "order_type": request.order_type,
            "client_id": client_id,
            "created_at": datetime.utcnow()
        }
        manuscripts_collection.insert_one(manuscript_data)
        manuscript_id = manuscript_data["manuscript_id"]

    # Step 3: Create Order
    # Generate unique order_id
    global_order_count = orders_collection.count_documents({}) + 1
    order_id = f"ORD-{datetime.utcnow().strftime('%Y')}-{global_order_count:03d}"
    
    # Ensure uniqueness in case of deleted documents mapping to same count
    while orders_collection.find_one({"order_id": order_id}):
        global_order_count += 1
        order_id = f"ORD-{datetime.utcnow().strftime('%Y')}-{global_order_count:03d}"

    # Ensure reference_id is unique
    if orders_collection.find_one({"reference_id": request.reference_id}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reference ID '{request.reference_id}' already exists"
        )

    order_data = {
        "order_id": order_id,
        "reference_id": request.reference_id,
        "profile_name": request.profile_name,
        "client_ref_no": request.client_ref_no,
        "s_no": global_order_count,
        "order_date": parse_date(request.order_date),
        "client_id": client_id,
        "manuscript_id": manuscript_id,
        "journal_name": request.journal_name,
        "title": request.title,
        "order_type": request.order_type,
        "index": request.index,
        "rank": request.rank,
        "currency": request.currency or "USD",
        "total_amount": request.total_amount or 0,
        "writing_amount": request.writing_amount or 0,
        "modification_amount": request.modification_amount or 0,
        "implementation_amount": request.implementation_amount or 0,
        "po_amount": request.po_amount or 0,
        "writing_start_date": parse_date(request.writing_start_date) or parse_date(request.write_start_date),
        "writing_end_date": parse_date(request.writing_end_date),
        "modification_start_date": parse_date(request.modification_start_date),
        "modification_end_date": parse_date(request.modification_end_date),
        "po_start_date": parse_date(request.po_start_date),
        "po_end_date": parse_date(request.po_end_date),
        "payment_status": request.payment_status or "Pending",
        "order_status": "Active",
        "payment_drive_link": request.payment_drive_link or client_payment_drive_link,
        "clients_details": request.clients_details or getattr(request, 'client_details', None),
        "client_drive_link": request.client_drive_link,
        "receive_bank_account": request.receive_bank_account,
        "is_new_order": request.is_new_order or "yes",
        "remarks": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    orders_collection.insert_one(order_data)

    # Step 4: Create Payment (Optional)
    payment_created = False
    if request.create_payment and request.payment_amount:
        payment_data = {
            "client_ref_number": request.client_ref_no,
            "reference_id": request.reference_id,
            "client_id": client_id,
            "order_id": order_id,
            "phase": request.payment_phase or 1,
            "amount": request.payment_amount,
            "payment_received_account": request.payment_received_account,
            "payment_date": parse_date(request.payment_date) or datetime.utcnow(),
            "status": "paid",
            "paid_amount": request.payment_amount,
            "created_at": datetime.utcnow()
        }

        # Update phase-specific fields
        phase = payment_data["phase"]
        payment_data[f"phase_{phase}_payment"] = request.payment_amount
        payment_data[f"phase_{phase}_payment_date"] = payment_data["payment_date"]

        payments_collection.insert_one(payment_data)

        # Sync with payment_history_collection
        history_item = {
            "client_name": request.client_name,
            "client_id": client_id,
            "order_id": order_id,
            "reference_id": request.reference_id,
            "amount": request.total_amount or request.payment_amount,
            "paid_amount": request.payment_amount,
            "payment_date": payment_data["payment_date"],
            "payment_received_account": request.payment_received_account,
            "order_title": request.title or "Unknown Title",
            "phase_1_payment": payment_data.get("phase_1_payment", 0.0),
            "phase_1_payment_date": payment_data.get("phase_1_payment_date"),
            "phase_1_payment_details": payment_data.get("phase_1_payment_details"),
            "phase_2_payment": payment_data.get("phase_2_payment", 0.0),
            "phase_2_payment_date": payment_data.get("phase_2_payment_date"),
            "phase_2_payment_details": payment_data.get("phase_2_payment_details"),
            "phase_3_payment": payment_data.get("phase_3_payment", 0.0),
            "phase_3_payment_date": payment_data.get("phase_3_payment_date"),
            "phase_3_payment_details": payment_data.get("phase_3_payment_details"),
            "created_at": datetime.utcnow()
        }
        payment_history_collection.insert_one(history_item)

        # Update order total_amount only if it wasn't already set from request
        if not order_data.get("total_amount"):
            orders_collection.update_one(
                {"order_id": order_id},
                {"$set": {"total_amount": request.payment_amount}}
            )
        payment_created = True

    # Step 5: Update Client Order Count
    clients_collection.update_one(
        {"client_id": client_id},
        {"$inc": {"total_orders": 1}}
    )


    # Return comprehensive response
    return {
        "status_code": 201,
        "status": "success",
        "message": "Unified record created successfully",
        "data": {
            "client_id": client_id,
            "order_id": order_id,
            "reference_id": request.reference_id,
            "manuscript_id": manuscript_id,
            "payment_created": payment_created,
            "client_created": existing_client is None,
            "created_records": {
                "client": existing_client is None,
                "order": True,
                "manuscript": request.create_manuscript,
                "payment": payment_created
            },
            "payment_drive_link_used": client_payment_drive_link
        }
    }


