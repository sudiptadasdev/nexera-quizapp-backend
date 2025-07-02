import sys
import os
import pytest
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException

# Adjust path to locate app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import your app's modules
from auth.routes import register_user, forgot_password, reset_password
from auth.schemas import UserCreate, ForgotPasswordRequest, ResetPasswordRequest
from db.models import User

# Config constants
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

# Dummy utility replacements
def get_password_hash(password):
    return f"hashed-{password}"

def verify_password(input_password, hashed_password):
    return hashed_password == f"hashed-{input_password}"

def create_access_token(data, expires_delta):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def send_verification_email(to_email, full_name):
    return True

def send_password_reset_email(email, full_name, url):
    return True

# Dummy DB session class
class DummyDB:
    def __init__(self):
        self.storage = {}

    def query(self, model):
        class Query:
            def __init__(inner_self, db):
                inner_self.db = db

            def filter(inner_self, condition):
                class Filter:
                    def first(inner_self2):
                        # For testing, use email string as key
                        email = condition.right.value if hasattr(condition, 'right') else condition
                        return self.storage.get(email)
                return Filter()
        return Query(self)

    def add(self, user):
        self.storage[user.email] = user

    def commit(self): pass
    def refresh(self, user): pass

# ---------- TEST CASES ----------

def test_register_user_success():
    db = DummyDB()
    user_data = UserCreate(email="new@example.com", full_name="New User", password="pass123")
    result = register_user(user_data, db=db)
    assert result.email == "new@example.com"

def test_register_user_duplicate():
    db = DummyDB()
    existing_user = User(email="exist@example.com", full_name="Test", hashed_password="hashed-pass")
    db.add(existing_user)
    with pytest.raises(HTTPException):
        user_data = UserCreate(email="exist@example.com", full_name="X", password="123")
        register_user(user_data, db=db)

@pytest.mark.asyncio
async def test_forgot_password_success():
    db = DummyDB()
    db.add(User(email="resetme@example.com", full_name="Reset Me", hashed_password="abc"))
    request = ForgotPasswordRequest(email="resetme@example.com")
    response = await forgot_password(request, db=db)
    assert response["message"] == "Password reset link sent."

@pytest.mark.asyncio
async def test_forgot_password_invalid_email():
    db = DummyDB()
    request = ForgotPasswordRequest(email="unknown@example.com")
    with pytest.raises(HTTPException) as exc_info:
        await forgot_password(request, db=db)
    assert exc_info.value.status_code == 404

def test_reset_password_success():
    db = DummyDB()
    email = "change@example.com"
    db.add(User(email=email, full_name="Changer", hashed_password="old"))
    token = jwt.encode({"sub": email, "exp": datetime.utcnow() + timedelta(seconds=3600)}, SECRET_KEY, algorithm=ALGORITHM)
    request = ResetPasswordRequest(token=token, new_password="newpass")
    response = reset_password(request, db=db)
    assert response["message"] == "Password updated successfully"

def test_reset_password_invalid_token():
    db = DummyDB()
    request = ResetPasswordRequest(token="invalid.token.value", new_password="pass")
    with pytest.raises(HTTPException):
        reset_password(request, db=db)
