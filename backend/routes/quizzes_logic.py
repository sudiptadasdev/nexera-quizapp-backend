from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from db.session import get_db
from db.models import User, Quiz
from auth.utils import get_current_user

# Router to handle quiz data retrieval
router = APIRouter()

@router.get("/{quiz_id}")
def retrieve_quiz_details(
    quiz_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch a complete quiz with questions based on the quiz_id.
    Only accessible to authenticated users.
    """
    quiz_entity = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    
    if not quiz_entity:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Prepare and return quiz metadata and question list
    return {
        "quiz_id": quiz_entity.id,
        "created_at": quiz_entity.created_at,
        "questions": [
            {
                "id": question.id,
                "text": question.text,
                "options": question.options,
                "question_type": question.question_type,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation
            }
            for question in quiz_entity.questions
        ]
    }
