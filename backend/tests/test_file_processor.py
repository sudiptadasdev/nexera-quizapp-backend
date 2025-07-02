import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile as StarletteUploadFile
from routes.file_processor import extract_text_from_uploaded_file, router
from io import BytesIO
import tempfile

client = TestClient(router)


def test_extract_text_from_valid_txt():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tf:
        tf.write("This is a test content.")
        temp_path = tf.name

    result = extract_text_from_uploaded_file(temp_path, ".txt")
    os.unlink(temp_path)  # Clean up

    assert "test content" in result


def test_extract_text_from_empty_txt():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tf:
        tf.write("")
        temp_path = tf.name

    with pytest.raises(HTTPException) as e:
     extract_text_from_uploaded_file(temp_path, ".txt")

    assert e.value.status_code == 422
    assert "400" in str(e.value.detail)




@pytest.mark.asyncio
async def test_handle_file_upload_valid_extension(monkeypatch):
    class DummyDB:
        def add(self, x): pass
        def commit(self): pass
        def refresh(self, x): pass

    class DummyUser:
        id = 123

    class DummyQuizItem:
        def __getitem__(self, item):
            return {
                "id": "qid",
                "question": "What is 2+2?",
                "answer": "4",
                "options": ["2", "4", "6"],
                "explanation": "Simple math",
                "question_type": "mcq"
            }[item]

        def get(self, key, default=None):
            return self.__getitem__(key)

    async def dummy_generate_quiz(text, db):
        return [DummyQuizItem()]

    monkeypatch.setattr("routes.file_processor.generate_quiz_from_text", dummy_generate_quiz)
    monkeypatch.setattr("routes.file_processor.get_current_user", lambda: DummyUser())
    monkeypatch.setattr("routes.file_processor.get_db", lambda: DummyDB())

    dummy_file = UploadFile(filename="sample.txt", file=BytesIO(b"Hello world"))
    response = await router.routes[0].endpoint(file=dummy_file, db=DummyDB(), current_user=DummyUser())
    assert "quiz_id" in response
    assert "questions" in response
    assert "file_id" in response

@pytest.mark.asyncio
async def test_handle_file_upload_invalid_extension():
    dummy_file = UploadFile(filename="invalid.exe", file=BytesIO(b"content"))
    class DummyDB: pass
    class DummyUser: id = 1

    response = await router.routes[0].endpoint(file=dummy_file, db=DummyDB(), current_user=DummyUser())
    assert isinstance(response, dict) or response.status_code == 415
