from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.models import User
from db.session import get_db
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

# ===================================
# Security Utilities (Hash & Token)
# ===================================
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")  # Replace with secure key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer scheme to extract token from header
oauth2_scheme = HTTPBearer()

# Hash password before saving
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Verify raw password with hashed one
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    payload = data.copy()
    expire_time = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire_time})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Middleware to fetch current user from token
def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise unauthorized_exc
        uuid_user_id = uuid.UUID(user_id)
    except (JWTError, ValueError):
        raise unauthorized_exc

    user = db.query(User).filter(User.id == str(uuid_user_id)).first()
    if not user:
        raise unauthorized_exc

    return user
