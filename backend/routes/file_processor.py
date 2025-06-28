from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os, uuid
from db.session import get_db
from db.models import UploadedFile, Quiz, Question
from services.gemini_service import build_quiz_from_content as generate_quiz_from_text
from auth.utils import get_current_user
from db.models import User
import docx
from docx.opc.exceptions import PackageNotFoundError
from fitz import open as open_pdf, FileDataError

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text_from_uploaded_file(path: str, extension: str) -> str:
    """
    Extracts plain text from uploaded file depending on file type.
    Supported types: PDF, DOCX, TXT.
    """
    extension = extension.lower()
    try:
        if extension == ".pdf":
            doc = open_pdf(path)
            text = "\n".join([page.get_text() for page in doc])
        elif extension == ".docx":
            doc = docx.Document(path)
            text = "\n".join([para.text for para in doc.paragraphs])
        else:  # Assume .txt
            with open(path, "r", encoding="utf-8", errors="strict") as f:
                text = f.read()

        if not text.strip():
            raise HTTPException(status_code=400, detail="Uploaded file has no readable content.")

        return text

    except PackageNotFoundError:
        raise HTTPException(status_code=400, detail="DOCX file is invalid or corrupted.")
    except FileDataError:
        raise HTTPException(status_code=400, detail="PDF file is invalid or corrupted.")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="TXT file is not valid UTF-8 text.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error during text extraction: {str(e)}")

@router.post("/", name="upload_file_and_generate_quiz")
async def handle_file_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a file, extracts text, generates quiz using Gemini, and stores result in DB.
    """
    # Validate file extension
    extension = os.path.splitext(file.filename)[1]
    allowed_exts = {".pdf", ".docx", ".txt"}

    if extension.lower() not in allowed_exts:
        return JSONResponse(status_code=415, content={"error": "Unsupported file type."})

    # Save the uploaded file to disk
    unique_name = f"{uuid.uuid4().hex}{extension}"
    saved_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(saved_path, "wb") as f:
        f.write(await file.read())

    # Create DB record for file
    file_record = UploadedFile(
        user_id=current_user.id,
        filename=unique_name,
        original_name=file.filename,
        file_type=extension.lower().lstrip(".")
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    # Extract file content
    extracted_text = extract_text_from_uploaded_file(saved_path, extension)

    # Use Gemini to generate quiz questions
    quiz_items = await generate_quiz_from_text(extracted_text, db)

    # Create a new quiz entry
    quiz_entry = Quiz(file_id=file_record.id)
    db.add(quiz_entry)
    db.commit()
    db.refresh(quiz_entry)

    # Store all questions
    for item in quiz_items:
        db_question = Question(
            id=item["id"],
            quiz_id=quiz_entry.id,
            text=item["question"],
            options=item.get("options"),  # Will be None for text-based Qs
            correct_answer=item["answer"],
            explanation=item.get("explanation", "No explanation provided."),
            question_type=item.get("question_type", "mcq")
        )
        db.add(db_question)

    db.commit()

    return {
        "quiz_id": quiz_entry.id,
        "questions": quiz_items,
        "file_id": file_record.id
    }
