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
        # Configure engine with connection pooling and SSL settings
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Test connections before using them
            pool_recycle=3600,   # Recycle connections after 1 hour
            pool_size=5,         # Limit pool size
            max_overflow=10,     # Allow overflow connections
            connect_args={
                "sslmode": "require",  # Require SSL but don't verify certificate
                "connect_timeout": 10
            }
        )
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
    institution_name = Column(Text, nullable=True)  # For institution-based sharing
    
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

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For educators
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # For students
    session_id = Column(String, nullable=False, index=True)  # Session identifier
    interface_type = Column(String, nullable=False)  # 'companion', 'student', 'planning'
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class EducatorAnalytics(Base):
    __tablename__ = "educator_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    interface_type = Column(String, nullable=False)  # 'companion', 'planning', etc.
    subject = Column(String, nullable=True)  # Subject area if applicable
    year_level = Column(String, nullable=True)  # Year level if applicable
    prompt_text = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)  # Estimated tokens
    model_used = Column(String, default="gpt-4o-mini")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class CurriculumContext(Base):
    __tablename__ = "curriculum_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False, index=True)  # Science, Mathematics, English
    year_level = Column(String, nullable=False, index=True)  # Year 1, Year 2, etc.
    curriculum_type = Column(String, default="AC_V9")  # AC_V9, Montessori, Blended
    strand = Column(String, nullable=True)
    focus_area = Column(String, nullable=True)
    descriptor = Column(Text, nullable=False)
    descriptor_code = Column(String, nullable=True)  # e.g., AC9S3U02
    montessori_connection = Column(Text, nullable=True)
    elaboration = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrendingKeyword(Base):
    __tablename__ = "trending_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False, index=True)  # Geography, History, etc.
    keyword = Column(String, nullable=False, index=True)  # The curriculum keyword
    count = Column(Integer, default=1)  # Number of times detected
    session_id = Column(String, nullable=True, index=True)  # Session that detected it
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # Optional student tracking
    last_detected = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def create_tables():
    """Create all database tables with error handling"""
    if not engine:
        return False
    
    # Use Streamlit's session state to cache initialization
    try:
        import streamlit as st
        if 'db_initialized' in st.session_state and st.session_state.db_initialized:
            return True
    except:
        pass
    
    try:
        # Create a fresh connection for initialization
        with engine.connect() as conn:
            Base.metadata.create_all(bind=engine)
        
        # Cache success in session state
        try:
            import streamlit as st
            st.session_state.db_initialized = True
        except:
            pass
        
        return True
    except Exception as e:
        # Log to console for debugging, don't expose details to users
        print(f"Database initialization error: {str(e)}")
        
        # Cache failure to avoid repeated attempts
        try:
            import streamlit as st
            st.session_state.db_initialized = False
        except:
            pass
        
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

def get_all_educators(db):
    """Get all educators"""
    return db.query(User).filter(User.user_type == 'educator').all()

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
    """
    Grant an educator access to view a student's activities.
    Returns: (success: bool, error_message: str or None)
    
    Enforces institution-based sharing when enforcement is enabled.
    """
    # Verify that granted_by is the primary educator of the student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or student.educator_id != granted_by:
        return (False, "You are not the primary educator of this student")
    
    # Check if educator exists and is active
    educator = db.query(User).filter(
        User.id == educator_id, 
        User.user_type == "educator", 
        User.is_active == True
    ).first()
    if not educator:
        return (False, "Educator not found or inactive")
    
    # Check institution enforcement
    if is_institution_enforcement_on(db):
        same_institution, institution_name = check_same_institution(db, granted_by, educator_id)
        if not same_institution:
            return (False, "You can only share students with educators from your institution")
    
    # Check if access already exists
    existing_access = db.query(EducatorStudentAccess).filter(
        EducatorStudentAccess.educator_id == educator_id,
        EducatorStudentAccess.student_id == student_id
    ).first()
    
    if existing_access:
        return (True, None)  # Already granted
    
    # Create new access record
    access = EducatorStudentAccess(
        educator_id=educator_id,
        student_id=student_id,
        granted_by=granted_by
    )
    db.add(access)
    db.commit()
    return (True, None)

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
    from sqlalchemy.orm import joinedload
    
    # Get students where educator is primary educator (eagerly load educator relationship)
    owned_students = db.query(Student).options(joinedload(Student.educator)).filter(Student.educator_id == educator_id).all()
    
    # Get students where educator has granted access
    accessible_student_ids = db.query(EducatorStudentAccess.student_id).filter(
        EducatorStudentAccess.educator_id == educator_id
    ).all()
    
    accessible_students = []
    if accessible_student_ids:
        student_ids = [row[0] for row in accessible_student_ids]
        # Eagerly load educator relationship for shared students
        accessible_students = db.query(Student).options(joinedload(Student.educator)).filter(Student.id.in_(student_ids)).all()
    
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

