import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from routes import user_dashboard

# -----------------------
# Tests for get_current_user_details
# -----------------------
def test_get_current_user_details_positive():
    user = type("User", (), {"id": "123", "email": "user@example.com"})()
    result = user_dashboard.get_current_user_details(current_user=user)
    assert result == {"id": "123", "email": "user@example.com"}

# -----------------------
# fetch_dashboard_summary
# -----------------------
def test_fetch_dashboard_summary_empty():
    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def join(self, other): return self
                def filter(self, condition): return self
                def all(self): return []
            return DummyQuery()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.fetch_dashboard_summary(db=DummyDB(), current_user=user)
    assert result == []

def test_fetch_dashboard_summary_db_failure():
    class DummyDB:
        def query(self, model): raise Exception("DB error")
    user = type("User", (), {"id": "1"})()
    with pytest.raises(Exception):
        user_dashboard.fetch_dashboard_summary(db=DummyDB(), current_user=user)

# -----------------------
# get_quiz_sections_by_file
# -----------------------
def test_get_quiz_sections_by_file_positive():
    class DummyQuiz:
        id = 1

    class DummyQuestion:
        text = "Q1"

    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def filter(self, condition):
                    class DummyFilter:
                        def all(self):
                            if model.__name__ == "Quiz":
                                return [DummyQuiz()]
                            elif model.__name__ == "Question":
                                return [DummyQuestion()]
                    return DummyFilter()
            return DummyQuery()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.get_quiz_sections_by_file("dummy-id", db=DummyDB(), current_user=user)
    assert isinstance(result, list)

def test_get_quiz_sections_by_file_empty():
    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def filter(self, condition):
                    class DummyFilter:
                        def all(self):
                            return []
                    return DummyFilter()
            return DummyQuery()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.get_quiz_sections_by_file("dummy-id", db=DummyDB(), current_user=user)
    assert result == []

# -----------------------
# list_user_files
# -----------------------
def test_list_user_files_positive():
    class DummyDB:
        def query(self, model):
            return type("Query", (), {
                "filter": lambda self, cond: type("Result", (), {"all": lambda self: ["file1", "file2"]})()
            })()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.list_user_files(db=DummyDB(), current_user=user)
    assert result == ["file1", "file2"]

# -----------------------
# view_profile
# -----------------------
def test_view_profile_positive():
    user = type("User", (), {
        "id": "1", "email": "user@example.com",
        "full_name": "Test User", "about": "I love quizzes."
    })()
    result = user_dashboard.view_profile(current_user=user)
    assert result["email"] == "user@example.com"

# -----------------------
# edit_profile
# -----------------------
def test_edit_profile_positive():
    class DummyDB:
        def commit(self): pass
        def refresh(self, user): pass
    class DummyUpdate:
        full_name = "Updated User"
        about = "Updated bio"
    user = type("User", (), {
        "id": "1", "full_name": "Old Name", "about": "Old about"
    })()
    result = user_dashboard.edit_profile(update=DummyUpdate(), db=DummyDB(), current_user=user)
    assert result["full_name"] == "Updated User"
    assert result["about"] == "Updated bio"

def test_edit_profile_empty_name():
    class DummyDB:
        def commit(self): pass
        def refresh(self, user): pass
    class DummyUpdate:
        full_name = "   "
        about = "Updated bio"
    user = type("User", (), {"id": "1", "full_name": "Old", "about": "Old bio"})()
    result = user_dashboard.edit_profile(update=DummyUpdate(), db=DummyDB(), current_user=user)
    assert result["full_name"] == "Old"
    assert result["about"] == "Updated bio"

# -----------------------
# get_user_quiz_history
# -----------------------
def test_get_user_quiz_history_empty():
    class DummyDB:
        def query(self, model):
            class DummyQuery:
                def join(self, other): return self
                def filter(self, *args): return self
                def order_by(self, *args): return type("Q", (), {"all": lambda self: []})()
            return DummyQuery()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.get_user_quiz_history(db=DummyDB(), current_user=user)
    assert result == []

