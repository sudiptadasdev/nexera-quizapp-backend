import pytest
from fastapi import HTTPException
from uuid import uuid4
import sys
import os

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routes import quizzes_logic


# -----------------------
# Tests for retrieve_quiz_details
# -----------------------

def test_retrieve_quiz_details_not_found(monkeypatch):
    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def filter(self, *args, **kwargs):
                    class DummyFirst:
                        def first(self):
                            return None
                    return DummyFirst()
            return DummyQuery()

    monkeypatch.setattr("routes.quizzes_logic.get_db", lambda: DummyDB())
    monkeypatch.setattr("routes.quizzes_logic.get_current_user", lambda: {"id": 1})

    with pytest.raises(HTTPException) as exc_info:
        quizzes_logic.retrieve_quiz_details(uuid4(), DummyDB(), {"id": 1})

    assert exc_info.value.status_code == 404
    assert "Quiz not found" in str(exc_info.value.detail)


def test_retrieve_quiz_details_success(monkeypatch):
    class DummyQuestion:
        id = "q1"
        text = "What is 2+2?"
        options = ["2", "3", "4"]
        question_type = "mcq"
        correct_answer = "4"
        explanation = "Simple math"

    class DummyQuiz:
        id = "quiz123"
        created_at = "2024-01-01"
        questions = [DummyQuestion()]

    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def filter(self, *args, **kwargs):
                    class DummyFirst:
                        def first(self):
                            return DummyQuiz()
                    return DummyFirst()
            return DummyQuery()

    monkeypatch.setattr("routes.quizzes_logic.get_db", lambda: DummyDB())
    monkeypatch.setattr("routes.quizzes_logic.get_current_user", lambda: {"id": 1})

    quiz_id = uuid4()
    result = quizzes_logic.retrieve_quiz_details(quiz_id, DummyDB(), {"id": 1})

    assert result["quiz_id"] == "quiz123"
    assert len(result["questions"]) == 1
    assert result["questions"][0]["correct_answer"] == "4"