def delete_student(db, student_id: int):
    """
    Permanently delete a student account and all associated data.
    This will cascade delete all student activities, conversations, and access records.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        # Delete educator-student access records for this specific student
        db.query(EducatorStudentAccess).filter(
            EducatorStudentAccess.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete conversation messages for this specific student
        db.query(ConversationHistory).filter(
            ConversationHistory.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete the student (activities will cascade delete automatically)
        db.delete(student)
        db.commit()
        return True
    return False

def delete_educator(db, educator_id: int):
    """
    Permanently delete an educator account and all associated data.
    Returns: (success: bool, error_message: str or None)
    """
    educator = db.query(User).filter(User.id == educator_id).first()
    if not educator:
        return (False, "Educator not found")
    
    # Safety check: prevent deletion if educator has active students
    active_students = db.query(Student).filter(
        Student.educator_id == educator_id,
        Student.is_active == True
    ).count()
    
    if active_students > 0:
        return (False, f"Cannot delete account: You have {active_students} active student(s). Please delete or transfer your students first.")
    
    try:
        # Delete educator-student access records
        db.query(EducatorStudentAccess).filter(
            EducatorStudentAccess.educator_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete lesson plans
        db.query(LessonPlan).filter(
            LessonPlan.creator_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete great stories
        db.query(GreatStory).filter(
            GreatStory.educator_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete planning notes
        db.query(PlanningNote).filter(
            PlanningNote.educator_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete conversation history
        db.query(ConversationHistory).filter(
            ConversationHistory.user_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete educator analytics
        db.query(EducatorAnalytics).filter(
            EducatorAnalytics.user_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete consent records where educator is the user
        db.query(ConsentRecord).filter(
            ConsentRecord.user_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete consent records granted by this educator (for students)
        db.query(ConsentRecord).filter(
            ConsentRecord.granted_by_id == educator_id
        ).delete(synchronize_session=False)
        
        # Delete parental consent records created by this educator
        db.query(ParentalConsentRecord).filter(
            ParentalConsentRecord.educator_id == educator_id
        ).delete(synchronize_session=False)
        
        # Finally delete the educator user record
        db.delete(educator)
        db.commit()
        return (True, None)
        
    except Exception as e:
        db.rollback()
        return (False, f"Error during deletion: {str(e)}")

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

# Conversation History functions
def save_conversation_message(db, session_id: str, interface_type: str, role: str, content: str, 
                              user_id: int = None, student_id: int = None):
    """Save a conversation message to history"""
    message = ConversationHistory(
        user_id=user_id,
        student_id=student_id,
        session_id=session_id,
        interface_type=interface_type,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_conversation_history(db, session_id: str, interface_type: str, limit: int = 20):
    """Get conversation history for a session"""
    return db.query(ConversationHistory).filter(
        ConversationHistory.session_id == session_id,
        ConversationHistory.interface_type == interface_type
    ).order_by(ConversationHistory.created_at.desc()).limit(limit).all()

def get_user_conversation_history(db, user_id: int = None, student_id: int = None, 
                                  interface_type: str = None, limit: int = 50):
    """Get conversation history for a user or student across sessions"""
    query = db.query(ConversationHistory)
    
    if user_id:
        query = query.filter(ConversationHistory.user_id == user_id)
    if student_id:
        query = query.filter(ConversationHistory.student_id == student_id)
    if interface_type:
        query = query.filter(ConversationHistory.interface_type == interface_type)
    
    return query.order_by(ConversationHistory.created_at.desc()).limit(limit).all()

def load_conversation_to_session(db, session_id: str, interface_type: str):
    """Load conversation history and format for session state"""
    messages = get_conversation_history(db, session_id, interface_type, limit=20)
    # Reverse to get chronological order
    messages.reverse()
    return [{"role": msg.role, "content": msg.content} for msg in messages]

def clear_conversation_history(db, session_id: str, interface_type: str):
    """Clear conversation history for a session"""
    db.query(ConversationHistory).filter(
        ConversationHistory.session_id == session_id,
        ConversationHistory.interface_type == interface_type
    ).delete()
    db.commit()
    return True

# Educator Analytics functions
def log_educator_prompt(db, user_id: int, interface_type: str, prompt_text: str,
                       subject: str = None, year_level: str = None, tokens_used: int = None):
    """Log educator prompt for analytics"""
    analytics = EducatorAnalytics(
        user_id=user_id,
        interface_type=interface_type,
        subject=subject,
        year_level=year_level,
        prompt_text=prompt_text,
        tokens_used=tokens_used
    )
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    return analytics

def get_educator_analytics(db, user_id: int, days: int = 30):
    """Get educator analytics for the past N days"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    return db.query(EducatorAnalytics).filter(
        EducatorAnalytics.user_id == user_id,
        EducatorAnalytics.created_at >= cutoff_date
    ).order_by(EducatorAnalytics.created_at.desc()).all()

