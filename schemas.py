from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class PasswordUpdate(BaseModel):
    new_password: str

class AdminPasswordUpdate(BaseModel):
    email: EmailStr
    new_password: str

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.EMPLOYEE

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    otp_required: bool = False
    email: Optional[EmailStr] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

# --- SCHEMA FROM ERD ---

class ClientBase(BaseModel):
    client_id: str
    name: str
    location: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp_no: Optional[str] = None
    client_ref_no: Optional[str] = None
    client_link: Optional[str] = None
    bank_account: Optional[str] = None
    affiliation: Optional[str] = None
    total_orders: int = 0
    client_handlers: Optional[str] = None # Ref to User email or ID

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True

class ManuscriptBase(BaseModel):
    manuscript_id: str
    title: str
    order_type: Optional[str] = None
    client_id: str # Ref to Client ObjectId string
    client_ref_no: Optional[str] = None

class ManuscriptCreate(ManuscriptBase):
    pass

class ManuscriptResponse(ManuscriptBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True

class OrderBase(BaseModel):
    order_id: str
    client_ref_no: Optional[str] = None
    s_no: Optional[int] = None
    order_date: datetime = Field(default_factory=datetime.utcnow)
    client_id: str # Ref to Client
    manuscript_id: str # Ref to Manuscript
    order_type: Optional[str] = None
    index: Optional[str] = None
    rank: Optional[str] = None
    currency: str = "USD"
    total_amount: float = 0.0
    writing_amount: float = 0.0
    modification_amount: float = 0.0
    po_amount: float = 0.0
    writing_start_date: Optional[datetime] = None
    writing_end_date: Optional[datetime] = None
    modification_start_date: Optional[datetime] = None
    modification_end_date: Optional[datetime] = None
    po_start_date: Optional[datetime] = None
    po_end_date: Optional[datetime] = None
    payment_status: str = "Pending"
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True

class PaymentBase(BaseModel):
    client_ref_number: Optional[str] = None
    client_id: str # Ref to Client
    phase: int = 1
    amount: float = 0.0
    payment_received_account: Optional[str] = None
    payment_date: Optional[datetime] = None
    phase_1_payment: Optional[float] = 0.0
    phase_1_payment_date: Optional[datetime] = None
    phase_2_payment: Optional[float] = 0.0
    phase_2_payment_date: Optional[datetime] = None
    phase_3_payment: Optional[float] = 0.0
    phase_3_payment_date: Optional[datetime] = None
    status: str = "Pending"

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True

class DashboardOrderResponse(BaseModel):
    s_no: Optional[int] = None
    order_date: datetime
    client_id: str
    client_location: Optional[str] = None
    client_Email: Optional[str] = None
    client_whatsapp_number: Optional[str] = None
    ref_no: Optional[str] = None
    manuscript_id: str
    order_type: Optional[str] = None
    index: Optional[str] = None
    rank: Optional[str] = None
    currency: str
    total_amount: float
    writing_amount: float
    modification_amount: float
    po_amount: float
    writing_start_date: Optional[datetime] = None
    writing_end_date: Optional[datetime] = None
    modification_start_date: Optional[datetime] = None
    modification_end_date: Optional[datetime] = None
    po_start_date: Optional[datetime] = None
    po_end_date: Optional[datetime] = None
    phase: Optional[int] = None
    phase_1_payment: float = 0.0
    phase_1_payment_date: Optional[datetime] = None
    phase_2_payment: float = 0.0
    phase_2_payment_date: Optional[datetime] = None
    phase_3_payment: float = 0.0
    phase_3_payment_date: Optional[datetime] = None
    payment_status: str
    client_link: Optional[str] = None
    bank_account: Optional[str] = None
    client_affiliations: Optional[str] = None
    remarks: Optional[str] = None
