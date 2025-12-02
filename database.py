import os
import bcrypt
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Table, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
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
    
    # Stripe subscription fields
    stripe_customer_id = Column(String, nullable=True, index=True)
    subscription_status = Column(String, nullable=True, default='inactive')  # 'active', 'inactive', 'cancelled', 'past_due'
    subscription_end_date = Column(DateTime, nullable=True)
    subscription_plan = Column(String, nullable=True)  # 'monthly', 'yearly'
    
    # Onboarding tracking
    onboarding_completed = Column(Boolean, default=False, nullable=True)
    
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

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeedbackTicket(Base):
    __tablename__ = "feedback_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    ticket_type = Column(String, nullable=False)  # 'bug_report' or 'feature_request'
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=True)  # 'low', 'medium', 'high' for bugs
    status = Column(String, default='new')  # 'new', 'reviewed', 'resolved'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SubscriptionContact(Base):
    __tablename__ = "subscription_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)  # 'billing', 'cancel_request', 'upgrade', 'other'
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default='new')  # 'new', 'responded'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
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
            
            # Migration: Add onboarding_completed column if it doesn't exist
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                columns = [col['name'] for col in inspector.get_columns('users')]
                if 'onboarding_completed' not in columns:
                    db.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE"))
                    db.commit()
                    logger.info("Added onboarding_completed column to users table")
            except Exception as migration_error:
                logger.warning(f"Onboarding column migration skipped: {str(migration_error)}")
        
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

def get_user_by_stripe_customer_id(db, stripe_customer_id: str) -> Optional[User]:
    """Get user by Stripe customer ID"""
    return db.query(User).filter(User.stripe_customer_id == stripe_customer_id).first()

def update_user_subscription(db, email: str, stripe_customer_id: str = None, 
                             subscription_status: str = None, subscription_end_date: datetime = None,
                             subscription_plan: str = None) -> Optional[User]:
    """Update user's subscription information"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    if stripe_customer_id is not None:
        user.stripe_customer_id = stripe_customer_id
    if subscription_status is not None:
        user.subscription_status = subscription_status
    if subscription_end_date is not None:
        user.subscription_end_date = subscription_end_date
    if subscription_plan is not None:
        user.subscription_plan = subscription_plan
    
    db.commit()
    db.refresh(user)
    return user

def update_subscription_by_customer_id(db, stripe_customer_id: str,
                                       subscription_status: str = None, 
                                       subscription_end_date: datetime = None,
                                       subscription_plan: str = None) -> Optional[User]:
    """Update subscription by Stripe customer ID"""
    user = db.query(User).filter(User.stripe_customer_id == stripe_customer_id).first()
    if not user:
        return None
    
    if subscription_status is not None:
        user.subscription_status = subscription_status
    if subscription_end_date is not None:
        user.subscription_end_date = subscription_end_date
    if subscription_plan is not None:
        user.subscription_plan = subscription_plan
    
    db.commit()
    db.refresh(user)
    return user

def check_subscription_active(db, user_id: int) -> bool:
    """
    Check if user has access based on subscription status.
    Handles Stripe state machine: active, trialing, past_due (grace period), cancelled (until end date)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    status = user.subscription_status
    end_date = user.subscription_end_date
    
    # Active or trialing subscriptions have access
    if status in ('active', 'trialing'):
        return True
    
    # Past due gets grace period (still has access until Stripe cancels)
    if status == 'past_due':
        return True
    
    # Cancelled subscriptions have access until their paid period ends
    if status == 'cancelled' and end_date and end_date > datetime.utcnow():
        return True
    
    # Check if end_date hasn't passed (for any status)
    if end_date and end_date > datetime.utcnow():
        return True
    
    return False

def get_all_educators(db):
    """Get all educators"""
    return db.query(User).filter(User.user_type == 'educator').all()

def get_onboarding_status(db, user_id: int) -> bool:
    """Check if user has completed onboarding"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user.onboarding_completed or False
    return False

def mark_onboarding_completed(db, user_id: int) -> bool:
    """Mark user's onboarding as completed"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.onboarding_completed = True
        db.commit()
        return True
    return False

