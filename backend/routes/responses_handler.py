from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from services.gemini_service import score_user_answers as score_user_responses
from db.session import get_db
from sqlalchemy.orm import Session
from auth.utils import get_current_user
from db.models import User, QuizAttempt, UserAnswer, Question
import uuid

router = APIRouter()

@router.post("/")
async def evaluate_user_submission(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = await request.json()
    quiz_data = data.get("quizData")
    user_answers = data.get("userAnswers")

    if not isinstance(user_answers, (list, dict)):
        raise HTTPException(status_code=422, detail="userAnswers must be a list or dict.")

    try:
        evaluation = score_user_responses(quiz_data, user_answers)
    except Exception as e:
        print("Error while evaluating answers with Gemini:", e)
        return JSONResponse(status_code=500, content={"error": "Failed to evaluate answers."})

    new_attempt = QuizAttempt(user_id=current_user.id, quiz_id=quiz_data["quiz_id"], score=0)
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)

    score = 0
    for res in evaluation["results"]:
        is_correct = True if res.get("is_correct") is True else False if res.get("is_correct") is False else None
        if is_correct:
            score += 1
        db.add(UserAnswer(
            user_id=current_user.id,
            attempt_id=new_attempt.id,
            question_id=uuid.UUID(str(res["id"])),
            answer=res["user_answer"],
            is_correct=is_correct
        ))

    new_attempt.score = score
    db.commit()

    return JSONResponse(content=evaluation)

@router.get("/attempts")
def retrieve_all_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id
    ).order_by(QuizAttempt.submitted_at.desc()).all()

    response_data = []
    for attempt in attempts:
        for ans in attempt.answers:
            question = db.query(Question).get(ans.question_id)
            response_data.append({
                "question": question.text,
                "user_answer": ans.answer,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "is_correct": ans.is_correct
            })
    return response_data
