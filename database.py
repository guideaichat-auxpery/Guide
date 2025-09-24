import os
import bcrypt
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional
import streamlit as st

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Optional database configuration - app can run without database
engine = None
SessionLocal = None
database_available = False
database_status_message = ""

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        database_available = True
        database_status_message = "Database connected successfully."
    except Exception as e:
        # Log to console for debugging, don't expose details to users
        print(f"Database connection failed: {str(e)}")
        database_status_message = "Database connection failed. Running in limited mode."
else:
    database_status_message = "Database not configured. Running in limited mode without persistent storage."
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    user_type = Column(String, nullable=False)  # 'educator'
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship to students they manage
    students = relationship("Student", back_populates="educator")

class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    age_group = Column(String, nullable=True)  # 'early_years', 'primary', 'adolescent'
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship to their educator
    educator = relationship("User", back_populates="students")

class LessonPlan(Base):
    __tablename__ = "lesson_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    australian_curriculum_codes = Column(Text, nullable=True)  # JSON string of AC codes
    montessori_principles = Column(Text, nullable=True)  # JSON string of principles
    age_group = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def create_tables():
    """Create all database tables with error handling"""
    if not engine:
        return False
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception as e:
        # Log to console for debugging, don't expose details to users
        print(f"Database initialization error: {str(e)}")
        return False

def get_db():
    """Get database session"""
    if not SessionLocal:
        return None
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the caller handle it

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hash: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))

def create_user(db, email: str, password: str, full_name: str, user_type: str) -> User:
    """Create a new user (educator)"""
    password_hash = hash_password(password)
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        user_type=user_type
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_student(db, username: str, password: str, full_name: str, educator_id: int, age_group: Optional[str] = None) -> Student:
    """Create a new student account"""
    password_hash = hash_password(password)
    student = Student(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        educator_id=educator_id,
        age_group=age_group
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def authenticate_user(db, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

def authenticate_student(db, username: str, password: str) -> Optional[Student]:
    """Authenticate a student by username and password"""
    student = db.query(Student).filter(Student.username == username, Student.is_active == True).first()
    if student and verify_password(password, student.password_hash):
        return student
    return None

def get_user_by_email(db, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_student_by_username(db, username: str) -> Optional[Student]:
    """Get student by username"""
    return db.query(Student).filter(Student.username == username).first()