def create_sample_lesson_plans_for_user(db, user_id: int) -> bool:
    """
    Create sample lesson plans for new educators to demonstrate platform value.
    Only creates if user has no existing lesson plans.
    """
    existing_plans = db.query(LessonPlan).filter(LessonPlan.creator_id == user_id).count()
    if existing_plans > 0:
        return False
    
    sample_plans = [
        {
            "title": "Example: The Story of the Universe (Foundation)",
            "description": "A sample Cosmic Education lesson introducing young children to their place in the universe.",
            "age_group": "3-6",
            "content": """## The Story of the Universe - Foundation Level

### Learning Intentions
Students will develop a sense of wonder about the universe and their place within it.

### Montessori Principles Applied
- **Cosmic Education**: Connecting the child to the larger story of existence
- **Sensorial Learning**: Using visual and tactile materials to explore concepts
- **Follow the Child**: Allowing natural curiosity to guide exploration

### Australian Curriculum Links
- Science: Earth and Space Sciences (ACSSU004)
- HASS: History (ACHASSK012)

### Materials Needed
- Timeline of Life materials
- Globe or sphere
- Star charts (simplified)
- Natural objects collection

### Lesson Flow

**Opening (10 minutes)**
Gather children in a circle. Begin with a moment of silence, then ask: "Have you ever looked at the stars and wondered where they came from?"

**Main Activity (20-30 minutes)**
1. Tell the First Great Story (abbreviated for this age)
2. Show the Timeline of Life
3. Let children handle materials and ask questions

**Closing (10 minutes)**
Invite children to share one thing that amazed them about our universe.

### Extensions
- Create star mobiles
- Plant seeds to observe growth
- Collect natural objects for classification

---
*This is a sample lesson plan demonstrating Guide's AI-powered planning capabilities.*"""
        },
        {
            "title": "Example: Interdependence in Ecosystems (Years 3-4)",
            "description": "A sample lesson exploring ecological relationships through the Montessori lens.",
            "age_group": "6-9",
            "content": """## Interdependence in Ecosystems - Years 3-4

### Learning Intentions
Students will understand how living things depend on each other and their environment.

### Success Criteria
- Identify at least 3 relationships between living things
- Explain how changes to one part affect the whole ecosystem
- Create a food web diagram

### Montessori Principles Applied
- **Cosmic Education**: Understanding interconnection of all life
- **Going Out**: Connecting learning to the real world
- **Research Skills**: Using multiple sources to investigate

### Australian Curriculum Links
- Science: Biological Sciences (ACSSU073)
- Science Inquiry Skills (ACSIS065)
- Cross-curriculum: Sustainability

### Materials Needed
- Ecosystem cards or pictures
- String or yarn for web activity
- Journals for observations
- Magnifying glasses

### Lesson Structure

**Introduction (15 minutes)**
Review what students know about ecosystems. Introduce the concept of interdependence using a ball of yarn - each child holds part of the web.

**Investigation (30 minutes)**
1. Students work in small groups with ecosystem cards
2. Identify producers, consumers, and decomposers
3. Map relationships using arrows

**Application (20 minutes)**
Groups present their food webs. Discuss: "What happens if we remove one organism?"

**Reflection (10 minutes)**
Journal entry: Draw yourself as part of an ecosystem. How do you depend on other living things?

### Assessment
- Observation of group work and discussions
- Food web diagram accuracy
- Journal reflection depth

---
*This is a sample lesson plan demonstrating Guide's AI-powered planning capabilities.*"""
        },
        {
            "title": "Example: Systems Thinking in History (Years 7-8)",
            "description": "A sample adolescent lesson connecting historical events to contemporary systems.",
            "age_group": "12-15",
            "content": """## Systems Thinking in History - Years 7-8

### Learning Intentions
Students will analyse how interconnected factors led to significant historical change.

### Success Criteria
- Identify multiple causes for historical events
- Recognise feedback loops in historical systems
- Apply systems thinking to a current issue

### Montessori Principles Applied
- **Cosmic Education**: Understanding patterns across time
- **Valorisation**: Meaningful work that contributes to community
- **Erdkinder**: Connecting learning to real-world application

### Australian Curriculum Links
- History: The Ancient to the Modern World (ACDSEH001)
- Critical and Creative Thinking (general capability)
- Ethical Understanding

### Resources
- Systems mapping templates
- Primary and secondary sources
- Digital collaboration tools

### Lesson Structure

**Provocation (10 minutes)**
Present a current news story about interconnected global issues (climate, trade, migration). Ask: "How do these connect? Have similar patterns occurred in history?"

**Investigation (40 minutes)**
1. Groups select a historical turning point
2. Use systems mapping to identify:
   - Key actors and their motivations
   - Economic factors
   - Environmental conditions
   - Social and cultural influences
3. Identify feedback loops (how actions created reactions)

**Synthesis (25 minutes)**
Groups present their systems maps. Class identifies common patterns across different historical periods.

**Application (15 minutes)**
Individual reflection: Apply systems thinking to a current challenge. What interconnections do you notice? What historical lessons might apply?

### Assessment
- Systems map complexity and accuracy
- Quality of historical evidence used
- Connection to contemporary issues

### Differentiation
- Scaffolded templates for emerging learners
- Extension: Research project on unintended consequences in history

---
*This is a sample lesson plan demonstrating Guide's AI-powered planning capabilities.*"""
        }
    ]
    
    try:
        for plan in sample_plans:
            lesson = LessonPlan(
                title=plan["title"],
                description=plan["description"],
                content=plan["content"],
                age_group=plan["age_group"],
                creator_id=user_id
            )
            db.add(lesson)
        db.commit()
        logger.info(f"Created {len(sample_plans)} sample lesson plans for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create sample lesson plans: {str(e)}")
        db.rollback()
        return False

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
                              user_id: int = None, student_id: int = None):
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

# Chat Conversation Management functions
def create_chat_conversation(db, title: str, session_id: str, interface_type: str, 
                             user_id: int = None, student_id: int = None, subject_tag: str = "General"):
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

def get_user_chat_conversations(db, user_id: int = None, student_id: int = None, 
                                interface_type: str = None):
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
                   user_id: int = None, student_id: int = None):
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

def get_filtered_student_chats(db, educator_id: int = None, student_id: int = None, 
                               subject_tag: str = None):
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
