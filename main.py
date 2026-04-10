from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from schemas import (
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
    DashboardUpdate,
    ApiResponse
)
import random
import smtplib
from email.message import EmailMessage
from config import (
    SMTP_SERVER, 
    SMTP_PORT, 
    SMTP_USERNAME, 
    SMTP_PASSWORD, 
    EMAIL_FROM,
    ALLOWED_ORIGINS
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


@app.get("/", response_model=ApiResponse[dict])
def read_root():
    return {
        "status_code": 200,
        "status": "success",
        "message": "Welcome to Email Dashboard API",
        "data": None
    }

# --- INITIALIZATION ---

@app.post("/init-super-admin", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
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
    
    return {
        "status_code": 201,
        "status": "success",
        "message": "Super Admin created successfully",
        "data": None
    }

# --- LOGIN ---

@app.post("/login", response_model=ApiResponse[LoginResponse])
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
        
        # Store OTP
        otps_collection.update_one(
            {"email": user["email"]},
            {"$set": {
                "otp": otp,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        # Send OTP
        sent = send_otp_email(user["email"], otp)
        
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
    return {
        "status_code": 201,
        "status": "success",
        "message": "User created successfully",
        "data": user_dict
    }

# --- PASSWORD MANAGEMENT ---

@app.put("/users/me/password", response_model=ApiResponse[dict])
def update_own_password(data: PasswordUpdate, current_user: dict = Depends(get_current_user)):
    """
    Update own password. Available to all roles.
    """
    hashed_password = get_password_hash(data.new_password)
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

    hashed_password = get_password_hash(data.new_password)
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
    users = list(users_collection.find({"role": UserRole.EMPLOYEE}))
    for u in users:
        u["_id"] = str(u["_id"])
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
    admins = list(users_collection.find({"role": {"$in": [UserRole.MANAGER, UserRole.ADMIN]}}))
    for a in admins:
        a["_id"] = str(a["_id"])
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

    users_collection.update_one(
        {"email": data.email},
        {"$set": {"permissions": data.permissions}}
    )
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Permissions updated for {data.email}",
        "data": None
    }

@app.get("/users/me/details", response_model=ApiResponse[UserDetailResponse])
def get_own_details(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile details including handled clients.
    """
    # Find active clients handled by this user
    clients = list(clients_collection.find({"client_handler": current_user.get("full_name")}))
    
    user_data = format_mongo_id(current_user)
    user_data["handled_clients"] = [format_mongo_id(c) for c in clients]
    
    return {
        "status_code": 200,
        "status": "success",
        "message": "User details fetched successfully",
        "data": user_data
    }

@app.get("/users/{email}/details", response_model=ApiResponse[UserDetailResponse])
def get_user_details(email: str, current_user: dict = Depends(require_manager_or_higher)):
    """
    Get profile details of any user including handled clients.
    Restricted to Admin and Manager.
    """
    target_user = users_collection.find_one({"email": email})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Find clients handled by this target user
    clients = list(clients_collection.find({"client_handler": target_user.get("full_name")}))
    
    user_data = format_mongo_id(target_user)
    user_data["handled_clients"] = [format_mongo_id(c) for c in clients]
    
    return {
        "status_code": 200,
        "status": "success",
        "message": f"Details for {email} fetched successfully",
        "data": user_data
    }

# --- CLIENTS ---

@app.post("/clients", response_model=ApiResponse[ClientResponse], status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, current_user: dict = Depends(get_current_user)):
    # Check if client_id already exists
    if clients_collection.find_one({"client_id": client.client_id}):
        raise HTTPException(status_code=400, detail="Client ID already exists")

    client_dict = client.model_dump()
    
    # Dynamic Client Handler logic
    if not client_dict.get("client_handler"):
        if current_user["role"] == UserRole.EMPLOYEE:
            client_dict["client_handler"] = current_user.get("full_name")
        else:
            client_dict["client_handler"] = None
            
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
        query = {"client_handler": current_user.get("full_name")}
    clients = list(clients_collection.find(query))
    return {
        "status_code": 200,
        "status": "success",
        "message": "Clients fetched successfully",
        "data": [format_mongo_id(c) for c in clients]
    }

@app.get("/clients/{client_id}", response_model=ApiResponse[ClientResponse])
def get_client(client_id: str, current_user: dict = Depends(require_manager_or_higher)):
    client = clients_collection.find_one({"client_id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "status_code": 200,
        "status": "success",
        "message": "Client fetched successfully",
        "data": format_mongo_id(client)
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
        # Get clients handled by this employee
        my_clients = list(clients_collection.find({"client_handler": current_user.get("full_name")}))
        my_client_ids = [c["client_id"] for c in my_clients]
        query = {"client_id": {"$in": my_client_ids}}
        
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
    return {
        "status_code": 201,
        "status": "success",
        "message": "Order created successfully",
        "data": order_dict
    }

@app.get("/orders", response_model=ApiResponse[list[OrderResponse]])
def get_orders(current_user: dict = Depends(require_manager_or_higher)):
    orders = list(orders_collection.find())
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
def get_payments(current_user: dict = Depends(require_manager_or_higher)):
    payments = list(payments_collection.find())
    return {
        "status_code": 200,
        "status": "success",
        "message": "Payments fetched successfully",
        "data": [format_mongo_id(p) for p in payments]
    }

# --- DASHBOARD ---

@app.get("/dashboard/orders", response_model=ApiResponse[list[DashboardOrderResponse]])
def get_dashboard_orders(current_user: dict = Depends(get_current_user)):
    """
    Unified endpoint for the frontend dashboard.
    Aggregates data from Orders, Clients, and Payments.
    Client-First Logic: Shows clients even if no orders exist.
    """
    # 1. Get filtered clients
    client_query = {}
    if current_user["role"] == UserRole.EMPLOYEE:
        client_query = {"client_handler": current_user.get("full_name")}
        
    all_clients = list(clients_collection.find(client_query))
    dashboard_data = []
    
    for client in all_clients:
        # 2. Find orders for this client
        client_orders = list(orders_collection.find({"client_id": client["client_id"]}))
        
        if not client_orders:
            # Create a "Placeholder" row for clients without orders
            entry = {
                "s_no": None,
                "order_date": None,
                "client_id": client.get("client_id"),
                "client_location": client.get("location"),
                "client_Email": client.get("email"),
                "client_whatsapp_number": client.get("whatsapp_no"),
                "ref_no": client.get("client_ref_no"),
                "manuscript_id": None,
                "order_type": None,
                "index": None,
                "rank": None,
                "currency": "USD",
                "total_amount": 0.0,
                "writing_amount": 0.0,
                "modification_amount": 0.0,
                "po_amount": 0.0,
                "payment_status": "No Order",
                "client_link": client.get("client_link"),
                "bank_account": client.get("bank_account"),
                "client_affiliations": client.get("affiliation"),
                "remarks": "No active orders for this client"
            }
            dashboard_data.append(entry)
            continue

        # 3. Process existing orders
        for order in client_orders:
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
                "client_location": client.get("location"),
                "client_Email": client.get("email"),
                "client_whatsapp_number": client.get("whatsapp_no"),
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
                "client_link": client.get("client_link"),
                "bank_account": client.get("bank_account"),
                "client_affiliations": client.get("affiliation"),
                "remarks": order.get("remarks")
            }
            dashboard_data.append(entry)
        
    return {
        "status_code": 200,
        "status": "success",
        "message": "Dashboard data fetched successfully",
        "data": dashboard_data
    }

@app.patch("/dashboard/orders/{order_id}", response_model=ApiResponse[dict])
def update_dashboard_order(order_id: str, update_data: DashboardUpdate, current_user: dict = Depends(get_current_user)):
    """
    Unified update endpoint for the dashboard.
    Checks column-level permissions for Employees.
    Updates relevant collections based on provided fields.
    """
    # 1. Permission Check
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return {
            "status_code": 200,
            "status": "success",
            "message": "No changes provided",
            "data": None
        }

    if current_user["role"] == UserRole.EMPLOYEE:
        allowed = current_user.get("permissions", {}).get("dashboard", [])
        for field in update_dict.keys():
            if field not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have permission to update column: {field}"
                )

    # 2. Map fields to collections
    client_fields = ["client_location", "client_Email", "client_whatsapp_number", "client_link", "bank_account", "client_affiliations"]
    order_fields = ["order_date", "ref_no", "order_type", "index", "rank", "currency", "total_amount", "writing_amount", "modification_amount", "po_amount", "writing_start_date", "writing_end_date", "modification_start_date", "modification_end_date", "po_start_date", "po_end_date", "payment_status", "remarks"]
    payment_fields = ["phase_1_payment", "phase_1_payment_date", "phase_2_payment", "phase_2_payment_date", "phase_3_payment", "phase_3_payment_date"]

    # Get the order to find linked client
    order = orders_collection.find_one({"order_id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    client_id = order["client_id"]

    # 3. Perform Updates
    
    # Update Clients
    client_updates = {f: update_dict[f] for f in client_fields if f in update_dict}
    if client_updates:
        # Map dashboard field names back to client collection names if different
        mapped_client_updates = {}
        mapping = {
            "client_location": "location",
            "client_Email": "email",
            "client_whatsapp_number": "whatsapp_no",
            "client_link": "client_link",
            "bank_account": "bank_account",
            "client_affiliations": "affiliation"
        }
        for k, v in client_updates.items():
            mapped_client_updates[mapping.get(k, k)] = v
        clients_collection.update_one({"client_id": client_id}, {"$set": mapped_client_updates})

    # Update Orders
    order_updates = {f: update_dict[f] for f in order_fields if f in update_dict}
    if order_updates:
        # Map dashboard field names back to order collection names if different
        mapped_order_updates = {}
        mapping = {
            "ref_no": "client_ref_no"
        }
        for k, v in order_updates.items():
            mapped_order_updates[mapping.get(k, k)] = v
        mapped_order_updates["updated_at"] = datetime.utcnow()
        orders_collection.update_one({"order_id": order_id}, {"$set": mapped_order_updates})

    # Update Payments
    payment_updates_raw = {f: update_dict[f] for f in payment_fields if f in update_dict}
    if payment_updates_raw:
        # Group by phase
        for phase in [1, 2, 3]:
            amt_key = f"phase_{phase}_payment"
            date_key = f"phase_{phase}_payment_date"
            
            p_updates = {}
            if amt_key in payment_updates_raw:
                p_updates["amount"] = payment_updates_raw[amt_key]
            if date_key in payment_updates_raw:
                p_updates["payment_date"] = payment_updates_raw[date_key]
            
            if p_updates:
                payments_collection.update_one(
                    {"order_id": order_id, "phase": phase},
                    {"$set": p_updates},
                    upsert=True # Create if doesn't exist for that phase
                )

    return {
        "status_code": 200,
        "status": "success",
        "message": "Dashboard order updated successfully",
        "data": None
    }

