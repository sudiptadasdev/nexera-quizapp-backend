import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_quiz_history_access_without_token():
    response = client.get("/user/dashboard/history")
    assert response.status_code == 403

def test_quiz_history_access_with_token():
    client.post("/auth/signup", json={
        "email": "history@example.com",
        "full_name": "History Tester",
        "password": "hispass"
    })

    login = client.post("/auth/login", data={
        "username": "history@example.com",
        "password": "hispass"
    })
    token = login.json()["access_token"]

    response = client.get("/user/dashboard/history", headers={
        "Authorization": f"Bearer {token}"
    })

    assert response.status_code == 200
    assert isinstance(response.json(), list)