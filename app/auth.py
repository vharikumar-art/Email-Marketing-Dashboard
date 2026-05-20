from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database import users_collection, tokens_collection
from app.schemas import TokenData, UserRole
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ENCRYPTION_KEY

fernet = Fernet(ENCRYPTION_KEY.encode('utf-8')) if ENCRYPTION_KEY else None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def encrypt_password(plain_password: str) -> str:
    if not fernet:
        raise Exception("ENCRYPTION_KEY not set in environment or config")
    return fernet.encrypt(plain_password.encode('utf-8')).decode('utf-8')

def decrypt_password(encrypted_password: str) -> str:
    if not fernet:
        return "ERROR: KEY MISSING"
    if not encrypted_password:
        return ""
    try:
        return fernet.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    except Exception:
        return "DECRYPTION_FAILED"

def verify_password(plain_password: str, stored_password: str) -> bool:
    # First try to see if it's plaintext (fallback testing)
    if plain_password == stored_password:
        return True
    
    # If not, try decrypting the stored password
    decrypted = decrypt_password(stored_password)
    if decrypted == "DECRYPTION_FAILED":
        return False
        
    return decrypted == plain_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token exists in database (not revoked/logged out)
    token_record = tokens_collection.find_one({"token": token})
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or logged out",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = users_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

def require_manager_or_higher(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required",
        )
    return current_user
