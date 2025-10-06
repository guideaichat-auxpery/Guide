import os
import bcrypt
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Table
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

class EducatorStudentAccess(Base):
    __tablename__ = "educator_student_access"
    
    educator_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), primary_key=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Relationships
    educator = relationship("User", foreign_keys=[educator_id])
    student = relationship("Student", foreign_keys=[student_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    user_type = Column(String, nullable=False)  # 'educator'
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship to students they manage (primary educator)
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
    
    # Relationship to their primary educator
    educator = relationship("User", back_populates="students")
    
    # Relationship to their activities
    activities = relationship("StudentActivity", back_populates="student", cascade="all, delete-orphan")

class StudentActivity(Base):
    __tablename__ = "student_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    activity_type = Column(String, nullable=False)  # 'prompt', 'response', 'edit', 'retry', 'refinement'
    prompt_text = Column(Text, nullable=True)  # The student's prompt
    response_text = Column(Text, nullable=True)  # AI's response
    session_id = Column(String, nullable=True)  # To group related interactions
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to student
    student = relationship("Student", back_populates="activities")

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

class GreatStory(Base):
    __tablename__ = "great_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    theme = Column(String, nullable=False)  # The prompted theme/topic
    content = Column(Text, nullable=False)  # The story content
    age_group = Column(String, nullable=True)  # Target age group
    keywords = Column(Text, nullable=True)  # JSON string of keywords/tags
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PlanningNote(Base):
    __tablename__ = "planning_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)  # Rich text content with chapters/sections
    chapters = Column(Text, nullable=True)  # JSON string for chapter organization
    images = Column(Text, nullable=True)  # JSON string of image URLs/data
    materials = Column(Text, nullable=True)  # Text for materials list
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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

def log_student_activity(db, student_id: int, activity_type: str, prompt_text: Optional[str] = None, 
                        response_text: Optional[str] = None, session_id: Optional[str] = None, extra_data: Optional[str] = None):
    """Log a student's activity"""
    activity = StudentActivity(
        student_id=student_id,
        activity_type=activity_type,
        prompt_text=prompt_text,
        response_text=response_text,
        session_id=session_id,
        extra_data=extra_data
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity

def get_student_activities(db, student_id: int, limit: int = 100):
    """Get student activities ordered by most recent"""
    return db.query(StudentActivity).filter(
        StudentActivity.student_id == student_id
    ).order_by(StudentActivity.created_at.desc()).limit(limit).all()

def grant_educator_access(db, educator_id: int, student_id: int, granted_by: int):
    """Grant an educator access to view a student's activities"""
    # Verify that granted_by is the primary educator of the student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.educator_id != granted_by:
        return False
    
    # Check if educator exists and is active
    educator = db.query(User).filter(
        User.id == educator_id, 
        User.user_type == "educator", 
        User.is_active == True
    ).first()
    if not educator:
        return False
    
    # Check if access already exists
    existing_access = db.query(EducatorStudentAccess).filter(
        EducatorStudentAccess.educator_id == educator_id,
        EducatorStudentAccess.student_id == student_id
    ).first()
    
    if existing_access:
        return True  # Already granted
    
    # Create new access record
    access = EducatorStudentAccess(
        educator_id=educator_id,
        student_id=student_id,
        granted_by=granted_by
    )
    db.add(access)
    db.commit()
    return True

def revoke_educator_access(db, educator_id: int, student_id: int, revoked_by: int = None):
    """Revoke an educator's access to view a student's activities"""
    # Verify that revoked_by is the primary educator of the student (if provided)
    if revoked_by:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student or student.educator_id != revoked_by:
            return False
    
    # Remove access record
    access = db.query(EducatorStudentAccess).filter(
        EducatorStudentAccess.educator_id == educator_id,
        EducatorStudentAccess.student_id == student_id
    ).first()
    
    if access:
        db.delete(access)
        db.commit()
        return True
    return False

def get_educator_accessible_students(db, educator_id: int):
    """Get all students that an educator has access to view"""
    # Get students where educator is primary educator
    owned_students = db.query(Student).filter(Student.educator_id == educator_id).all()
    
    # Get students where educator has granted access
    accessible_student_ids = db.query(EducatorStudentAccess.student_id).filter(
        EducatorStudentAccess.educator_id == educator_id
    ).all()
    
    accessible_students = []
    if accessible_student_ids:
        student_ids = [row[0] for row in accessible_student_ids]
        accessible_students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    
    # Combine and deduplicate
    all_students = list(owned_students)
    for student in accessible_students:
        if student not in all_students:
            all_students.append(student)
    
    return all_students

def get_student_access_educators(db, student_id: int):
    """Get all educators who have access to view a student's activities (excluding primary)"""
    return db.query(User).join(
        EducatorStudentAccess, 
        User.id == EducatorStudentAccess.educator_id
    ).filter(
        EducatorStudentAccess.student_id == student_id,
        User.is_active == True
    ).all()

def get_student_with_activities(db, student_id: int):
    """Get student with their recent activities"""
    return db.query(Student).filter(Student.id == student_id).first()

# Great Story functions
def create_great_story(db, educator_id: int, title: str, theme: str, content: str, age_group: str = None, keywords: str = None):
    """Create a new Great Story"""
    story = GreatStory(
        educator_id=educator_id,
        title=title,
        theme=theme,
        content=content,
        age_group=age_group,
        keywords=keywords
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story

def update_great_story(db, story_id: int, title: str = None, content: str = None, age_group: str = None, keywords: str = None):
    """Update an existing Great Story"""
    story = db.query(GreatStory).filter(GreatStory.id == story_id).first()
    if story:
        if title:
            story.title = title
        if content:
            story.content = content
        if age_group:
            story.age_group = age_group
        if keywords:
            story.keywords = keywords
        story.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(story)
    return story

def get_educator_great_stories(db, educator_id: int):
    """Get all Great Stories created by an educator"""
    return db.query(GreatStory).filter(GreatStory.educator_id == educator_id).order_by(GreatStory.updated_at.desc()).all()

def get_great_story(db, story_id: int):
    """Get a specific Great Story by ID"""
    return db.query(GreatStory).filter(GreatStory.id == story_id).first()

def delete_great_story(db, story_id: int):
    """Delete a Great Story"""
    story = db.query(GreatStory).filter(GreatStory.id == story_id).first()
    if story:
        db.delete(story)
        db.commit()
        return True
    return False

# Planning Note functions
def create_planning_note(db, educator_id: int, title: str, content: str = "", chapters: str = None, images: str = None, materials: str = None):
    """Create a new Planning Note"""
    note = PlanningNote(
        educator_id=educator_id,
        title=title,
        content=content,
        chapters=chapters,
        images=images,
        materials=materials
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def update_planning_note(db, note_id: int, title: str = None, content: str = None, chapters: str = None, images: str = None, materials: str = None):
    """Update an existing Planning Note"""
    note = db.query(PlanningNote).filter(PlanningNote.id == note_id).first()
    if note:
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if chapters is not None:
            note.chapters = chapters
        if images is not None:
            note.images = images
        if materials is not None:
            note.materials = materials
        note.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(note)
    return note

def get_educator_planning_notes(db, educator_id: int):
    """Get all Planning Notes created by an educator"""
    return db.query(PlanningNote).filter(PlanningNote.educator_id == educator_id).order_by(PlanningNote.updated_at.desc()).all()

def get_planning_note(db, note_id: int):
    """Get a specific Planning Note by ID"""
    return db.query(PlanningNote).filter(PlanningNote.id == note_id).first()

def delete_planning_note(db, note_id: int):
    """Delete a Planning Note"""
    note = db.query(PlanningNote).filter(PlanningNote.id == note_id).first()
    if note:
        db.delete(note)
        db.commit()
        return True
    return False