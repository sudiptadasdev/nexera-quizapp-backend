from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.session import get_db
from db.models import Quiz, UploadedFile, Question, User, QuizAttempt

from services.gemini_service import expand_quiz_with_new_items as generate_additional_questions
import json
import fitz  # PyMuPDF
from docx import Document
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel
from auth.schemas import ProfileUpdate



router = APIRouter()

#class ProfileUpdate(BaseModel):
 #   full_name: str


@router.get("/me")
def get_current_user_details(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@router.get("/dashboard")
def fetch_dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns metadata for all quizzes created from user's uploaded files."""
    associated_quizzes = (
        db.query(Quiz)
        .join(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id)
        .all()
    )

    return [
        {
            "quiz_id": q.id,
            "file_name": q.file.original_name,
            "created_at": q.created_at,
            "question_count": len(q.questions),
        }
        for q in associated_quizzes
    ]


@router.get("/dashboard/files")
def list_user_files(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(UploadedFile).filter(UploadedFile.user_id == current_user.id).all()


@router.get("/dashboard/files/{file_id}/sections")
def get_quiz_sections_by_file(file_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns quizzes and their questions derived from a specific uploaded file."""
    file_quizzes = db.query(Quiz).filter(Quiz.file_id == file_id).all()
    section_data = []
    for index, quiz in enumerate(file_quizzes):
        questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()
        section_data.append({
            "section_number": index + 1,
            "quiz_id": quiz.id,
            "questions": questions
        })
    return section_data


@router.post("/dashboard/files/{file_id}/generate")
async def create_additional_quiz(file_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generates new quiz section using Gemini and stores in DB."""
    file_record = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.user_id == current_user.id
    ).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Extract file content
    try:
        path = f"uploads/{file_record.filename}"
        if file_record.file_type == 'pdf':
            doc = fitz.open(path)
            raw_text = "\n".join([p.get_text() for p in doc])
        elif file_record.file_type == 'docx':
            doc = Document(path)
            raw_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                raw_text = file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading {file_record.file_type} file: {e}")

    existing_texts = [
        q.text for q in db.query(Question.text)
        .join(Quiz).filter(Quiz.file_id == file_id)
        .all()
    ]

    # Generate questions from Gemini
    response = await generate_additional_questions(raw_text, existing_texts, db)

    try:
        if isinstance(response, str):
            response = response.strip("```json").strip("```").strip()
            questions = json.loads(response)
        elif isinstance(response, list):
            questions = response
        else:
            raise ValueError("Unsupported Gemini response format")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {e}")

    # Save new quiz section
    new_quiz = Quiz(file_id=file_id)
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    for item in questions:
        db.add(Question(
            quiz_id=new_quiz.id,
            text=item["question"],
            options=item.get("options"),
            correct_answer=item["answer"],
            explanation=item.get("explanation", ""),
            question_type=item.get("question_type", "mcq")
        ))
    db.commit()

    return {
        "quiz_id": new_quiz.id,
        "section_number": len(existing_texts) // 5 + 1,
        "questions": questions
    }


@router.get("/profile")
def view_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "about": current_user.about
    }


@router.put("/profile")
def edit_profile(update: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Only update full_name if it's provided and not empty
    if update.full_name is not None and update.full_name.strip() != "":
        current_user.full_name = update.full_name.strip()

    # Always update 'about' as it's required
    current_user.about = update.about.strip()

    db.commit()
    db.refresh(current_user)
    return {
        "message": "Profile updated",
        "full_name": current_user.full_name,
        "about": current_user.about
    }


@router.get("/dashboard/history")
def get_user_quiz_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the most recent quiz attempts per quiz by the user."""
    attempts = (
        db.query(QuizAttempt)
        .join(Quiz)
        .join(UploadedFile)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.submitted_at.desc())
        .all()
    )

    latest_attempts = {}
    for a in attempts:
        if a.quiz_id not in latest_attempts:
            latest_attempts[a.quiz_id] = a

    history = []
    for attempt in latest_attempts.values():
        quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
        file = db.query(UploadedFile).filter(UploadedFile.id == quiz.file_id).first()

        if not quiz or not file:
            continue

        quizzes_for_file = db.query(Quiz).filter(Quiz.file_id == file.id).order_by(Quiz.created_at.asc()).all()
        section = next((i + 1 for i, q in enumerate(quizzes_for_file) if q.id == quiz.id), None)

        history.append({
            "quiz_id": quiz.id,
            "label": f"{file.original_name} - Section {section}",
            "score": attempt.score,
            "submitted_at": attempt.submitted_at,
            "num_questions": len(quiz.questions)
        })

    return history


@router.get("/dashboard/quiz/{quiz_id}/attempts")
def get_attempt_details(quiz_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns all attempts made by user for a given quiz."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    file = db.query(UploadedFile).filter(UploadedFile.id == quiz.file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.quiz_id == quiz_id
    ).order_by(QuizAttempt.submitted_at.desc()).all()

    quizzes_for_file = db.query(Quiz).filter(Quiz.file_id == file.id).order_by(Quiz.created_at.asc()).all()
    section = next((i + 1 for i, q in enumerate(quizzes_for_file) if q.id == quiz.id), None)

    return [
        {
            "label": f"{file.original_name} - Section {section}",
            "score": a.score,
            "submitted_at": a.submitted_at,
            "num_questions": len(quiz.questions)
        }
        for a in attempts
    ]


@router.get("/dashboard/weekly-scores")
def weekly_average_scores(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns weekly average scores for the last 3 months (approx. 13 weeks)."""
    start = datetime.utcnow().date() - timedelta(days=90)

    weekly_data = db.query(
        func.date_trunc('week', QuizAttempt.submitted_at).label('week_start'),
        func.avg(QuizAttempt.score).label('avg_score')
    ).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.submitted_at >= start
    ).group_by(
        func.date_trunc('week', QuizAttempt.submitted_at)
    ).order_by(
        func.date_trunc('week', QuizAttempt.submitted_at)
    ).all()

    return [
        {
            "week_start": row.week_start.date().isoformat(),
            "avg_score": round(float(row.avg_score), 2)
        }
        for row in weekly_data
    ]
