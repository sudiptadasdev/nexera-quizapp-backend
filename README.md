# 🧠 Backend – NexEra Quiz App

This is the **FastAPI backend** of the NexEra AI-powered quiz platform. It handles user registration, file uploads, quiz generation using Gemini AI, quiz evaluation, history tracking, and more.

---

### Related Repositories

> 🖥️ The frontend for this project is here: [nexera-quizapp-frontend](https://github.com/sudiptadasdev/nexera-quizapp-frontend)

---

## 🚀 Tech Stack

- **FastAPI** with SQLAlchemy
- **PostgreSQL** (via SQLAlchemy ORM)
- **JWT Authentication**
- **Google Gemini API** (AI quiz generation)
- **Uvicorn**, **Alembic**, **PyMuPDF**, **docx**

---

## 📁 Folder Structure

```
backend/
├── auth/               # User authentication & JWT
├── db/                 # DB session & models
├── routes/             # API routes (upload, quiz, user, responses)
├── services/           # Gemini AI integration
├── tests/              # Pytest test cases
├── uploads/            # Uploaded DOCX, PDF, TXT files
├── main.py             # App entry point
└── requirements.txt    # Dependencies
```

---

## 🔐 Authentication

- Register/Login endpoints return JWT tokens.
- Tokens must be included in headers:  
  `Authorization: Bearer <your_token>`

---

## ⚙️ Setup Instructions

### 1. Clone and enter the repo:

```bash
git clone https://github.com/sudiptadasdev/nexera-quizapp-backend.git
cd nexera-quizapp-backend/backend
```

### 2. Create virtual environment:

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate       # macOS/Linux
```

### 3. Install dependencies:

```bash
pip install -r requirements.txt
```

### 4. Pre-Setup: PostgreSQL, Gemini API Key & SMTP App Password

Before proceeding with the setup, ensure you have the following ready:

PostgreSQL Setup
- **Install PostgreSQL** from [https://www.postgresql.org/download/](https://www.postgresql.org/download/)
- Create a new database named `quizdb` (or any name of your choice).
- Set a username and password. Use these in the `DATABASE_URL` environment variable.

Gemini API Key
- Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Sign in with your Google account and click “Create API Key”.
- Copy the key and use it in the `GEMINI_API_KEY` environment variable.

Gmail SMTP App Password
- Go to [https://myaccount.google.com/security](https://myaccount.google.com/security)
- Under **"Signing in to Google"**, enable **2-Step Verification**.
- Then go to [App Passwords](https://myaccount.google.com/apppasswords)
- Generate an app password for "Mail" → "Other (Custom name)".
- Use the same email and generated app password in `EMAIL_USERNAME` & `EMAIL_PASSWORD` environment variable.



### 5. Set environment variables (`.env` file or shell):

```
DATABASE_URL=postgresql://user:password@localhost/quizdb
GEMINI_API_KEY=your_google_gemini_key

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```



### 6. Create and Run Alembic(Make sure to update your .env file first):
```bash
alembic init alembic
```

```bash
alembic revision --autogenerate -m "initial migration"
```


```bash
alembic upgrade head
```

### 7. Start the server:

```bash
uvicorn main:app --reload
```

Visit docs at: http://localhost:8000/docs

---

## 🧪 Testing

This project uses `pytest` for writing and running test cases.

- All test files are located inside /backend/tests/
- Test files are named like test_<feature>.py
  
Before running tests, make sure you have created a virtual environment and installed dependencies

one way to run in case of issue in finding  libraries while runnig pytest:

navigate to nexera-quizapp-backend\backend folder then run the below commands

```bash
 ..\venv\Scripts\python.exe -m pytest
 ```

To run specific tests:
```bash
 ..\venv\Scripts\python.exe -m pytest tests/file_name.py
 ```

To run coverage :
```bash
.\venv\Scripts\python.exe -m pytest --cov=. tests/
```



Run all tests:
```bash
pytest
```

Run a specific test file:
```bash
pytest tests/file_name.py
```
---


## 📬 Contact

For queries, reach out via email:  [Mail](mailto:nexera.quizmaster@gmail.com)

Built by -  
Sachin Malik  and Sudipta Das
