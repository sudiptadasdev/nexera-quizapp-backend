import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_protected_dashboard_access_without_token():
    response = client.get("/user/dashboard")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

def test_protected_dashboard_access_with_token():
    client.post("/auth/signup", json={
        "email": "dashboard@example.com",
        "full_name": "Dashboard User",
        "password": "dashpass"
    })

    login = client.post("/auth/login", data={
        "username": "dashboard@example.com",
        "password": "dashpass"
    })
    token = login.json()["access_token"]

    response = client.get("/user/dashboard", headers={
        "Authorization": f"Bearer {token}"
    })

    assert response.status_code == 200