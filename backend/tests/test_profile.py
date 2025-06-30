import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_profile_view_and_update():
    # Sign up and log in first
    client.post("/auth/signup", json={
        "email": "profile@example.com",
        "full_name": "Profile User",
        "password": "profilepass"
    })
 
    login_resp = client.post("/auth/login", data={
        "username": "profile@example.com",
        "password": "profilepass"
    })
    token = login_resp.json()["access_token"]

    # View profile
    view = client.get("/user/profile", headers={
        "Authorization": f"Bearer {token}"
    })
    assert view.status_code == 200
    assert view.json()["email"] == "profile@example.com"

    # Update profile
    update = client.put("/user/profile", json={
        "full_name": "Updated Name",
        "about": "I love quizzes!"
    }, headers={
        "Authorization": f"Bearer {token}"
    })
    assert update.status_code == 200
    assert update.json()["full_name"] == "Updated Name"
