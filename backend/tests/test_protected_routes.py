import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_unauthorized_profile_access():
    response = client.get("/user/profile")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    response = client.put("/user/profile", json={
        "full_name": "Updated Name",
        "about": "I love quizzes!"
    })
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"