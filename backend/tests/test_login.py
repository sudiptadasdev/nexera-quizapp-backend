import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_success():
    client.post("/auth/signup", json={
        "email": "loginuser@example.com",
        "full_name": "Login User",
        "password": "securepass"
    })

    response = client.post("/auth/login", data={
        "username": "loginuser@example.com",
        "password": "securepass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_credentials():
    response = client.post("/auth/login", data={
        "username": "wrong@example.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."

def test_login_missing_fields():
    response = client.post("/auth/login", data={
        "username": "",
        "password": ""
    })
    assert response.status_code == 401