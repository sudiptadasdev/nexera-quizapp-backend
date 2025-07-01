from fastapi import APIRouter, Depends, HTTPException, Depends, Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jose import jwt, JWTError
from starlette.responses import JSONResponse
from .schemas import ForgotPasswordRequest, ResetPasswordRequest
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
import os
from auth.utils import get_password_hash, verify_password, create_access_token, send_verification_email
from db.session import get_db
from db.models import User
from auth.schemas import UserOut, UserCreate
from dotenv import load_dotenv
from datetime import datetime, timedelta

router = APIRouter()
load_dotenv()
auth_router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_SECONDS = 3600

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("EMAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
    MAIL_FROM=os.getenv("EMAIL_USERNAME"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


@auth_router.post("/signup", response_model=UserOut)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pwd = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send basic registration confirmation email
    send_verification_email(to_email=user_data.email, full_name=user_data.full_name)

    return new_user

@auth_router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=60)
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db=Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    expire = datetime.utcnow() + timedelta(seconds=RESET_TOKEN_EXPIRE_SECONDS)
    token = jwt.encode({"sub": user.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    reset_url = f"http://localhost:3000/reset-password?token={token}"
    message = MessageSchema(
        subject="Reset Your NexEra Password",
        recipients=[user.email],
        body=f"Click to reset your password: {reset_url}",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    return {"message": "Password reset link sent."}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db=Depends(get_db)):
    try:
        payload = jwt.decode(request.token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password updated successfully"}