def test_get_user_quiz_history_positive():
    class DummyQuiz:
        def __init__(self, id):
            self.id = id
            self.questions = [1, 2]
            self.created_at = datetime.utcnow()
            self.file_id = "f1"

    class DummyAttempt:
        def __init__(self, quiz_id):
            self.quiz_id = quiz_id
            self.score = 5
            self.submitted_at = datetime.utcnow()

    class DummyDB:
        def query(self, model):
            if model.__name__ == "QuizAttempt":
                return type("Query", (), {
                    "join": lambda self, other: self,
                    "filter": lambda self, *args: self,
                    "order_by": lambda self, *args: type("Q", (), {
                        "all": lambda self: [DummyAttempt("q1")]
                    })()
                })()
            elif model.__name__ == "Quiz":
                return type("Query", (), {
                    "filter": lambda self, cond: type("Q", (), {
                        "first": lambda self: DummyQuiz("q1"),
                        "order_by": lambda self, *args: type("Q2", (), {
                            "all": lambda self: [DummyQuiz("q1")]
                        })()
                    })()
                })()
            elif model.__name__ == "UploadedFile":
                return type("Query", (), {
                    "filter": lambda self, cond: type("Q", (), {
                        "first": lambda self: type("F", (), {"original_name": "doc1.txt", "id": "f1"})()
                    })()
                })()
            return None

    user = type("User", (), {"id": "1"})()
    result = user_dashboard.get_user_quiz_history(db=DummyDB(), current_user=user)
    assert isinstance(result, list)
    assert result[0]["score"] == 5

# -----------------------
# get_attempt_details
# -----------------------
def test_get_attempt_details_quiz_not_found():
    class DummyDB:
        def query(self, model):
            return type("Query", (), {"filter": lambda self, cond: type("Q", (), {"first": lambda self: None})()})()
    with pytest.raises(HTTPException):
        user_dashboard.get_attempt_details("dummy", db=DummyDB(), current_user=type("User", (), {"id": 1})())

def test_get_attempt_details_positive():
    class DummyQuiz:
        id = "q1"
        file_id = "f1"
        questions = [1, 2]

    class DummyAttempt:
        def __init__(self):
            self.score = 4
            self.submitted_at = datetime.utcnow()

    class DummyDB:
        def query(self, model):
            if model.__name__ == "Quiz":
                class DummyQuizQuery:
                    def filter(self, *args):
                        class DummyResult:
                            def first(self): return DummyQuiz()
                            def order_by(self, *args):
                                return type("Ordered", (), {
                                    "all": lambda self: [DummyQuiz()]
                                })()
                        return DummyResult()
                return DummyQuizQuery()
            elif model.__name__ == "UploadedFile":
                class DummyFileQuery:
                    def filter(self, *args):
                        class DummyResult:
                            def first(self): return type("File", (), {"original_name": "doc.txt", "id": "f1"})()
                        return DummyResult()
                return DummyFileQuery()
            elif model.__name__ == "QuizAttempt":
                class DummyAttemptQuery:
                    def filter(self, *args):
                        class DummyResult:
                            def order_by(self, *args):
                                class DummySet:
                                    def all(self): return [DummyAttempt()]
                                return DummySet()
                        return DummyResult()
                return DummyAttemptQuery()
            return None

    result = user_dashboard.get_attempt_details("q1", db=DummyDB(), current_user=type("User", (), {"id": 1})())
    assert isinstance(result, list)
    assert result[0]["score"] == 4

# -----------------------
# weekly_average_scores
# -----------------------
def test_weekly_average_scores_empty():
    class DummyDB:
        def query(self, *args):
            return type("Q", (), {
                "filter": lambda self, *a: self,
                "group_by": lambda self, *a: self,
                "order_by": lambda self, *a: type("Q", (), {"all": lambda self: []})()
            })()
    user = type("User", (), {"id": "1"})()
    result = user_dashboard.weekly_average_scores(db=DummyDB(), current_user=user)
    assert result == []

def test_weekly_average_scores_positive():
    class DummyRow:
        def __init__(self, week_start, avg_score):
            self.week_start = week_start
            self.avg_score = avg_score

    class DummyDB:
        def query(self, *args):
            return type("Q", (), {
                "filter": lambda self, *a: self,
                "group_by": lambda self, *a: self,
                "order_by": lambda self, *a: type("Q", (), {
                    "all": lambda self: [
                        DummyRow(datetime(2024, 1, 1), 3.5),
                        DummyRow(datetime(2024, 1, 8), 4.2)
                    ]
                })()
            })()
    result = user_dashboard.weekly_average_scores(db=DummyDB(), current_user=type("User", (), {"id": 1})())
    assert result[0]["avg_score"] == 3.5
    assert result[1]["avg_score"] == 4.2