def get_analytics_summary(db, user_id: int, days: int = 30):
    """Get summary statistics for educator analytics"""
    from sqlalchemy import func
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    summary = db.query(
        func.count(EducatorAnalytics.id).label('total_prompts'),
        func.sum(EducatorAnalytics.tokens_used).label('total_tokens'),
        func.count(func.distinct(EducatorAnalytics.subject)).label('subjects_explored')
    ).filter(
        EducatorAnalytics.user_id == user_id,
        EducatorAnalytics.created_at >= cutoff_date
    ).first()
    
    return {
        'total_prompts': summary.total_prompts or 0,
        'total_tokens': summary.total_tokens or 0,
        'subjects_explored': summary.subjects_explored or 0
    }

# Curriculum Context functions
def create_curriculum_context(db, subject: str, year_level: str, descriptor: str,
                              strand: str = None, focus_area: str = None, descriptor_code: str = None,
                              montessori_connection: str = None, elaboration: str = None,
                              curriculum_type: str = "AC_V9"):
    """Create a new curriculum context entry"""
    context = CurriculumContext(
        subject=subject,
        year_level=year_level,
        curriculum_type=curriculum_type,
        strand=strand,
        focus_area=focus_area,
        descriptor=descriptor,
        descriptor_code=descriptor_code,
        montessori_connection=montessori_connection,
        elaboration=elaboration
    )
    db.add(context)
    db.commit()
    db.refresh(context)
    return context

def get_curriculum_context(db, subject: str, year_level: str, curriculum_type: str = "AC_V9"):
    """Get curriculum context from database"""
    return db.query(CurriculumContext).filter(
        CurriculumContext.subject == subject,
        CurriculumContext.year_level == year_level,
        CurriculumContext.curriculum_type == curriculum_type,
        CurriculumContext.is_active == True
    ).first()

def get_all_curriculum_contexts(db, subject: str = None, year_level: str = None):
    """Get all curriculum contexts, optionally filtered"""
    query = db.query(CurriculumContext).filter(CurriculumContext.is_active == True)
    
    if subject:
        query = query.filter(CurriculumContext.subject == subject)
    if year_level:
        query = query.filter(CurriculumContext.year_level == year_level)
    
    return query.order_by(CurriculumContext.subject, CurriculumContext.year_level).all()

def update_curriculum_context(db, context_id: int, **kwargs):
    """Update curriculum context"""
    context = db.query(CurriculumContext).filter(CurriculumContext.id == context_id).first()
    if context:
        for key, value in kwargs.items():
            if hasattr(context, key) and value is not None:
                setattr(context, key, value)
        context.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(context)
    return context

def seed_curriculum_data(db):
    """Seed database with initial curriculum data"""
    # Check if we already have data
    existing_count = db.query(CurriculumContext).count()
    if existing_count > 0:
        return False  # Already seeded
    
    # This will be populated from utils.py curriculum data
    return True

