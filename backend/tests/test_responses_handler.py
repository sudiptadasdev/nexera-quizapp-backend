import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from routes.responses_handler import router
from uuid import uuid4

client = TestClient(router)

# -------------------------------
# Tests for evaluate_user_submission
# -------------------------------

@pytest.mark.asyncio
async def test_evaluate_user_submission_invalid_answers(monkeypatch):
    class DummyRequest:
        async def json(self):
            return {
                "quizData": {"quiz_id": str(uuid4()), "questions": [{"id": "1"}]},
                "userAnswers": "not_a_list"
            }

    with pytest.raises(HTTPException) as exc_info:
        await router.routes[0].endpoint(
            request=DummyRequest(),
            db=None,
            current_user=type("User", (), {"id": 1})()
        )
    assert exc_info.value.status_code == 422
    assert "userAnswers must be a list or dict" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_evaluate_user_submission_success(monkeypatch):
    qid1 = str(uuid4())
    qid2 = str(uuid4())
    dummy_eval_result = {
        "results": [
            {"id": qid1, "is_correct": True, "user_answer": "A"},
            {"id": qid2, "is_correct": False, "user_answer": "B"}
        ]
    }

    class DummyRequest:
        async def json(self):
            return {
                "quizData": {
                    "quiz_id": str(uuid4()),
                    "questions": [{"id": qid1}, {"id": qid2}]
                },
                "userAnswers": [{"id": qid1, "answer": "A"}, {"id": qid2, "answer": "B"}]
            }

    class DummyDB:
        def __init__(self):
            self.data = []

        def add(self, item): self.data.append(item)
        def commit(self): pass
        def refresh(self, item): item.submitted_at = "now"

    monkeypatch.setattr("routes.responses_handler.score_user_responses", lambda quiz, answers: dummy_eval_result)

    response = await router.routes[0].endpoint(
        request=DummyRequest(),
        db=DummyDB(),
        current_user=type("User", (), {"id": 1})()
    )

    assert response["score"] == 1
    assert response["quiz_id"] is not None
    assert len(response["results"]) == 2

# -------------------------------
# Tests for retrieve_all_attempts
# -------------------------------

def test_retrieve_all_attempts(monkeypatch):
    class DummyQuestion:
        def __init__(self, id, text, correct_answer, explanation):
            self.id = id
            self.text = text
            self.correct_answer = correct_answer
            self.explanation = explanation

    class DummyAnswer:
        def __init__(self, question_id):
            self.question_id = question_id
            self.answer = "A"
            self.is_correct = True

    class DummyAttempt:
        def __init__(self, answers):
            self.answers = answers
            self.submitted_at = "now"

    qid = uuid4()
    dummy_question = DummyQuestion(id=qid, text="What is AI?", correct_answer="Artificial Intelligence", explanation="It's AI.")

    monkeypatch.setattr("routes.responses_handler.get_db", lambda: None)
    monkeypatch.setattr("routes.responses_handler.get_current_user", lambda: type("User", (), {"id": 1})())

    class DummyDB:
        def query(self, model):
            if model.__name__ == "QuizAttempt":
                return type("Query", (), {
                    "filter": lambda *a, **kw: type("QuerySet", (), {
                        "order_by": lambda *args, **kwargs: type("All", (), {
                            "all": lambda self: [DummyAttempt([DummyAnswer(qid)])]
                        })()
                    })()
                })()
            elif model.__name__ == "Question":
                return type("Query", (), {"get": lambda self, id: dummy_question})()
            return None

    result = router.routes[1].endpoint(DummyDB(), type("User", (), {"id": 1})())
    assert isinstance(result, list)
    assert result[0]["question"] == "What is AI?"
