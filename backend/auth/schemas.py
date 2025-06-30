from sqlalchemy.orm import declarative_base
import uuid
from pydantic import BaseModel, EmailStr

Base = declarative_base()

# ============================
# Pydantic Schemas for Users
# ============================

# Schema for registering a user
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

# Schema for login form
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema for user info returned from API
class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    about: str | None = None

    class Config:
        orm_mode = True  # enables ORM to Pydantic conversion

class ProfileUpdate(BaseModel):
    full_name: str
    about: str | None = None 
