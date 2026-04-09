from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from schemas import (
    UserCreate, 
    UserResponse, 
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
    OTPVerifyRequest
)
import random
import smtplib
from email.message import EmailMessage
from config import (
    SMTP_SERVER, 
    SMTP_PORT, 
    SMTP_USERNAME, 
    SMTP_PASSWORD, 
    EMAIL_FROM
)
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    require_manager_or_higher
)
from database import (
    users_collection, 
    tokens_collection,
    clients_collection,
    manuscripts_collection,
    orders_collection,
    payments_collection,
    otps_collection
)
from bson import ObjectId

app = FastAPI(title="Email Dashboard API")

# --- HELPER ---
def send_otp_email(to_email: str, otp: str):
    """
    Sends an OTP email via SMTP.
    """
    msg = EmailMessage()
    msg.set_content(f"Your OTP for login is: {otp}\n\nThis OTP is valid for 5 minutes.")
    msg["Subject"] = "Login OTP - Email Dashboard"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    print(f"\n[OTP DEBUG] Attempting to send email to {to_email} via {SMTP_SERVER}:{SMTP_PORT}\n")
    try:
        if SMTP_PORT == 465:
            # Port 465 requires SMTP_SSL from the start
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            # Port 587 (and others) typically use STARTTLS
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def format_mongo_id(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Email Dashboard API"}

# --- INITIALIZATION ---

@app.post("/init-super-admin", status_code=status.HTTP_201_CREATED)
def init_super_admin(user: UserCreate):
    """
    Endpoint to initialize the first super admin user. 
    Only works if no admin exists in the database.
    """
    if users_collection.find_one({"role": UserRole.ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Admin already exists"
        )
    
    user_dict = user.model_dump()
    user_dict["password"] = get_password_hash(user.password)
    user_dict["role"] = UserRole.ADMIN
    users_collection.insert_one(user_dict)
    return {"message": "Super Admin created successfully"}

# --- LOGIN ---

@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
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
    if user["role"] in [UserRole.ADMIN, UserRole.MANAGER]:
        otp = str(random.randint(100000, 999999))
        
        # Store OTP (overwrite any previous OTP for this user)
        otps_collection.update_one(
            {"email": user["email"]},
            {"$set": {
                "otp": otp,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        # Send OTP via SMTP
        sent = send_otp_email(user["email"], otp)
        if not sent:
             print(f"\n[OTP DEBUG] FAILED to send email to {user['email']}. OTP: {otp}\n")
        
        return LoginResponse(otp_required=True, email=user["email"])

    # Regular login for Employee
    access_token = create_access_token(data={"sub": user["email"]})
    
    # Store token in tokens table
    tokens_collection.insert_one({
        "user_email": user["email"],
        "token": access_token,
        "created_at": datetime.utcnow()
    })
    
    return LoginResponse(access_token=access_token, token_type="bearer")

@app.post("/verify-otp", response_model=Token)
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
    
    return {"access_token": access_token, "token_type": "bearer"}

# --- USER & ADMIN CREATION ---

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    
    # Logic for Admin role restriction
    if user.role == UserRole.ADMIN:
        # Only existing Admin can create another Admin
        if current_user["role"] != UserRole.ADMIN:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can create another Admin"
            )
             
        admin_count = users_collection.count_documents({"role": UserRole.ADMIN})
        if admin_count >= 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 2 Admins allowed"
            )
            
    user_dict = user.model_dump()
    user_dict["password"] = get_password_hash(user.password)
    result = users_collection.insert_one(user_dict)
    
    user_dict["_id"] = str(result.inserted_id)
    return user_dict

# --- PASSWORD MANAGEMENT ---

@app.put("/users/me/password")
def update_own_password(data: PasswordUpdate, current_user: dict = Depends(get_current_user)):
    """
    Update own password. Available to all roles.
    """
    hashed_password = get_password_hash(data.new_password)
    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"password": hashed_password}}
    )
    return {"message": "Password updated successfully"}

@app.put("/users/password")
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

    hashed_password = get_password_hash(data.new_password)
    users_collection.update_one(
        {"email": data.email},
        {"$set": {"password": hashed_password}}
    )
    return {"message": f"Password for {data.email} updated successfully"}

# --- VISIBILITY ---

@app.get("/users", response_model=list[UserResponse])
def get_all_users(current_user: dict = Depends(require_manager_or_higher)):
    """
    Get all regular Users. Accessible to Admin and Super Admin.
    """
    users = list(users_collection.find({"role": UserRole.EMPLOYEE}))
    for u in users:
        u["_id"] = str(u["_id"])
    return users

#@app.get("/admins", response_model=list[UserResponse])
def get_all_admins(current_user: dict = Depends(require_admin)):
    """
    Get all Admins and Super Admins. Accessible to Super Admin only.
    """
    admins = list(users_collection.find({"role": {"$in": [UserRole.MANAGER, UserRole.ADMIN]}}))
    for a in admins:
        a["_id"] = str(a["_id"])
    return admins

# --- CLIENTS ---

@app.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, current_user: dict = Depends(require_manager_or_higher)):
    client_dict = client.model_dump()
    client_dict["created_at"] = datetime.utcnow()
    result = clients_collection.insert_one(client_dict)
    client_dict["_id"] = str(result.inserted_id)
    return client_dict

