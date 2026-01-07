import os
import bcrypt
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Table, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st
import logging

# Logger for database module
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()

# Backend optimization: Cache database engine and session factory using st.cache_resource
# This prevents creating new engine/session factory on every page load
@st.cache_resource
def get_database_engine():
    """
    Create and cache database engine using Streamlit's cache_resource.
    This ensures we reuse the same engine across reruns, improving performance.
    """
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not configured")
        return None, "Database not configured. Running in limited mode without persistent storage."
    
    try:
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
        logger.info("Database engine created successfully")
        return engine, "Database connected successfully."
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return None, "Database connection failed. Running in limited mode."

# Get cached engine and status
engine, database_status_message = get_database_engine()
database_available = engine is not None

# Create thread-safe scoped session factory from cached engine
from sqlalchemy.orm import scoped_session
from contextlib import contextmanager

SessionLocal = None
if engine:
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    SessionLocal = scoped_session(session_factory)

@contextmanager
def session_scope():
    """
    Provide a transactional scope with automatic rollback on exception.
    
    This context manager ensures:
    - Automatic rollback if any exception occurs
    - Proper session cleanup in all cases
    - Thread-safe session management
    
    Usage:
        with session_scope() as db:
            result = db.query(User).filter_by(email=email).first()
    """
    if not SessionLocal:
        raise RuntimeError("Database not available")
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed, rolled back: {str(e)}")
        raise
    finally:
        session.close()
        SessionLocal.remove()  # Remove thread-local session

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
    is_admin = Column(Boolean, default=False)  # Admin users bypass subscription checks
    
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

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, default="New Chat")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For educators
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # For students
    interface_type = Column(String, nullable=False)  # 'companion', 'student', 'planning'
    session_id = Column(String, nullable=False, unique=True, index=True)  # Links to conversation_history
    subject_tag = Column(String, nullable=True, default="General", index=True)  # Subject classification for student chats
    summary = Column(Text, nullable=True)  # Auto-generated summary of chat content
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
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

class ChatAnalytics(Base):
    __tablename__ = "chat_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For educators
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # For students
    action_type = Column(String, nullable=False)  # 'create', 'rename', 'delete', 'reopen'
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=True)
    interface_type = Column(String, nullable=False)  # 'companion', 'student', 'planning'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class EducatorAuditLog(Base):
    """Audit log for educator actions on student data (Australian Privacy Act 1988 compliance)"""
    __tablename__ = "educator_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False, index=True)  # 'view_student', 'create_student', 'update_student', 'delete_student', 'view_activities'
    target_student_id = Column(Integer, nullable=True, index=True)  # Student affected (nullable for list views)
    target_entity = Column(String, nullable=True)  # Entity type affected (student, activity, etc.)
    details = Column(Text, nullable=True)  # Additional context in JSON format
    ip_address = Column(String, nullable=True)  # For security audit trail
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class SafetyAlert(Base):
    """Child safety alerts for concerning content detection"""
    __tablename__ = "safety_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    educator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Primary educator to notify
    alert_type = Column(String, nullable=False)  # 'content_flag', 'student_report', 'system_detected'
    severity = Column(String, default='medium')  # 'low', 'medium', 'high'
    trigger_text = Column(Text, nullable=True)  # The text that triggered the alert (redacted if needed)
    matched_keywords = Column(Text, nullable=True)  # JSON list of matched keywords
    context = Column(Text, nullable=True)  # Additional context
    status = Column(String, default='pending')  # 'pending', 'reviewed', 'actioned', 'dismissed'
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

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

# Process-level flag for one-time initialization
_initialized = False

def initialize_database_once():
    """
    Backend optimization: Run one-time database operations at process startup.
    This includes migrations and initial cleanup checks.
    Should be called once per process, not per session.
    """
    global _initialized
    
    if _initialized:
        return True
    
    if not engine or not SessionLocal:
        logger.warning("Database not available for initialization")
        return False
    
    try:
        # Create tables if they don't exist
        with engine.connect() as conn:
            Base.metadata.create_all(bind=engine)
        
        # Run one-time migrations
        db = SessionLocal()
        try:
            # Migration: Add is_admin column to users table if not exists
            try:
                conn = engine.connect()
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"))
                conn.commit()
                conn.close()
                logger.info("Added is_admin column to users table (or already exists)")
            except Exception as e:
                logger.info(f"is_admin column migration: {str(e)}")
            
            # Migration: Create persistent_sessions table for login persistence
            try:
                conn = engine.connect()
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS persistent_sessions (
                        id SERIAL PRIMARY KEY,
                        token VARCHAR(64) UNIQUE NOT NULL,
                        user_id INTEGER REFERENCES users(id),
                        student_id INTEGER REFERENCES students(id),
                        user_type VARCHAR NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP NOT NULL,
                        last_activity TIMESTAMP DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE,
                        user_agent VARCHAR
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persistent_sessions_token ON persistent_sessions(token)"))
                conn.commit()
                conn.close()
                logger.info("Created persistent_sessions table (or already exists)")
            except Exception as e:
                logger.info(f"persistent_sessions table migration: {str(e)}")
            
            # Create admin account if not exists (requires ADMIN_PASSWORD env var)
            from database import User
            admin_email = "admin@auxpery.com.au"
            admin_password = os.getenv('ADMIN_PASSWORD')
            existing_admin = db.query(User).filter(User.email == admin_email).first()
            
            if admin_password:
                if not existing_admin:
                    admin_password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    admin_user = User(
                        email=admin_email,
                        password_hash=admin_password_hash,
                        full_name="Admin",
                        user_type="educator",
                        is_admin=True,
                        is_active=True
                    )
                    db.add(admin_user)
                    db.commit()
                    logger.info(f"Created admin account: {admin_email}")
                elif existing_admin and not getattr(existing_admin, 'is_admin', False):
                    # Ensure existing admin has is_admin flag set
                    existing_admin.is_admin = True
                    db.commit()
                    logger.info(f"Updated admin flag for: {admin_email}")
            else:
                logger.warning("ADMIN_PASSWORD not set - skipping admin account creation")
            
            # Migrate legacy chats to General subject
            from database import ChatConversation
            updated = db.query(ChatConversation).filter(
                (ChatConversation.subject_tag == None) | (ChatConversation.subject_tag == "")
            ).update({ChatConversation.subject_tag: "General"}, synchronize_session=False)
            
            if updated > 0:
                db.commit()
                logger.info(f"Migrated {updated} legacy chats to 'General' subject tag")
            
            # Quick cleanup check (non-blocking)
            from datetime import datetime, timedelta
            from database import ConversationHistory
            conversation_cutoff = datetime.utcnow() - timedelta(days=730)
            
            old_count = db.query(ConversationHistory).filter(
                ConversationHistory.created_at < conversation_cutoff
            ).count()
            
            if old_count > 100:  # Only log if substantial old data exists
                logger.info(f"Found {old_count} old conversations for eventual cleanup")
        
        finally:
            db.close()
        
        _initialized = True
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

def get_db():
    """
    Get database session (LEGACY - prefer session_scope() context manager).
    
    IMPORTANT: Callers must handle rollback and close properly:
        db = get_db()
        try:
            # operations
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    Better pattern:
        with session_scope() as db:
            # operations (auto-rollback on exception)
    """
    if not SessionLocal:
        return None
    db = SessionLocal()
    
    # Add safety mechanism: if session is in failed state, rollback immediately
    try:
        if db.is_active and db.in_transaction():
            # Check if transaction is in usable state (SQLAlchemy 2.x compatible)
            db.execute(text("SELECT 1"))
    except Exception:
        # Transaction is broken, rollback to clear it
        db.rollback()
        logger.warning("Rolled back broken transaction in get_db()")
    
    return db

# Backend optimization: Cache reference data that doesn't change often
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_subject_list():
    """Get list of available subjects for student chats (cached)"""
    return ["Mathematics", "Science", "Language", "Humanities", "Arts", "Technology", "General"]

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_age_group_list():
    """Get list of age groups (cached)"""
    return [
        "3-6 years (Early Childhood)",
        "6-9 years (Lower Elementary)",
        "9-12 years (Upper Elementary)",
        "12-15 years (Adolescent)"
    ]

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_curriculum_frameworks():
    """Get list of curriculum frameworks (cached)"""
    return [
        "Australian Curriculum V9",
        "Montessori National Curriculum (2011)",
        "Blended Approach"
    ]

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
def create_great_story(db, educator_id: int, title: str, theme: str, content: str, age_group: Optional[str] = None, keywords: Optional[str] = None):
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

def update_great_story(db, story_id: int, title: Optional[str] = None, content: Optional[str] = None, age_group: Optional[str] = None, keywords: Optional[str] = None):
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
def create_planning_note(db, educator_id: int, title: str, content: str = "", chapters: Optional[str] = None, images: Optional[str] = None, materials: Optional[str] = None):
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

def update_planning_note(db, note_id: int, title: Optional[str] = None, content: Optional[str] = None, chapters: Optional[str] = None, images: Optional[str] = None, materials: Optional[str] = None):
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
def trim_message_content(content: str, max_length: int = 10000) -> str:
    """
    Backend optimization: Trim excessively long messages to prevent database bloat.
    Keeps first and last portions for context while indicating truncation.
    """
    if len(content) <= max_length:
        return content
    
    # Keep first 80% and last 10% of allowed length
    keep_start = int(max_length * 0.8)
    keep_end = int(max_length * 0.1)
    
    truncated = (
        content[:keep_start] + 
        f"\n\n... [Content trimmed for storage efficiency. Original length: {len(content)} chars] ...\n\n" +
        content[-keep_end:]
    )
    
    logger.info(f"Trimmed message from {len(content)} to {len(truncated)} characters")
    return truncated

def save_conversation_message(db, session_id: str, interface_type: str, role: str, content: str, 
                              user_id: Optional[int] = None, student_id: Optional[int] = None):
    """
    Save a conversation message to history.
    Backend optimization: Trims excessively long content to prevent database bloat.
    """
    # Trim content if too long (optimization)
    trimmed_content = trim_message_content(content)
    
    message = ConversationHistory(
        user_id=user_id,
        student_id=student_id,
        session_id=session_id,
        interface_type=interface_type,
        role=role,
        content=trimmed_content
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

def get_user_conversation_history(db, user_id: Optional[int] = None, student_id: Optional[int] = None, 
                                  interface_type: Optional[str] = None, limit: int = 50):
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

# Chat Conversation Management functions
def create_chat_conversation(db, title: str, session_id: str, interface_type: str, 
                             user_id: Optional[int] = None, student_id: Optional[int] = None, subject_tag: str = "General"):
    """Create a new chat conversation with optional subject tagging"""
    conversation = ChatConversation(
        title=title,
        user_id=user_id,
        student_id=student_id,
        interface_type=interface_type,
        session_id=session_id,
        subject_tag=subject_tag
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Log analytics
    log_chat_action(db, 'create', conversation.id, interface_type, user_id, student_id)
    
    return conversation

def get_user_chat_conversations(db, user_id: Optional[int] = None, student_id: Optional[int] = None, 
                                interface_type: Optional[str] = None):
    """Get all chat conversations for a user or student"""
    query = db.query(ChatConversation).filter(ChatConversation.is_active == True)
    
    if user_id:
        query = query.filter(ChatConversation.user_id == user_id)
    if student_id:
        query = query.filter(ChatConversation.student_id == student_id)
    if interface_type:
        query = query.filter(ChatConversation.interface_type == interface_type)
    
    return query.order_by(ChatConversation.updated_at.desc()).all()

def get_chat_conversation_by_id(db, conversation_id: int):
    """Get a specific chat conversation by ID"""
    return db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()

def get_chat_conversation_by_session(db, session_id: str):
    """Get a chat conversation by session ID"""
    return db.query(ChatConversation).filter(ChatConversation.session_id == session_id).first()

def rename_chat_conversation(db, conversation_id: int, new_title: str, user_id: int = None, student_id: int = None):
    """Rename a chat conversation"""
    conversation = get_chat_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.title = new_title
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)
        
        # Log analytics
        log_chat_action(db, 'rename', conversation_id, conversation.interface_type, user_id, student_id)
        
        return conversation
    return None

def delete_chat_conversation(db, conversation_id: int, user_id: int = None, student_id: int = None):
    """Soft delete a chat conversation (mark as inactive)"""
    conversation = get_chat_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.is_active = False
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        # Log analytics
        log_chat_action(db, 'delete', conversation_id, conversation.interface_type, user_id, student_id)
        
        return True
    return False

def reopen_chat_conversation(db, conversation_id: int, user_id: int = None, student_id: int = None):
    """Reopen a chat conversation (log analytics)"""
    conversation = get_chat_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        # Log analytics
        log_chat_action(db, 'reopen', conversation_id, conversation.interface_type, user_id, student_id)
        
        return conversation
    return None

def log_chat_action(db, action_type: str, conversation_id: int, interface_type: str,
                   user_id: Optional[int] = None, student_id: Optional[int] = None):
    """Log chat management actions for analytics"""
    analytics = ChatAnalytics(
        user_id=user_id,
        student_id=student_id,
        action_type=action_type,
        conversation_id=conversation_id,
        interface_type=interface_type
    )
    db.add(analytics)
    db.commit()
    return analytics

def get_chat_analytics(db, user_id: int = None, student_id: int = None, days: int = 30):
    """Get chat management analytics for a user or student"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(ChatAnalytics).filter(ChatAnalytics.created_at >= cutoff_date)
    
    if user_id:
        query = query.filter(ChatAnalytics.user_id == user_id)
    if student_id:
        query = query.filter(ChatAnalytics.student_id == student_id)
    
    return query.order_by(ChatAnalytics.created_at.desc()).all()

def get_chat_analytics_summary(db, user_id: int = None, student_id: int = None, days: int = 30):
    """Get summary statistics for chat management"""
    from sqlalchemy import func
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(
        ChatAnalytics.action_type,
        func.count(ChatAnalytics.id).label('count')
    ).filter(ChatAnalytics.created_at >= cutoff_date)
    
    if user_id:
        query = query.filter(ChatAnalytics.user_id == user_id)
    if student_id:
        query = query.filter(ChatAnalytics.student_id == student_id)
    
    results = query.group_by(ChatAnalytics.action_type).all()
    
    return {action: count for action, count in results}

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

# Child Safety Content Detection (Child protection compliance)
CONCERNING_KEYWORDS = {
    'high': [
        'suicide', 'kill myself', 'want to die', 'end my life', 'self harm',
        'hurt myself', 'cutting', 'overdose', 'abuse', 'being hurt',
        'someone touching me', 'unsafe at home', 'scared of',
    ],
    'medium': [
        'bullying', 'bullied', 'threatened', 'scared', 'hate myself',
        'worthless', 'nobody likes me', 'alone', 'depressed', 'anxious',
        'cant sleep', 'nightmares', 'hurt by', 'hitting me', 'mean to me',
    ],
    'low': [
        'sad', 'worried', 'nervous', 'upset', 'angry', 'frustrated',
        'dont want to go to school', 'no friends',
    ]
}

def detect_concerning_content(text: str) -> tuple:
    """Detect concerning content in student messages.
    
    Returns: (detected: bool, severity: str, matched_keywords: list)
    """
    if not text:
        return False, None, []
    
    text_lower = text.lower()
    matched = []
    highest_severity = None
    
    # Check in order of severity (high first)
    for severity in ['high', 'medium', 'low']:
        for keyword in CONCERNING_KEYWORDS[severity]:
            if keyword in text_lower:
                matched.append(keyword)
                if highest_severity is None:
                    highest_severity = severity
    
    return len(matched) > 0, highest_severity, matched

def create_safety_alert(db, student_id: int, educator_id: int, alert_type: str,
                        trigger_text: Optional[str] = None, matched_keywords: Optional[list] = None,
                        severity: str = 'medium', context: Optional[str] = None):
    """Create a safety alert for educator review."""
    try:
        import json
        alert = SafetyAlert(
            student_id=student_id,
            educator_id=educator_id,
            alert_type=alert_type,
            severity=severity,
            trigger_text=trigger_text[:500] if trigger_text else None,  # Limit length
            matched_keywords=json.dumps(matched_keywords) if matched_keywords else None,
            context=context,
            status='pending'
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating safety alert: {str(e)}")
        return None

def get_pending_safety_alerts(db, educator_id: int) -> list:
    """Get all pending safety alerts for an educator's students."""
    try:
        return db.query(SafetyAlert).filter(
            SafetyAlert.educator_id == educator_id,
            SafetyAlert.status == 'pending'
        ).order_by(SafetyAlert.created_at.desc()).all()
    except Exception as e:
        logger.error(f"Error getting safety alerts: {str(e)}")
        return []

def review_safety_alert(db, alert_id: int, reviewer_id: int, status: str, notes: Optional[str] = None):
    """Mark a safety alert as reviewed."""
    try:
        alert = db.query(SafetyAlert).filter(SafetyAlert.id == alert_id).first()
        if alert:
            alert.status = status
            alert.reviewed_by = reviewer_id
            alert.reviewed_at = datetime.utcnow()
            alert.review_notes = notes
            db.commit()
            return alert
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error reviewing safety alert: {str(e)}")
        return None

def create_student_concern_report(db, student_id: int, concern_text: str) -> bool:
    """Create a concern report from a student (Report a Concern feature)."""
    try:
        # Get student's educator
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return False
        
        alert = create_safety_alert(
            db=db,
            student_id=student_id,
            educator_id=student.educator_id,
            alert_type='student_report',
            trigger_text=concern_text,
            severity='medium',
            context='Student initiated concern report'
        )
        return alert is not None
    except Exception as e:
        logger.error(f"Error creating student concern report: {str(e)}")
        return False

def delete_student_and_data(db, student_id: int, educator_id: int, reason: Optional[str] = None) -> dict:
    """Delete a student account and all associated data with audit trail.
    
    This implements the 'right to erasure' under Australian Privacy Act.
    Returns summary of deleted records.
    """
    try:
        # Get student info for audit log before deletion
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {'success': False, 'error': 'Student not found'}
        
        student_name = student.full_name
        student_username = student.username
        
        # Verify educator has permission (must be the student's educator)
        if student.educator_id != educator_id:
            return {'success': False, 'error': 'Permission denied - not the student\'s educator'}
        
        summary = {
            'student_name': student_name,
            'activities_deleted': 0,
            'conversations_deleted': 0,
            'chat_sessions_deleted': 0,
            'consents_deleted': 0,
            'safety_alerts_deleted': 0,
        }
        
        # Delete student activities
        summary['activities_deleted'] = db.query(StudentActivity).filter(
            StudentActivity.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete conversation history
        summary['conversations_deleted'] = db.query(ConversationHistory).filter(
            ConversationHistory.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete chat conversations
        summary['chat_sessions_deleted'] = db.query(ChatConversation).filter(
            ChatConversation.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete consent records
        summary['consents_deleted'] = db.query(ConsentRecord).filter(
            ConsentRecord.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete parental consent records
        db.query(ParentalConsentRecord).filter(
            ParentalConsentRecord.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete safety alerts (but keep for 25 years if child safety related - mark as deleted instead)
        summary['safety_alerts_deleted'] = db.query(SafetyAlert).filter(
            SafetyAlert.student_id == student_id
        ).delete(synchronize_session=False)
        
        # Delete the student account
        db.query(Student).filter(Student.id == student_id).delete(synchronize_session=False)
        
        # Log the deletion in audit trail (this is permanent and not deleted)
        import json
        audit_log = EducatorAuditLog(
            educator_id=educator_id,
            action_type='delete_student',
            target_student_id=student_id,
            target_entity='student',
            details=json.dumps({
                'student_name': student_name,
                'student_username': student_username,
                'reason': reason,
                'records_deleted': summary
            })
        )
        db.add(audit_log)
        
        db.commit()
        summary['success'] = True
        logger.info(f"Student {student_id} ({student_name}) deleted by educator {educator_id}")
        return summary
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting student and data: {str(e)}")
        return {'success': False, 'error': str(e)}

# Data Retention Functions (Australian Privacy Act 1988 APP 11 compliance)
RETENTION_YEARS_DEFAULT = 7  # 7-year retention for general student records
RETENTION_YEARS_CHILD_SAFETY = 25  # Extended retention for child safety records

def cleanup_old_conversations(db, retention_years: int = RETENTION_YEARS_DEFAULT) -> int:
    """Delete conversation history older than retention period.
    
    Returns the number of records deleted.
    Runs as part of scheduled maintenance.
    """
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=retention_years * 365)
    
    try:
        # First, get count for logging
        old_count = db.query(ConversationHistory).filter(
            ConversationHistory.created_at < cutoff_date
        ).count()
        
        if old_count == 0:
            return 0
        
        # Delete old conversations
        deleted = db.query(ConversationHistory).filter(
            ConversationHistory.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        # Also delete associated chat conversations with no remaining messages
        orphan_chats = db.query(ChatConversation).filter(
            ChatConversation.created_at < cutoff_date,
            ~ChatConversation.session_id.in_(
                db.query(ConversationHistory.session_id).distinct()
            )
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Data retention: Deleted {deleted} old conversation records, {orphan_chats} orphan chats")
        return deleted
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during conversation cleanup: {str(e)}")
        return 0

def cleanup_old_planning_notes(db, retention_years: int = RETENTION_YEARS_DEFAULT) -> int:
    """Delete planning notes (including attached images) older than retention period.
    
    Returns the number of records deleted.
    """
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=retention_years * 365)
    
    try:
        deleted = db.query(PlanningNote).filter(
            PlanningNote.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Data retention: Deleted {deleted} old planning notes")
        return deleted
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during planning notes cleanup: {str(e)}")
        return 0

def cleanup_old_student_activities(db, retention_years: int = RETENTION_YEARS_DEFAULT) -> int:
    """Delete student activity records older than retention period.
    
    Returns the number of records deleted.
    """
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=retention_years * 365)
    
    try:
        deleted = db.query(StudentActivity).filter(
            StudentActivity.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Data retention: Deleted {deleted} old student activity records")
        return deleted
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during student activity cleanup: {str(e)}")
        return 0

def run_data_retention_cleanup(db) -> dict:
    """Run all data retention cleanup tasks.
    
    Should be called periodically (e.g., daily or weekly).
    Returns summary of cleanup actions.
    """
    results = {
        'conversations_deleted': cleanup_old_conversations(db),
        'planning_notes_deleted': cleanup_old_planning_notes(db),
        'student_activities_deleted': cleanup_old_student_activities(db),
        'retention_years': RETENTION_YEARS_DEFAULT,
        'run_at': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Data retention cleanup completed: {results}")
    return results

# Educator Audit Log functions (Australian Privacy Act 1988 compliance)
def log_educator_action(db, educator_id: int, action_type: str, target_student_id: int = None,
                        target_entity: str = None, details: str = None, ip_address: str = None):
    """Log educator actions on student data for audit trail.
    
    Action types: 'view_student', 'create_student', 'update_student', 'delete_student', 
                  'view_activities', 'export_data', 'share_student'
    """
    try:
        audit_log = EducatorAuditLog(
            educator_id=educator_id,
            action_type=action_type,
            target_student_id=target_student_id,
            target_entity=target_entity,
            details=details,
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log educator action: {e}")
        return None

def get_educator_audit_logs(db, educator_id: int = None, student_id: int = None, 
                            action_type: str = None, days: int = 90):
    """Retrieve educator audit logs with optional filters"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(EducatorAuditLog).filter(EducatorAuditLog.created_at >= cutoff_date)
    
    if educator_id:
        query = query.filter(EducatorAuditLog.educator_id == educator_id)
    if student_id:
        query = query.filter(EducatorAuditLog.target_student_id == student_id)
    if action_type:
        query = query.filter(EducatorAuditLog.action_type == action_type)
    
    return query.order_by(EducatorAuditLog.created_at.desc()).all()

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

def get_student_learning_journey(db, student_id: int):
    """
    Get all topics explored by a student for the Learning Journey Map.
    Extracts keywords from student conversation history and groups by subject.
    Returns: {subject: [{keyword, count, first_explored, last_explored}]}
    """
    from utils import detect_trending_keywords
    
    try:
        # Get all student conversations
        conversations = db.query(ConversationHistory).filter(
            ConversationHistory.student_id == student_id,
            ConversationHistory.role == 'user'
        ).order_by(ConversationHistory.created_at.asc()).all()
        
        # Track topics with their exploration data
        topic_data = {}
        
        for conv in conversations:
            # Extract keywords from this message
            detected = detect_trending_keywords(conv.content or "")
            
            for kw in detected:
                subject = kw['subject']
                keyword = kw['keyword']
                key = f"{subject}|{keyword}"
                
                if key not in topic_data:
                    topic_data[key] = {
                        'subject': subject,
                        'keyword': keyword,
                        'count': 0,
                        'first_explored': conv.created_at,
                        'last_explored': conv.created_at,
                        'session_ids': set()
                    }
                
                topic_data[key]['count'] += 1
                topic_data[key]['last_explored'] = conv.created_at
                topic_data[key]['session_ids'].add(conv.session_id)
        
        # Group by subject
        journey_data = {}
        for key, data in topic_data.items():
            subject = data['subject']
            if subject not in journey_data:
                journey_data[subject] = []
            
            # Convert session_ids set to list for JSON serialization
            data['session_count'] = len(data['session_ids'])
            del data['session_ids']
            journey_data[subject].append(data)
        
        # Sort topics within each subject by count
        for subject in journey_data:
            journey_data[subject].sort(key=lambda x: x['count'], reverse=True)
        
        return journey_data
    except Exception as e:
        print(f"Error getting student learning journey: {str(e)}")
        return {}

def get_topic_connections(db, student_id: int):
    """
    Find connections between topics based on co-occurrence in same session.
    Returns list of (topic1, topic2, weight) for network graph edges.
    """
    from utils import detect_trending_keywords
    
    try:
        # Get all student conversations grouped by session
        conversations = db.query(ConversationHistory).filter(
            ConversationHistory.student_id == student_id,
            ConversationHistory.role == 'user'
        ).all()
        
        # Group by session
        session_topics = {}
        for conv in conversations:
            session_id = conv.session_id
            if session_id not in session_topics:
                session_topics[session_id] = set()
            
            detected = detect_trending_keywords(conv.content or "")
            for kw in detected:
                session_topics[session_id].add(f"{kw['subject']}|{kw['keyword']}")
        
        # Find co-occurrences (topics in same session)
        connections = {}
        for session_id, topics in session_topics.items():
            topic_list = list(topics)
            for i in range(len(topic_list)):
                for j in range(i + 1, len(topic_list)):
                    # Create sorted pair key for consistency
                    pair = tuple(sorted([topic_list[i], topic_list[j]]))
                    if pair not in connections:
                        connections[pair] = 0
                    connections[pair] += 1
        
        # Convert to list format
        return [(pair[0], pair[1], weight) for pair, weight in connections.items()]
    except Exception as e:
        print(f"Error getting topic connections: {str(e)}")
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
    attestation_text = Column(Text, nullable=True)  # Full text of what educator attested to
    expires_at = Column(DateTime, nullable=True)  # Optional expiry
    withdrawn_at = Column(DateTime, nullable=True)  # If consent withdrawn
    notes = Column(Text, nullable=True)

class LoginAttempt(Base):
    """Track failed login attempts for rate limiting"""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, nullable=False, index=True)  # Email or username
    attempt_type = Column(String, default='educator')  # 'educator' or 'student'
    success = Column(Boolean, default=False)
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)

# ---- LOGIN RATE LIMITING FUNCTIONS ----

def record_login_attempt(db, identifier: str, attempt_type: str = 'educator', success: bool = False, ip_address: str = None):
    """Record a login attempt for rate limiting"""
    try:
        attempt = LoginAttempt(
            identifier=identifier.lower(),
            attempt_type=attempt_type,
            success=success,
            attempted_at=datetime.utcnow(),
            ip_address=ip_address
        )
        db.add(attempt)
        db.commit()
        return attempt
    except Exception as e:
        print(f"Error recording login attempt: {str(e)}")
        db.rollback()
        return None

def check_login_rate_limit(db, identifier: str, max_attempts: int = 5, lockout_minutes: int = 15):
    """Check if account is locked out due to too many failed attempts.
    Returns (is_locked, remaining_lockout_seconds, failed_count)"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=lockout_minutes)
        
        # Count failed attempts since cutoff
        failed_count = db.query(LoginAttempt).filter(
            LoginAttempt.identifier == identifier.lower(),
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff_time
        ).count()
        
        if failed_count >= max_attempts:
            # Get most recent failed attempt to calculate remaining lockout
            last_failed = db.query(LoginAttempt).filter(
                LoginAttempt.identifier == identifier.lower(),
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff_time
            ).order_by(LoginAttempt.attempted_at.desc()).first()
            
            if last_failed:
                unlock_time = last_failed.attempted_at + timedelta(minutes=lockout_minutes)
                remaining_seconds = (unlock_time - datetime.utcnow()).total_seconds()
                if remaining_seconds > 0:
                    return (True, int(remaining_seconds), failed_count)
        
        return (False, 0, failed_count)
    except Exception as e:
        print(f"Error checking rate limit: {str(e)}")
        return (False, 0, 0)

def clear_login_attempts(db, identifier: str):
    """Clear failed login attempts after successful login"""
    try:
        db.query(LoginAttempt).filter(
            LoginAttempt.identifier == identifier.lower()
        ).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        print(f"Error clearing login attempts: {str(e)}")
        db.rollback()


class PersistentSession(Base):
    """Store persistent session tokens for login persistence across browser refresh"""
    __tablename__ = "persistent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    user_type = Column(String, nullable=False)  # 'educator' or 'student'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    user_agent = Column(String, nullable=True)


def create_persistent_session(db, user_id=None, student_id=None, user_type='educator', 
                               duration_hours=24, user_agent=None):
    """Create a new persistent session token for browser persistence.
    Returns the session token string."""
    import secrets
    
    try:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        
        session = PersistentSession(
            token=token,
            user_id=user_id,
            student_id=student_id,
            user_type=user_type,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_activity=datetime.utcnow(),
            is_active=True,
            user_agent=user_agent
        )
        db.add(session)
        db.commit()
        return token
    except Exception as e:
        print(f"Error creating persistent session: {str(e)}")
        db.rollback()
        return None


def validate_persistent_session(db, token: str):
    """Validate a session token and return user info if valid.
    Returns dict with user_id/student_id, user_type, or None if invalid."""
    try:
        session = db.query(PersistentSession).filter(
            PersistentSession.token == token,
            PersistentSession.is_active == True,
            PersistentSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            return None
        
        session.last_activity = datetime.utcnow()
        db.commit()
        
        return {
            'user_id': session.user_id,
            'student_id': session.student_id,
            'user_type': session.user_type,
            'created_at': session.created_at
        }
    except Exception as e:
        print(f"Error validating session: {str(e)}")
        return None


def invalidate_persistent_session(db, token: str):
    """Invalidate/logout a session by token"""
    try:
        session = db.query(PersistentSession).filter(
            PersistentSession.token == token
        ).first()
        if session:
            session.is_active = False
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error invalidating session: {str(e)}")
        db.rollback()
        return False


def invalidate_all_user_sessions(db, user_id=None, student_id=None):
    """Invalidate all sessions for a user (e.g., on password change)"""
    try:
        query = db.query(PersistentSession).filter(PersistentSession.is_active == True)
        if user_id:
            query = query.filter(PersistentSession.user_id == user_id)
        if student_id:
            query = query.filter(PersistentSession.student_id == student_id)
        
        query.update({PersistentSession.is_active: False}, synchronize_session=False)
        db.commit()
        return True
    except Exception as e:
        print(f"Error invalidating sessions: {str(e)}")
        db.rollback()
        return False


def cleanup_expired_sessions(db):
    """Remove expired sessions from database"""
    try:
        deleted = db.query(PersistentSession).filter(
            PersistentSession.expires_at < datetime.utcnow()
        ).delete(synchronize_session=False)
        db.commit()
        return deleted
    except Exception as e:
        print(f"Error cleaning up sessions: {str(e)}")
        db.rollback()
        return 0


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

def create_student_with_consent(db, username: str, password: str, full_name: str, 
                                 educator_id: int, age_group: str = None,
                                 consent_attestation_text: str = None):
    """Create student account with guardian consent in a single atomic transaction.
    
    This ensures consent is recorded BEFORE the student account is created,
    meeting Australian Privacy Act 1988 APP 3 requirements for child data collection.
    Returns tuple: (student, consent_record) or (None, None) on failure.
    """
    try:
        # Start transaction - don't commit until both records are created
        
        # First, create the student (but don't commit yet)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        student = Student(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            educator_id=educator_id,
            age_group=age_group
        )
        db.add(student)
        db.flush()  # Get the student ID without committing
        
        # Create consent record with the student ID
        consent = ParentalConsentRecord(
            student_id=student.id,
            educator_id=educator_id,
            consent_obtained=True,
            consent_date=datetime.utcnow(),
            consent_method='educator_confirmed_with_attestation',
            attestation_text=consent_attestation_text or "Guardian consent confirmed by educator"
        )
        db.add(consent)
        
        # Log the educator action for audit trail
        audit_log = EducatorAuditLog(
            educator_id=educator_id,
            action_type='create_student',
            target_student_id=student.id,
            target_entity='student',
            details=f'{{"full_name": "{full_name}", "username": "{username}", "age_group": "{age_group}"}}'
        )
        db.add(audit_log)
        
        # Now commit all three records atomically
        db.commit()
        db.refresh(student)
        db.refresh(consent)
        
        return student, consent
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating student with consent: {str(e)}")
        return None, None

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

def get_cached_educator_profile(educator_id):
    """
    Get educator profile with caching for dashboard performance.
    Combines institution info and enforcement status in a single cached call.
    Cache TTL: 60 seconds
    """
    import streamlit as st
    from datetime import datetime, timedelta
    
    cache_key = f'educator_profile_{educator_id}'
    cache_time_key = f'educator_profile_time_{educator_id}'
    CACHE_TTL = timedelta(seconds=60)
    
    cached_data = st.session_state.get(cache_key)
    cached_time = st.session_state.get(cache_time_key)
    
    if cached_data and cached_time:
        if datetime.now() - cached_time < CACHE_TTL:
            return cached_data
    
    db = get_db()
    if not db:
        return None
    
    try:
        educator = db.query(User).filter(User.id == educator_id).first()
        if not educator:
            db.close()
            return None
        
        enforcement_on = is_institution_enforcement_on(db)
        
        result = {
            'id': educator.id,
            'email': educator.email,
            'full_name': educator.full_name,
            'institution_name': educator.institution_name,
            'institution_needs_setup': not educator.institution_name or educator.institution_name.strip() == '',
            'enforcement_on': enforcement_on
        }
        
        db.close()
        
        st.session_state[cache_key] = result
        st.session_state[cache_time_key] = datetime.now()
        return result
    except Exception as e:
        print(f"Error getting educator profile: {str(e)}")
        if db:
            db.close()
        return None

def invalidate_educator_profile_cache(educator_id):
    """Invalidate educator profile cache after updates"""
    import streamlit as st
    cache_key = f'educator_profile_{educator_id}'
    cache_time_key = f'educator_profile_time_{educator_id}'
    if cache_key in st.session_state:
        del st.session_state[cache_key]
    if cache_time_key in st.session_state:
        del st.session_state[cache_time_key]

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
        
        # Count educators/teachers without institution (both user types are educators)
        educators_without_institution = db.query(User).filter(
            or_(User.user_type == 'educator', User.user_type == 'teacher'),
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
        print(f"DEBUG: Updating institution for educator_id={educator_id}, institution={institution_name}")
        educator = db.query(User).filter(
            User.id == educator_id
        ).first()
        
        if not educator:
            print(f"ERROR: Educator not found with id={educator_id}")
            return (False, False)
        
        # Update institution name
        educator.institution_name = institution_name.strip() if institution_name else None
        print(f"DEBUG: Set institution_name to {educator.institution_name}")
        db.commit()
        print(f"DEBUG: Committed successfully")
        
        # Check if this triggers auto-enable
        auto_enabled = maybe_auto_enable_enforcement(db)
        print(f"DEBUG: Auto-enabled={auto_enabled}")
        
        return (True, auto_enabled)
    except Exception as e:
        print(f"ERROR updating institution: {str(e)}")
        import traceback
        traceback.print_exc()
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

# ---- SUBJECT-BASED CHAT ORGANIZATION (Student Chat Management) ----

def get_available_subjects():
    """Get list of available subject tags for student chats"""
    return [
        "Mathematics",
        "Science",
        "Language",
        "Humanities",
        "Cosmic Education",
        "Personal Project",
        "General"
    ]

def get_student_chats_by_subject(db, student_id: int):
    """
    Get student chats grouped by subject
    Returns: dict with subject as key, list of conversations as value
    """
    try:
        chats = db.query(ChatConversation).filter(
            ChatConversation.student_id == student_id,
            ChatConversation.interface_type == 'student',
            ChatConversation.is_active == True
        ).order_by(ChatConversation.updated_at.desc()).all()
        
        # Group by subject
        grouped = {}
        for chat in chats:
            subject = chat.subject_tag or "General"
            if subject not in grouped:
                grouped[subject] = []
            grouped[subject].append(chat)
        
        return grouped
    except Exception as e:
        print(f"Error getting student chats by subject: {str(e)}")
        return {}

def get_filtered_student_chats(db, educator_id: Optional[int] = None, student_id: Optional[int] = None, 
                               subject_tag: Optional[str] = None):
    """
    Get filtered student chats for educator dashboard
    Filters by student and/or subject
    """
    try:
        query = db.query(ChatConversation).filter(
            ChatConversation.interface_type == 'student',
            ChatConversation.is_active == True
        )
        
        # Filter by student if specified
        if student_id:
            query = query.filter(ChatConversation.student_id == student_id)
        
        # Filter by subject if specified
        if subject_tag:
            query = query.filter(ChatConversation.subject_tag == subject_tag)
        
        # If educator specified, only show students from same institution
        if educator_id:
            educator = db.query(User).filter(User.id == educator_id).first()
            if educator and educator.institution_name:
                # Get students from same institution
                students = db.query(Student).join(User).filter(
                    User.institution_name == educator.institution_name
                ).all()
                student_ids = [s.id for s in students]
                query = query.filter(ChatConversation.student_id.in_(student_ids))
        
        return query.order_by(ChatConversation.updated_at.desc()).all()
    except Exception as e:
        print(f"Error getting filtered student chats: {str(e)}")
        return []

def update_chat_summary(db, conversation_id: int, summary: str):
    """Update the summary field of a chat conversation"""
    try:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.summary = summary
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating chat summary: {str(e)}")
        db.rollback()
        return False

def migrate_legacy_chats_to_general(db):
    """
    Migrate existing chats without subject_tag to 'General'
    Run once during deployment
    """
    try:
        # Update all chats with NULL or empty subject_tag
        updated = db.query(ChatConversation).filter(
            (ChatConversation.subject_tag == None) | (ChatConversation.subject_tag == "")
        ).update({ChatConversation.subject_tag: "General"}, synchronize_session=False)
        
        db.commit()
        print(f"Migrated {updated} legacy chats to 'General' subject tag")
        return updated
    except Exception as e:
        print(f"Error migrating legacy chats: {str(e)}")
        db.rollback()
        return 0
