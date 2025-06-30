import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from main import app
from db.session import engine
from sqlalchemy import text

client = TestClient(app)

def test_signup_success():
    # Cleanup users table first
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        conn.commit()

    response = client.post("/auth/signup", json={
        "email": "newuser_test456@example.com",
        "full_name": "New User",
        "password": "newpassword"
    })

    print("DEBUG RESPONSE:", response.status_code, response.json())
    assert response.status_code == 200
    assert response.json()["email"] == "newuser_test456@example.com"

def test_signup_existing_email():
    client.post("/auth/signup", json={
        "email": "existing@example.com",
        "full_name": "User 1",
        "password": "pass123"
    })
    response = client.post("/auth/signup", json={
        "email": "existing@example.com",
        "full_name": "User 2",
        "password": "pass456"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered."

def test_signup_invalid_email_format():
    response = client.post("/auth/signup", json={
        "email": "invalid-email",
        "full_name": "Bad Email",
        "password": "newpassword"
    })
    assert response.status_code == 422