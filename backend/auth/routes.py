# ==============================
# auth/routes.py (refactored)
# ==============================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from auth.utils import get_password_hash, verify_password, create_access_token
from db.session import get_db
from db.models import User
from auth.schemas import UserOut, UserCreate

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/signup", response_model=UserOut)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user after verifying email uniqueness.
    """
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@auth_router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates user and returns JWT token.
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=60)
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }
