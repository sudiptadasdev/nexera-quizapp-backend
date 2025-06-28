import os
import uuid
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from db.models import Quiz, Question

load_dotenv()

# === Generate a unique UUID not present in the table ===
def get_unique_id(session, model, column):
    while True:
        potential_id = str(uuid.uuid4())
        existing = session.execute(select(model).where(column == potential_id))
        if not existing.scalars().first():
            return potential_id

# === Safely parse JSON structure from Gemini's response ===
def parse_json_from_response(response_text: str):
    try:
        json_payload = re.search(r'\{.*\}', response_text, re.DOTALL).group(0)
        return json.loads(json_payload)
    except Exception as e:
        print("❌ Raw Gemini Response:\n", response_text)
        raise ValueError(f"Gemini returned unparsable JSON: {e}")

# === Build a full quiz (MCQ + open-ended) from text ===
async def build_quiz_from_content(raw_text: str, db: Session):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
You are an assistant helping students learn. Based on the following content, generate a quiz with 5 multiple-choice questions and 5 text-based open-ended questions.

Each MCQ must have 4 options and exactly one correct answer.
Each text-based question should include an expected answer and explanation.

Text:
{raw_text}

Return JSON in the following format:
{{
  "questions": [
    {{
      "question": "Question here",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "Explanation here",
      "question_type": "mcq"
    }},
    {{
      "question": "Explain ...",
      "answer": "Text answer here",
      "explanation": "Explanation here",
      "question_type": "text"
    }}
  ]
}}
"""

    response = model.generate_content(prompt)
    print("📤 Gemini Output:", response.text)
    parsed = parse_json_from_response(response.text)

    questions = parsed.get("questions", [])

    for q in questions:
        q["id"] = get_unique_id(db, Question, Question.id)
        q["question_type"] = q.get("question_type", "mcq")  # default to MCQ
        if q["question_type"] == "mcq":
            if "options" not in q or not isinstance(q["options"], list):
                raise ValueError("Missing valid options for MCQ.")
        else:
            q["options"] = None

    return questions

# === Evaluate user's answers against Gemini's solution ===
def score_user_answers(quiz_payload, user_inputs):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
You are an AI tutor.

Below is a quiz and a user's selected answers. For each question, return:
- the correct answer
- whether the user was right
- a brief explanation

Respond strictly in JSON format as:

{{
  "results": [
    {{
      "id": "uuid",
      "question": "...",
      "user_answer": "...",
      "correct_answer": "...",
      "is_correct": true,
      "explanation": "..."
    }}
  ]
}}

Quiz:
{quiz_payload}

User Answers:
{user_inputs}
"""

    response = model.generate_content(prompt)
    return parse_json_from_response(response.text)

# === Generate new questions (no duplicates) from existing content ===
async def expand_quiz_with_new_items(text_block, prior_questions, db: Session):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
You are a quiz-generating assistant.

Based on the text below, generate new multiple-choice and text-based questions (5 each) that are *not* duplicates of these:

{json.dumps(prior_questions)}

Text:
{text_block}

Return JSON in the format:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "...",
      "question_type": "mcq"
    }},
    {{
      "question": "...",
      "answer": "...",
      "explanation": "...",
      "question_type": "text"
    }}
  ]
}}
"""

    response = model.generate_content(prompt)
    print("📤 Gemini Response (New Questions):", response.text)
    parsed = parse_json_from_response(response.text)

    new_questions = parsed.get("questions", [])

    for q in new_questions:
        q["id"] = get_unique_id(db, Question, Question.id)
        q["question_type"] = q.get("question_type", "mcq")
        if q["question_type"] == "mcq":
            if "options" not in q or not isinstance(q["options"], list):
                raise ValueError("MCQ question missing options.")
        else:
            q["options"] = None

    return new_questions