@app.get("/clients", response_model=list[ClientResponse])
def get_clients(current_user: dict = Depends(require_manager_or_higher)):
    clients = list(clients_collection.find())
    return [format_mongo_id(c) for c in clients]

@app.get("/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, current_user: dict = Depends(require_manager_or_higher)):
    client = clients_collection.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return format_mongo_id(client)

# --- MANUSCRIPTS ---

@app.post("/manuscripts", response_model=ManuscriptResponse, status_code=status.HTTP_201_CREATED)
def create_manuscript(manuscript: ManuscriptCreate, current_user: dict = Depends(require_manager_or_higher)):
    # Verify client exists
    if not clients_collection.find_one({"client_id": manuscript.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    ms_dict = manuscript.model_dump()
    ms_dict["created_at"] = datetime.utcnow()
    result = manuscripts_collection.insert_one(ms_dict)
    ms_dict["_id"] = str(result.inserted_id)
    return ms_dict

@app.get("/manuscripts", response_model=list[ManuscriptResponse])
def get_manuscripts(current_user: dict = Depends(require_manager_or_higher)):
    ms = list(manuscripts_collection.find())
    return [format_mongo_id(m) for m in ms]

# --- ORDERS ---

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, current_user: dict = Depends(require_manager_or_higher)):
    # Verify client and manuscript exist
    if not clients_collection.find_one({"client_id": order.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    if not manuscripts_collection.find_one({"manuscript_id": order.manuscript_id}):
        raise HTTPException(status_code=400, detail="Invalid manuscript_id")
    
    order_dict = order.model_dump()
    order_dict["created_at"] = datetime.utcnow()
    order_dict["updated_at"] = datetime.utcnow()
    result = orders_collection.insert_one(order_dict)
    order_dict["_id"] = str(result.inserted_id)
    return order_dict

@app.get("/orders", response_model=list[OrderResponse])
def get_orders(current_user: dict = Depends(require_manager_or_higher)):
    orders = list(orders_collection.find())
    return [format_mongo_id(o) for o in orders]

# --- PAYMENTS ---

@app.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentCreate, current_user: dict = Depends(require_manager_or_higher)):
    if not clients_collection.find_one({"client_id": payment.client_id}):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    
    pay_dict = payment.model_dump()
    pay_dict["created_at"] = datetime.utcnow()
    result = payments_collection.insert_one(pay_dict)
    pay_dict["_id"] = str(result.inserted_id)
    return pay_dict

@app.get("/payments", response_model=list[PaymentResponse])
def get_payments(current_user: dict = Depends(require_manager_or_higher)):
    payments = list(payments_collection.find())
    return [format_mongo_id(p) for p in payments]

# --- DASHBOARD ---

@app.get("/dashboard/orders", response_model=list[DashboardOrderResponse])
def get_dashboard_orders(current_user: dict = Depends(get_current_user)):
    """
    Unified endpoint for the frontend dashboard.
    Aggregates data from Orders, Clients, and Payments.
    """
    all_orders = list(orders_collection.find())
    dashboard_data = []
    
    for order in all_orders:
        client = clients_collection.find_one({"client_id": order["client_id"]})
        payments = list(payments_collection.find({"order_id": order["order_id"]}))
        
        # Aggregate payment info
        phase_payments = {1: {"amount": 0.0, "date": None}, 2: {"amount": 0.0, "date": None}, 3: {"amount": 0.0, "date": None}}
        for p in payments:
            phase = p.get("phase", 1)
            if phase in phase_payments:
                phase_payments[phase]["amount"] += p.get("amount", 0.0)
                if not phase_payments[phase]["date"]:
                    phase_payments[phase]["date"] = p.get("payment_date")

        entry = {
            "s_no": order.get("s_no"),
            "order_date": order.get("order_date"),
            "client_id": order.get("client_id"),
            "client_location": client.get("location") if client else None,
            "client_Email": client.get("email") if client else None,
            "client_whatsapp_number": client.get("whatsapp_no") if client else None,
            "ref_no": order.get("client_ref_no"),
            "manuscript_id": order.get("manuscript_id"),
            "order_type": order.get("order_type"),
            "index": order.get("index"),
            "rank": order.get("rank"),
            "currency": order.get("currency"),
            "total_amount": order.get("total_amount"),
            "writing_amount": order.get("writing_amount"),
            "modification_amount": order.get("modification_amount"),
            "po_amount": order.get("po_amount"),
            "writing_start_date": order.get("writing_start_date"),
            "writing_end_date": order.get("writing_end_date"),
            "modification_start_date": order.get("modification_start_date"),
            "modification_end_date": order.get("modification_end_date"),
            "po_start_date": order.get("po_start_date"),
            "po_end_date": order.get("po_end_date"),
            "phase" : None, 
            "phase_1_payment": phase_payments[1]["amount"],
            "phase_1_payment_date": phase_payments[1]["date"],
            "phase_2_payment": phase_payments[2]["amount"],
            "phase_2_payment_date": phase_payments[2]["date"],
            "phase_3_payment": phase_payments[3]["amount"],
            "phase_3_payment_date": phase_payments[3]["date"],
            "payment_status": order.get("payment_status"),
            "client_link": client.get("client_link") if client else None,
            "bank_account": client.get("bank_account") if client else None,
            "client_affiliations": client.get("affiliation") if client else None,
            "remarks": order.get("remarks")
        }
        dashboard_data.append(entry)
        
    return dashboard_data