# ---- TRENDING KEYWORD FUNCTIONS ----

def update_trending_keyword(db, subject: str, keyword: str, session_id: str = None, student_id: int = None):
    """
    Update or create trending keyword entry.
    Increments count if keyword already exists for this subject.
    """
    try:
        # Check if keyword exists for this subject
        existing = db.query(TrendingKeyword).filter(
            TrendingKeyword.subject == subject,
            TrendingKeyword.keyword == keyword
        ).first()
        
        if existing:
            # Increment count and update last_detected
            existing.count += 1
            existing.last_detected = datetime.utcnow()
            if session_id:
                existing.session_id = session_id
            if student_id:
                existing.student_id = student_id
        else:
            # Create new trending keyword entry
            new_keyword = TrendingKeyword(
                subject=subject,
                keyword=keyword,
                count=1,
                session_id=session_id,
                student_id=student_id,
                last_detected=datetime.utcnow()
            )
            db.add(new_keyword)
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating trending keyword: {str(e)}")
        db.rollback()
        return False

def get_trending_keywords(db, limit: int = 5):
    """
    Get trending keywords grouped by subject.
    Returns dict: {subject: {keyword: count}}
    """
    try:
        # Query all trending keywords, ordered by count
        keywords = db.query(TrendingKeyword).order_by(
            TrendingKeyword.subject,
            TrendingKeyword.count.desc()
        ).all()
        
        # Group by subject
        trending_data = {}
        for kw in keywords:
            if kw.subject not in trending_data:
                trending_data[kw.subject] = {}
            
            # Only add up to limit per subject
            if len(trending_data[kw.subject]) < limit:
                trending_data[kw.subject][kw.keyword] = kw.count
        
        return trending_data
    except Exception as e:
        print(f"Error getting trending keywords: {str(e)}")
        return {}

def reset_trending_keywords(db):
    """Reset all trending keyword counts (for new sessions/days)"""
    try:
        db.query(TrendingKeyword).delete()
        db.commit()
        return True
    except Exception as e:
        print(f"Error resetting trending keywords: {str(e)}")
        db.rollback()
        return False

def get_top_keywords_by_subject(db, subject: str, limit: int = 5):
    """Get top N trending keywords for a specific subject"""
    try:
        keywords = db.query(TrendingKeyword).filter(
            TrendingKeyword.subject == subject
        ).order_by(TrendingKeyword.count.desc()).limit(limit).all()
        
        return [(kw.keyword, kw.count) for kw in keywords]
    except Exception as e:
        print(f"Error getting top keywords: {str(e)}")
        return []

# ---- DATA RETENTION POLICY FUNCTIONS (APP 11.2) ----

def cleanup_old_data(db, retention_days_conversations=730, retention_days_analytics=730, retention_days_inactive_accounts=1095):
    """
    Clean up old data according to retention policy:
    - Conversation history: 2 years (730 days)
    - Analytics: 2 years (730 days)  
    - Inactive accounts: 3 years (1095 days)
    """
    from datetime import datetime, timedelta
    
    try:
        # Calculate cutoff dates
        conversation_cutoff = datetime.utcnow() - timedelta(days=retention_days_conversations)
        analytics_cutoff = datetime.utcnow() - timedelta(days=retention_days_analytics)
        inactive_account_cutoff = datetime.utcnow() - timedelta(days=retention_days_inactive_accounts)
        
        deleted_counts = {
            "conversations": 0,
            "student_activities": 0,
            "educator_analytics": 0,
            "inactive_students": 0,
            "inactive_educators": 0
        }
        
        # Delete old conversation history
        old_conversations = db.query(ConversationHistory).filter(
            ConversationHistory.created_at < conversation_cutoff
        ).delete(synchronize_session=False)
        deleted_counts["conversations"] = old_conversations
        
        # Delete old student activities
        old_activities = db.query(StudentActivity).filter(
            StudentActivity.created_at < analytics_cutoff
        ).delete(synchronize_session=False)
        deleted_counts["student_activities"] = old_activities
        
        # Delete old educator analytics
        old_analytics = db.query(EducatorAnalytics).filter(
            EducatorAnalytics.created_at < analytics_cutoff
        ).delete(synchronize_session=False)
        deleted_counts["educator_analytics"] = old_analytics
        
        # Find and delete inactive student accounts (no activity in 3 years)
        inactive_students = db.query(Student).filter(
            Student.created_at < inactive_account_cutoff,
            ~Student.activities.any(StudentActivity.created_at >= inactive_account_cutoff)
        ).all()
        
        for student in inactive_students:
            db.delete(student)
            deleted_counts["inactive_students"] += 1
        
        # Find and delete inactive educator accounts (no activity in 3 years)
        inactive_educators = db.query(User).filter(
            User.created_at < inactive_account_cutoff,
            User.user_type == "educator"
        ).all()
        
        # Check if educator has recent activity
        for educator in inactive_educators:
            recent_analytics = db.query(EducatorAnalytics).filter(
                EducatorAnalytics.user_id == educator.id,
                EducatorAnalytics.created_at >= inactive_account_cutoff
            ).first()
            
            if not recent_analytics:
                db.delete(educator)
                deleted_counts["inactive_educators"] += 1
        
        db.commit()
        return deleted_counts
        
    except Exception as e:
        print(f"Error during data cleanup: {str(e)}")
        db.rollback()
        return None


