from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from db.models import Base
from db.session import engine, get_db
from sqlalchemy.orm import Session

# Updated routes based on your renamed files
from routes.responses_handler import router as answer_router
from routes.file_processor import router as upload_db_router
from routes.user_dashboard import router as me_router
from routes.quizzes_logic import router as quizzes_router
from auth.routes import router, auth_router

# Load environment variables
load_dotenv()

# Create tables (replace with Alembic in production)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for local frontend or deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Change this if deploying
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups
app.include_router(auth_router)
app.include_router(router)
app.include_router(answer_router, prefix="/api/answers", tags=["Answers"])
app.include_router(upload_db_router, prefix="/upload-db", tags=["Upload & Store"])
app.include_router(me_router, prefix="/user", tags=["Dashboard"])
app.include_router(quizzes_router, prefix="/api/quizzes", tags=["Quizzes"])

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    return {"message": "Nexera Quiz backend is operational!"}

# Utility: Print all active routes at server start
from fastapi.routing import APIRoute

def list_routes(app):
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "name": route.name,
                "methods": route.methods
            })
    return routes

for r in list_routes(app):
    print(f"{r['methods']} -> {r['path']} (name: {r['name']})")