def get_data_retention_status(db):
    """Get statistics about data retention and what could be cleaned up"""
    from datetime import datetime, timedelta
    
    try:
        conversation_cutoff = datetime.utcnow() - timedelta(days=730)
        analytics_cutoff = datetime.utcnow() - timedelta(days=730)
        inactive_account_cutoff = datetime.utcnow() - timedelta(days=1095)
        
        status = {
            "old_conversations": db.query(ConversationHistory).filter(
                ConversationHistory.created_at < conversation_cutoff
            ).count(),
            "old_student_activities": db.query(StudentActivity).filter(
                StudentActivity.created_at < analytics_cutoff
            ).count(),
            "old_educator_analytics": db.query(EducatorAnalytics).filter(
                EducatorAnalytics.created_at < analytics_cutoff
            ).count(),
            "total_conversations": db.query(ConversationHistory).count(),
            "total_activities": db.query(StudentActivity).count(),
            "total_analytics": db.query(EducatorAnalytics).count(),
            "total_students": db.query(Student).count(),
            "total_educators": db.query(User).filter(User.user_type == "educator").count()
        }
        
        return status
    except Exception as e:
        print(f"Error getting retention status: {str(e)}")
        return None


# ---- CONSENT TRACKING MODELS (APP 5/8 AUDITING) ----

class ConsentRecord(Base):
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For educators
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # For students
    consent_type = Column(String, nullable=False)  # 'data_collection', 'overseas_transfer', 'privacy_policy', 'parental_consent'
    granted = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Educator who granted for student
    policy_version = Column(String, default="1.0")  # Track policy version
    ip_address = Column(String, nullable=True)  # Optional IP for audit trail
    user_agent = Column(String, nullable=True)  # Optional browser info
    
class ParentalConsentRecord(Base):
    __tablename__ = "parental_consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who created the record
    parent_guardian_name = Column(String, nullable=True)  # Optional parent name
    parent_guardian_email = Column(String, nullable=True)  # Optional parent email
    consent_obtained = Column(Boolean, default=True)
    consent_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    consent_method = Column(String, nullable=True)  # 'written', 'email', 'verbal', etc.
    expires_at = Column(DateTime, nullable=True)  # Optional expiry
    withdrawn_at = Column(DateTime, nullable=True)  # If consent withdrawn
    notes = Column(Text, nullable=True)

# ---- CONSENT TRACKING FUNCTIONS ----

def record_consent(db, user_id=None, student_id=None, consent_type='privacy_policy', granted_by_id=None, policy_version="1.0"):
    """Record user consent for auditing purposes"""
    try:
        consent = ConsentRecord(
            user_id=user_id,
            student_id=student_id,
            consent_type=consent_type,
            granted=True,
            granted_at=datetime.utcnow(),
            granted_by_id=granted_by_id,
            policy_version=policy_version
        )
        db.add(consent)
        db.commit()
        return consent
    except Exception as e:
        print(f"Error recording consent: {str(e)}")
        db.rollback()
        return None

def record_parental_consent(db, student_id, educator_id, parent_name=None, parent_email=None, consent_method=None):
    """Record parental consent for student account"""
    try:
        consent = ParentalConsentRecord(
            student_id=student_id,
            educator_id=educator_id,
            parent_guardian_name=parent_name,
            parent_guardian_email=parent_email,
            consent_obtained=True,
            consent_date=datetime.utcnow(),
            consent_method=consent_method
        )
        db.add(consent)
        db.commit()
        return consent
    except Exception as e:
        print(f"Error recording parental consent: {str(e)}")
        db.rollback()
        return None

def get_user_consents(db, user_id=None, student_id=None):
    """Get all consent records for a user"""
    try:
        if user_id:
            return db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).all()
        elif student_id:
            return db.query(ConsentRecord).filter(ConsentRecord.student_id == student_id).all()
        return []
    except Exception as e:
        print(f"Error getting consents: {str(e)}")
        return []

def get_parental_consent(db, student_id):
    """Get parental consent record for a student"""
    try:
        return db.query(ParentalConsentRecord).filter(
            ParentalConsentRecord.student_id == student_id,
            ParentalConsentRecord.withdrawn_at.is_(None)
        ).first()
    except Exception as e:
        print(f"Error getting parental consent: {str(e)}")
        return None

def withdraw_parental_consent(db, student_id):
    """Mark parental consent as withdrawn"""
    try:
        consent = get_parental_consent(db, student_id)
        if consent:
            consent.withdrawn_at = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error withdrawing consent: {str(e)}")
        db.rollback()
        return False

# === INSTITUTION-BASED SHARING WITH GRACE PERIOD ===

def is_institution_enforcement_on(db):
    """Check if institution enforcement is currently active"""
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == 'enforce_institution'
        ).first()
        return config and config.config_value == 'true'
    except Exception as e:
        print(f"Error checking enforcement: {str(e)}")
        return False

def maybe_auto_enable_enforcement(db):
    """
    Automatically enable institution enforcement when ALL educators have set their institution.
    This implements the grace period auto-switch feature.
    """
    try:
        from sqlalchemy import or_
        
        # Count educators without institution
        educators_without_institution = db.query(User).filter(
            User.user_type == 'educator',
            User.is_active == True,
            or_(
                User.institution_name.is_(None),
                User.institution_name == ''
            )
        ).count()
        
        # If all educators have institution, auto-enable enforcement
        if educators_without_institution == 0:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'enforce_institution'
            ).first()
            
            if config and config.config_value != 'true':
                config.config_value = 'true'
                config.updated_at = datetime.utcnow()
                db.commit()
                print("🚀 All educators have set their institution. Enforcement automatically enabled!")
                return True
        
        return False
    except Exception as e:
        print(f"Error in auto-enable enforcement: {str(e)}")
        db.rollback()
        return False

def update_educator_institution(db, educator_id: int, institution_name: str):
    """
    Update an educator's institution name and check for auto-enable enforcement.
    Returns: (success: bool, auto_enabled: bool)
    """
    try:
        educator = db.query(User).filter(
            User.id == educator_id,
            User.user_type == 'educator'
        ).first()
        
        if not educator:
            return (False, False)
        
        # Update institution name
        educator.institution_name = institution_name.strip() if institution_name else None
        db.commit()
        
        # Check if this triggers auto-enable
        auto_enabled = maybe_auto_enable_enforcement(db)
        
        return (True, auto_enabled)
    except Exception as e:
        print(f"Error updating institution: {str(e)}")
        db.rollback()
        return (False, False)

def check_same_institution(db, educator_id_1: int, educator_id_2: int):
    """
    Check if two educators are from the same institution.
    Returns: (same_institution: bool, institution_name: str or None)
    """
    try:
        educators = db.query(User).filter(
            User.id.in_([educator_id_1, educator_id_2]),
            User.user_type == 'educator'
        ).all()
        
        if len(educators) != 2:
            return (False, None)
        
        inst1 = educators[0].institution_name
        inst2 = educators[1].institution_name
        
        # Both must have institution set
        if not inst1 or not inst2:
            return (False, None)
        
        # Compare case-insensitive
        same = inst1.strip().lower() == inst2.strip().lower()
        
        return (same, inst1 if same else None)
    except Exception as e:
        print(f"Error checking institution: {str(e)}")
        return (False, None)
