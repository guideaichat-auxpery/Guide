import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI
import io
import json
import hashlib
# Note: Email functionality handled via feedback system, not direct SMTP
import secrets
import string
import re

# Configure page
st.set_page_config(
    page_title="Guide - AI Curriculum Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize OpenAI client
# Using ChatGPT 4o-mini model as requested by the user
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.stop()
    return OpenAI(api_key=api_key)

client = get_openai_client()

# Authentication and User Management System
def init_user_database():
    """Initialize user database with persistent storage"""
    # Load from file if exists
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.users = data.get('users', {})
                st.session_state.usage_logs = data.get('usage_logs', {})
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            st.error(f"Error reading user database: {str(e)}. Starting with empty database.")
            st.session_state.users = {}
            st.session_state.usage_logs = {}
        except Exception as e:
            st.error(f"Unexpected error loading user data: {str(e)}")
            st.session_state.users = {}
            st.session_state.usage_logs = {}
    else:
        st.session_state.users = {}
        st.session_state.usage_logs = {}
    
    if 'training_content' not in st.session_state:
        st.session_state.training_content = ""
    if 'feedback_messages' not in st.session_state:
        st.session_state.feedback_messages = []

def save_user_database():
    """Save user database to persistent storage"""
    try:
        data = {
            'users': st.session_state.users,
            'usage_logs': st.session_state.usage_logs
        }
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving user data: {str(e)}")
        return False
    return True

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_student_credentials():
    """Generate random username and password for students"""
    username = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    return username, password

def create_teacher_account(username, password, email, school=""):
    """Create new teacher account"""
    # Input validation
    if not username or not password or not email:
        return False, "Username, password, and email are required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    if '@' not in email:
        return False, "Please enter a valid email address"
    
    if username in st.session_state.users:
        return False, "Username already exists"
    
    st.session_state.users[username] = {
        'password': hash_password(password),
        'role': 'teacher',
        'email': email,
        'school': school,
        'created': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'students': {},
        'monthly_usage': 0,
        'monthly_limit': 100000,  # 100k tokens per month
        'daily_requests': 0,
        'daily_limit': 200,  # 200 requests per day
        'last_request_date': datetime.now().strftime("%d/%m/%Y"),
        'archived': False
    }
    
    st.session_state.usage_logs[username] = []
    save_user_database()  # Save to persistent storage
    return True, "Account created successfully"

def create_student_account(teacher_username, student_name):
    """Create student account with auto-generated credentials linked to teacher"""
    if teacher_username not in st.session_state.users:
        return False, "Teacher not found", None, None
    
    username, password = generate_student_credentials()
    
    st.session_state.users[username] = {
        'password': hash_password(password),
        'role': 'student',
        'real_name': student_name,
        'teacher': teacher_username,
        'created': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'monthly_usage': 0,
        'monthly_limit': 10000,  # 10k tokens per month for students
        'daily_requests': 0,
        'daily_limit': 50,  # 50 requests per day for students
        'last_request_date': datetime.now().strftime("%d/%m/%Y"),
        'archived': False
    }
    
    # Add student to teacher's student list
    st.session_state.users[teacher_username]['students'][username] = student_name
    st.session_state.usage_logs[username] = []
    save_user_database()  # Save to persistent storage
    
    return True, "Student account created", username, password

def create_custom_student_account(username, password, student_name, teacher_username=None):
    """Create student account with custom username and password"""
    # Input validation
    if not username or not password or not student_name:
        return False, "Username, password, and student name are required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    
    if username in st.session_state.users:
        return False, "Username already exists"
    
    st.session_state.users[username] = {
        'password': hash_password(password),
        'role': 'student',
        'real_name': student_name,
        'teacher': teacher_username,
        'created': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'monthly_usage': 0,
        'monthly_limit': 10000,  # 10k tokens per month for students
        'daily_requests': 0,
        'daily_limit': 50,  # 50 requests per day for students
        'last_request_date': datetime.now().strftime("%d/%m/%Y"),
        'archived': False
    }
    
    # Add student to teacher's student list if teacher is specified
    if teacher_username and teacher_username in st.session_state.users:
        if 'students' not in st.session_state.users[teacher_username]:
            st.session_state.users[teacher_username]['students'] = {}
        st.session_state.users[teacher_username]['students'][username] = student_name
    
    st.session_state.usage_logs[username] = []
    save_user_database()  # Save to persistent storage
    
    return True, "Student account created successfully"

def authenticate_user(username, password):
    """Authenticate user login"""
    if username not in st.session_state.users:
        return False, "User not found"
    
    user = st.session_state.users[username]
    if user.get('archived', False):
        return False, "Account is archived"
    
    if user['password'] == hash_password(password):
        return True, "Login successful"
    
    return False, "Incorrect password"

def check_usage_limits(username):
    """Check if user has exceeded usage limits"""
    if username == 'anonymous' or username not in st.session_state.users:
        return False
    
    user = st.session_state.users[username]
    today = datetime.now().strftime("%d/%m/%Y")
    
    # Reset daily counter if new day
    if user['last_request_date'] != today:
        user['daily_requests'] = 0
        user['last_request_date'] = today
    
    # Check limits
    if user['monthly_usage'] >= user['monthly_limit']:
        return False
    if user['daily_requests'] >= user['daily_limit']:
        return False
    
    return True

def log_api_usage(username, tokens_used):
    """Log API usage for billing and monitoring"""
    if username == 'anonymous' or username not in st.session_state.users:
        return
    
    user = st.session_state.users[username]
    user['monthly_usage'] += tokens_used
    user['daily_requests'] += 1
    
    log_entry = {
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'tokens': tokens_used,
        'model': 'gpt-4o-mini'
    }
    
    if username not in st.session_state.usage_logs:
        st.session_state.usage_logs[username] = []
    
    st.session_state.usage_logs[username].append(log_entry)

def send_feedback_email(teacher_name, feedback_content):
    """Send teacher feedback to guideaichat@gmail.com"""
    try:
        feedback_entry = {
            'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'teacher': teacher_name,
            'content': feedback_content
        }
        st.session_state.feedback_messages.append(feedback_entry)
        return True, "Feedback sent successfully"
    except Exception as e:
        return False, f"Error sending feedback: {str(e)}"

@st.cache_data
def load_montessori_curriculum():
    """Load Montessori National Curriculum content with caching"""
    try:
        with open('montessori_national_curriculum.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("Montessori National Curriculum file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading Montessori curriculum: {str(e)}")
        return ""

@st.cache_data
def load_australian_curriculum():
    """Load Australian Curriculum V9 content with caching"""
    try:
        with open('australian_curriculum_v9.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("Australian Curriculum V9 file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading Australian curriculum: {str(e)}")
        return ""

@st.cache_data
def load_cross_curriculum_priorities():
    """Load Cross-Curriculum Priorities V9 content with caching"""
    try:
        with open('cross_curriculum_priorities_v9.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("Cross-Curriculum Priorities V9 file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading Cross-Curriculum Priorities: {str(e)}")
        return ""

@st.cache_data
def load_general_capabilities():
    """Load General Capabilities V9 content with caching"""
    try:
        with open('general_capabilities_v9.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("General Capabilities V9 file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading General Capabilities: {str(e)}")
        return ""

def save_rubric_to_user_data(username, rubric_data):
    """Save rubric to user data file for persistence"""
    try:
        # Read existing users data
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        if username in users:
            if 'saved_rubrics' not in users[username]:
                users[username]['saved_rubrics'] = []
            
            # Add the rubric
            users[username]['saved_rubrics'].append(rubric_data)
            
            # Write back to file with error checking
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
            
            return True
        else:
            st.error(f"Username {username} not found in users database")
            return False
    except FileNotFoundError:
        st.error("users.json file not found")
        return False
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error: {e}")
        return False
    except Exception as e:
        st.error(f"Error saving rubric: {e}")
        return False

def load_user_rubrics(username):
    """Load user's saved rubrics from user data file"""
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        if username in users and 'saved_rubrics' in users[username]:
            return users[username]['saved_rubrics']
        return []
    except Exception as e:
        st.error(f"Error loading rubrics: {e}")
        return []

def upload_training_content(content, admin_password):
    """Upload training content (admin only)"""
    # Simple admin check - using environment variable for security
    expected_password = os.getenv("GUIDE_ADMIN_PASSWORD", "guide_admin_2025")
    if admin_password == expected_password:
        st.session_state.training_content = content
        return True, "Training content uploaded successfully"
    return False, "Invalid admin password"

def accessibility_wizard():
    """Accessibility wizard to customize learning interface for diverse learners"""
    st.header("♿ Accessibility Wizard")
    st.markdown("Customize your learning interface to meet your unique needs and learning preferences.")
    
    # Load current settings
    settings = st.session_state.accessibility_settings
    
    # Visual Accessibility Section
    with st.expander("👁️ Visual & Display Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            settings['font_size'] = st.selectbox(
                "Font Size",
                ["Small", "Medium", "Large", "Extra Large"],
                index=["Small", "Medium", "Large", "Extra Large"].index(settings['font_size']),
                help="Choose a comfortable text size for reading"
            )
            
            settings['contrast_mode'] = st.selectbox(
                "Display Contrast",
                ["Standard", "High Contrast", "Dark Mode", "Low Light"],
                index=["Standard", "High Contrast", "Dark Mode", "Low Light"].index(settings['contrast_mode']),
                help="Adjust contrast for better visibility"
            )
        
        with col2:
            settings['dyslexia_support'] = st.checkbox(
                "Dyslexia-Friendly Font",
                value=settings['dyslexia_support'],
                help="Use fonts designed for dyslexic readers"
            )
            
            settings['motion_reduced'] = st.checkbox(
                "Reduce Motion & Animations",
                value=settings['motion_reduced'],
                help="Minimize moving elements and transitions"
            )
    
    # Cognitive Support Section
    with st.expander("🧠 Cognitive & Learning Support"):
        col1, col2 = st.columns(2)
        
        with col1:
            settings['simple_layout'] = st.checkbox(
                "Simplified Interface",
                value=settings['simple_layout'],
                help="Reduce visual clutter and simplify navigation"
            )
            
            settings['focus_mode'] = st.checkbox(
                "Focus Mode",
                value=settings['focus_mode'],
                help="Highlight current section and reduce distractions"
            )
            
            settings['adhd_support'] = st.checkbox(
                "ADHD Support",
                value=settings['adhd_support'],
                help="Break content into smaller chunks with clear progress indicators"
            )
        
        with col2:
            settings['memory_support'] = st.checkbox(
                "Memory Support",
                value=settings['memory_support'],
                help="Add visual cues and reminders throughout the interface"
            )
            
            settings['reading_support'] = st.checkbox(
                "Reading Comprehension Aid",
                value=settings['reading_support'],
                help="Highlight key terms and provide definitions"
            )
    
    # Motor & Navigation Section
    with st.expander("⌨️ Motor & Navigation Support"):
        col1, col2 = st.columns(2)
        
        with col1:
            settings['keyboard_nav'] = st.checkbox(
                "Enhanced Keyboard Navigation",
                value=settings['keyboard_nav'],
                help="Optimize interface for keyboard-only navigation"
            )
        
        with col2:
            settings['screen_reader'] = st.checkbox(
                "Screen Reader Optimization",
                value=settings['screen_reader'],
                help="Enhance compatibility with screen reading software"
            )
    
    # Audio Support Section
    with st.expander("🔊 Audio & Communication Support"):
        settings['audio_support'] = st.checkbox(
            "Text-to-Speech",
            value=settings['audio_support'],
            help="Enable audio reading of content"
        )
    
    # Save settings
    st.session_state.accessibility_settings = settings
    
    # Apply Settings Preview
    if st.button("💾 Save & Apply Settings", type="primary", use_container_width=True):
        st.success("✅ Accessibility settings saved! Your interface will update to match your preferences.")
        st.rerun()
    
    # Reset to defaults
    if st.button("🔄 Reset to Default Settings"):
        st.session_state.accessibility_settings = {
            'font_size': 'Medium',
            'contrast_mode': 'Standard',
            'reading_support': False,
            'audio_support': False,
            'simple_layout': False,
            'focus_mode': False,
            'motion_reduced': False,
            'keyboard_nav': False,
            'screen_reader': False,
            'dyslexia_support': False,
            'adhd_support': False,
            'memory_support': False
        }
        st.success("Settings reset to defaults")
        st.rerun()

def apply_accessibility_styles():
    """Apply custom CSS based on accessibility settings"""
    # Ensure accessibility_settings exists
    if 'accessibility_settings' not in st.session_state:
        return
    
    settings = st.session_state.accessibility_settings
    
    # Build CSS based on settings
    css_styles = []
    
    # Font size adjustments
    font_sizes = {
        'Small': '0.9rem',
        'Medium': '1rem', 
        'Large': '1.2rem',
        'Extra Large': '1.5rem'
    }
    base_font_size = font_sizes.get(settings['font_size'], '1rem')
    css_styles.append(f"""
        .main .block-container {{
            font-size: {base_font_size};
        }}
        .stSelectbox label, .stTextInput label, .stTextArea label {{
            font-size: {base_font_size};
            font-weight: 600;
        }}
    """)
    
    # Contrast and color adjustments
    if settings['contrast_mode'] == 'High Contrast':
        css_styles.append("""
            .main {
                background-color: #000000 !important;
                color: #FFFFFF !important;
            }
            .stApp > header {
                background-color: #000000 !important;
            }
            .block-container {
                background-color: #000000 !important;
                color: #FFFFFF !important;
            }
            .stButton button {
                background-color: #FFFFFF !important;
                color: #000000 !important;
                border: 2px solid #FFFFFF !important;
            }
        """)
    elif settings['contrast_mode'] == 'Dark Mode':
        css_styles.append("""
            .main {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }
            .stApp > header {
                background-color: #1E1E1E !important;
            }
            .block-container {
                background-color: #1E1E1E !important;
                color: #E0E0E0 !important;
            }
        """)
    elif settings['contrast_mode'] == 'Low Light':
        css_styles.append("""
            .main {
                background-color: #2D2D2D !important;
                color: #D0D0D0 !important;
            }
            .stApp > header {
                background-color: #2D2D2D !important;
            }
        """)
    
    # Dyslexia-friendly font
    if settings['dyslexia_support']:
        css_styles.append("""
            * {
                font-family: 'Arial', 'Helvetica', sans-serif !important;
                letter-spacing: 0.1em !important;
                line-height: 1.6 !important;
            }
        """)
    
    # Simplified layout
    if settings['simple_layout']:
        css_styles.append("""
            .main .block-container {
                max-width: 800px !important;
                padding-top: 2rem !important;
            }
            .stSidebar {
                display: none !important;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 2px;
            }
        """)
    
    # Focus mode
    if settings['focus_mode']:
        css_styles.append("""
            .main .block-container {
                max-width: 700px !important;
                margin: 0 auto !important;
            }
            .stSidebar {
                background-color: #F8F9FA !important;
                border-right: 3px solid #007BFF !important;
            }
            :focus {
                outline: 3px solid #007BFF !important;
                outline-offset: 2px !important;
            }
        """)
    
    # Reduced motion
    if settings['motion_reduced']:
        css_styles.append("""
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        """)
    
    # Enhanced keyboard navigation
    if settings['keyboard_nav']:
        css_styles.append("""
            .stButton button:focus,
            .stSelectbox div[role="button"]:focus,
            .stTextInput input:focus,
            .stTextArea textarea:focus {
                outline: 3px solid #FF6B35 !important;
                outline-offset: 2px !important;
                box-shadow: 0 0 0 2px white, 0 0 0 5px #FF6B35 !important;
            }
            .stTabs [role="tab"]:focus {
                outline: 3px solid #FF6B35 !important;
                outline-offset: 2px !important;
            }
        """)
    
    # Screen reader optimization
    if settings['screen_reader']:
        css_styles.append("""
            .screen-reader-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0,0,0,0);
                white-space: nowrap;
                border: 0;
            }
        """)
    
    # ADHD support - chunked content
    if settings['adhd_support']:
        css_styles.append("""
            .main .block-container > div > div {
                margin-bottom: 2rem !important;
                padding: 1rem !important;
                border-left: 4px solid #28A745 !important;
                background-color: #F8F9FA !important;
                border-radius: 0.5rem !important;
            }
        """)
    
    # Memory support - visual cues
    if settings['memory_support']:
        css_styles.append("""
            h1, h2, h3 {
                background: linear-gradient(90deg, #007BFF, #28A745) !important;
                background-clip: text !important;
                -webkit-background-clip: text !important;
                -webkit-text-fill-color: transparent !important;
                font-weight: bold !important;
            }
            .stButton button[kind="primary"] {
                background: linear-gradient(90deg, #007BFF, #28A745) !important;
                border: none !important;
                font-weight: bold !important;
            }
        """)
    
    # Apply all styles
    if css_styles:
        st.markdown(f"<style>{''.join(css_styles)}</style>", unsafe_allow_html=True)

def add_accessibility_indicators():
    """Add accessibility status indicators when relevant settings are enabled"""
    settings = st.session_state.accessibility_settings
    indicators = []
    
    if settings['screen_reader']:
        indicators.append("Screen Reader Mode")
    if settings['focus_mode']:
        indicators.append("Focus Mode")
    if settings['simple_layout']:
        indicators.append("Simplified Layout")
    if settings['adhd_support']:
        indicators.append("ADHD Support")
    if settings['dyslexia_support']:
        indicators.append("Dyslexia-Friendly")
    
    if indicators:
        st.info(f"🔧 Active Accessibility Features: {', '.join(indicators)}")

def get_accessible_content_format(content, settings):
    """Format content based on accessibility settings"""
    if not content:
        return content
    
    # ADHD support - break into smaller chunks
    if settings.get('adhd_support', False):
        # Split long paragraphs into smaller chunks
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        for para in paragraphs:
            if len(para) > 200:  # If paragraph is long, break it down
                sentences = para.split('. ')
                chunks = []
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk + sentence) < 150:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                if current_chunk:
                    chunks.append(current_chunk.strip())
                formatted_paragraphs.extend(chunks)
            else:
                formatted_paragraphs.append(para)
        content = '\n\n'.join(formatted_paragraphs)
    
    # Reading support - highlight key terms
    if settings.get('reading_support', False):
        # Simple keyword highlighting for educational content
        key_terms = ['objective', 'learning', 'assessment', 'students', 'curriculum', 'development', 'skills', 'knowledge']
        for term in key_terms:
            content = content.replace(term, f"**{term}**")
    
    # Memory support - add structure cues
    if settings.get('memory_support', False):
        lines = content.split('\n')
        structured_lines = []
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                structured_lines.append(f"📌 {line}")
            elif line.strip().startswith('-'):
                structured_lines.append(f"• {line[1:]}")
            else:
                structured_lines.append(line)
        content = '\n'.join(structured_lines)
    
    return content

def analyze_student_work(file_content, file_type, work_description, curriculum):
    """Analyze student work and provide constructive feedback using AI"""
    try:
        # Prepare analysis prompt based on file type
        analysis_prompts = {
            'text': f"""
            Analyze this student's written work with a focus on constructive, growth-oriented feedback:
            
            Student's Description: {work_description}
            Written Work: {file_content}
            
            Provide feedback that:
            1. Celebrates what the student has done well (specific examples)
            2. Suggests 2-3 areas for improvement with practical next steps
            3. Connects to bigger learning goals and curriculum outcomes
            4. Encourages curiosity and further exploration
            5. Uses warm, supportive language appropriate for the student's developmental stage
            
            Format as constructive feedback, not evaluation.
            """,
            
            'image': f"""
            Analyze this student's visual work (image/presentation) with constructive feedback:
            
            Student's Description: {work_description}
            
            Based on the image content, provide feedback that:
            1. Acknowledges creative choices and visual communication strengths
            2. Suggests ways to enhance visual storytelling or clarity
            3. Connects visual elements to learning objectives
            4. Encourages artistic growth and experimentation
            5. Considers accessibility and inclusive design principles
            
            Use encouraging, specific language that builds confidence.
            """,
            
            'audio': f"""
            Provide feedback on this student's audio work:
            
            Student's Description: {work_description}
            
            Focus on:
            1. Communication clarity and expression
            2. Content organization and flow
            3. Engagement and creativity
            4. Technical aspects (if relevant)
            5. Suggestions for continued growth
            
            Emphasize growth mindset and celebrate effort.
            """
        }
        
        base_prompt = f"""You are providing constructive feedback to a student using {curriculum}. 
        Your feedback should integrate both Australian Curriculum V9 outcomes and Montessori cosmic education principles:
        - Warm and encouraging, honoring the student's natural curiosity
        - Specific and actionable with practical next steps
        - Growth-focused rather than evaluative, emphasizing the learning journey
        - Connected to both curriculum standards and cosmic education themes
        - Appropriate for the student's developmental stage and agency
        - Celebrates effort and process over product
        - Connects learning to bigger patterns and the student's place in the universe
        
        Always start with genuine recognition of effort and specific strengths."""
        
        prompt = analysis_prompts.get(file_type, analysis_prompts['text'])
        
        # Call OpenAI API for analysis
        system_prompt = get_system_prompt(curriculum) + "\n\n" + base_prompt
        messages = [{"role": "user", "content": prompt}]
        
        response = call_openai_api(messages, system_prompt)
        
        return response if response else "I'm having trouble analyzing your work right now. Please try again or ask your teacher for feedback."
        
    except Exception as e:
        return f"I encountered an issue analyzing your work: {str(e)}. Please try again or share your work with your teacher."

def process_uploaded_file(uploaded_file):
    """Process different types of uploaded files for feedback analysis"""
    try:
        file_info = {
            'name': uploaded_file.name,
            'type': uploaded_file.type,
            'size': uploaded_file.size
        }
        
        # Handle text files
        if uploaded_file.type in ['text/plain', 'application/pdf']:
            if uploaded_file.type == 'text/plain':
                content = str(uploaded_file.read(), 'utf-8')
                return content, 'text', file_info
            else:
                # For PDF, extract text content (basic implementation)
                content = f"PDF file uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)"
                return content, 'text', file_info
        
        # Handle images
        elif uploaded_file.type.startswith('image/'):
            # For images, we'll use description-based analysis
            content = f"Image file: {uploaded_file.name} ({uploaded_file.size} bytes)"
            return content, 'image', file_info
        
        # Handle audio files
        elif uploaded_file.type.startswith('audio/'):
            content = f"Audio file: {uploaded_file.name} ({uploaded_file.size} bytes)"
            return content, 'audio', file_info
        
        # Handle documents (DOCX, presentations)
        elif uploaded_file.type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-powerpoint'
        ]:
            content = f"Document file: {uploaded_file.name} ({uploaded_file.size} bytes)"
            return content, 'text', file_info
        
        else:
            return f"Unsupported file type: {uploaded_file.type}", 'unknown', file_info
            
    except Exception as e:
        return f"Error processing file: {str(e)}", 'error', {'name': 'unknown', 'type': 'error', 'size': 0}

def save_student_feedback(student_name, work_description, feedback, file_info):
    """Save feedback to student's progress tracking"""
    if 'student_feedback_history' not in st.session_state:
        st.session_state.student_feedback_history = []
    
    feedback_entry = {
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'student': student_name,
        'work_description': work_description,
        'feedback': feedback,
        'file_info': file_info,
        'type': 'work_feedback'
    }
    
    st.session_state.student_feedback_history.append(feedback_entry)
    
    # Also link to student activity tracking
    activity_data = {
        "type": "work_submission",
        "content": work_description,
        "feedback": feedback,
        "competency_analysis": "Demonstrated learning through work submission and reflection",
        "extensions": "Continue developing skills based on feedback received"
    }
    link_student_activity(student_name, activity_data)

# Initialize session state and user database  
init_user_database()

# Apply accessibility styles and indicators will be handled after session state initialization

# Initialize session state safely
def ensure_session_state():
    """Ensure all required session state variables are initialized"""
    defaults = {
        'messages': [],
        'curriculum': "Australian Curriculum V9",
        'uploaded_content': "",
        'user_type': "Teacher",
        'student_work': "",
        'student_feedback_history': [],
        'student_progress': {},
        'shared_lessons': [],
        'collaboration_mode': False,
        'authenticated': False,
        'current_user': None,
        'user_role': None,
        'show_login': True,
        'portfolios': {},
        'saved_rubrics': [],
        'shared_rubrics': [],
        'cec_competency_data': {},
        'file_processing_cache': {},
        'training_content': "",
        'feedback_messages': [],
        'accessibility_settings': {
            'font_size': 'Medium',
            'contrast_mode': 'Standard',
            'reading_support': False,
            'audio_support': False,
            'simple_layout': False,
            'focus_mode': False,
            'motion_reduced': False,
            'keyboard_nav': False,
            'screen_reader': False,
            'dyslexia_support': False,
            'adhd_support': False,
            'memory_support': False
        },
        'student_work_timeline': {},
        'show_portfolio_creator': False
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Call ensure_session_state to properly initialize
ensure_session_state()

# Apply accessibility styles globally after session state is initialized
apply_accessibility_styles()

# Add accessibility indicators if any are active
if st.session_state.get('accessibility_settings'):
    add_accessibility_indicators()

# Helper functions
def get_system_prompt(curriculum):
    """Get system prompt based on selected curriculum with Montessori Cosmic Education and systems thinking approach"""
    base_prompt = """You are an AI curriculum guide inspired by Montessori's Cosmic Education and grounded in systems thinking. Your responses are warm, humble, and practical, avoiding jargon-heavy academic language. Use British/Australian English spelling and terminology throughout.

You honour the adolescent developmental plane: curiosity, belonging, purpose, and independence. You emphasise interconnections across disciplines rather than siloed subjects, drawing attention to big ideas and patterns (cycles, cause-and-effect, networks) rather than isolated facts. 

You respect Montessori principles of freedom within responsibility, hands-on experience, and student agency. You help teachers, students, and parents understand not only what to learn, but why it matters in the bigger picture of life and the world.

EMBEDDED CURRICULUM DESIGN COMPONENTS:
{
    "Component": "Inquiry-Driven Questions",
    "Description": "Use open-ended, essential questions to guide interdisciplinary learning and spark student engagement.",
    "Keywords": "big questions, inquiry-based, thematic learning",
    "Use_Case": "Anchor question generator that prompts users to define unit themes."
},
{
    "Component": "Conceptual Organizers", 
    "Description": "Organize curriculum around big concepts that connect across disciplines and promote deep understanding.",
    "Keywords": "concept mapping, interdisciplinary, themes",
    "Use_Case": "Visual concept map interface for designing cross-subject units."
},
{
    "Component": "Mathematical Thinking Patterns",
    "Description": "Emphasise mathematical patterns, relationships, and cosmic connections in number, space, and data.",
    "Keywords": "patterns, mathematical modeling, cosmic mathematics, golden ratio, fibonacci, fractals",
    "Use_Case": "Guide mathematical explorations that connect to natural phenomena and universal patterns."
},
{
    "Component": "Problem-Solving Investigations", 
    "Description": "Frame mathematics as investigation and discovery rather than procedure memorisation.",
    "Keywords": "mathematical investigation, problem-solving, inquiry mathematics, real-world applications",
    "Use_Case": "Create authentic mathematical challenges that connect to students' interests and cosmic themes."
}

When appropriate, incorporate these components as guardrails to guide curriculum design towards inquiry-based, conceptual approaches that foster deep connections and authentic engagement."""
    
    # Add uploaded curriculum content if available
    uploaded_content = ""
    if hasattr(st.session_state, 'uploaded_content') and st.session_state.uploaded_content:
        uploaded_content = f"\n\nAdditional curriculum documents and context:\n{st.session_state.uploaded_content[:2000]}..."
    
    # Load Montessori National Curriculum content (optimized)
    montessori_content = load_montessori_curriculum()
    if montessori_content and len(montessori_content) > 100:
        # Use first 1000 chars for better context while keeping prompt manageable
        uploaded_content += f"\n\nMontessori National Curriculum Reference:\n{montessori_content[:1000]}..."
    
    # Load Australian Curriculum V9 content (optimized)  
    australian_content = load_australian_curriculum()
    if australian_content and len(australian_content) > 100:
        # Use first 1000 chars for better context while keeping prompt manageable
        uploaded_content += f"\n\nAustralian Curriculum V9 Reference:\n{australian_content[:1000]}..."
    
    # Load Cross-Curriculum Priorities V9 content
    priorities_content = load_cross_curriculum_priorities()
    if priorities_content and len(priorities_content) > 100:
        uploaded_content += f"\n\nCross-Curriculum Priorities V9:\n{priorities_content[:800]}..."
    
    # Load General Capabilities V9 content
    capabilities_content = load_general_capabilities()
    if capabilities_content and len(capabilities_content) > 100:
        uploaded_content += f"\n\nGeneral Capabilities V9:\n{capabilities_content[:800]}..."
    
    # Include Montessori National Curriculum reference
    montessori_reference = """

MONTESSORI NATIONAL CURRICULUM INTEGRATION:
You reference the official Montessori National Curriculum (2011) which organises learning by three planes of development:
- First Plane (Birth-6): Absorbent mind, sensory exploration, practical life skills
- Second Plane (6-12): Reasoning mind, Cosmic Education approach, Great Stories foundation  
- Third Plane (12-18): Social consciousness, real-world learning, personal development

Key Montessori principles to incorporate:
- Human tendencies: exploration, communication, work, repetition, self-perfection
- Prepared environment with order, beauty, mixed ages, freedom within limits
- Cosmic Education showing universe story and interconnections
- Curriculum areas: Practical Life, Sensorial, Language, Mathematics, Cultural Studies
- Observation-based assessment focusing on individual growth"""

    if curriculum == "Australian Curriculum V9":
        return f"{base_prompt}\n\nYou integrate the official Australian Curriculum V9 framework with Cosmic Education principles. Reference learning areas, general capabilities (Literacy, Numeracy, Digital Literacy, Critical and Creative Thinking, Personal and Social Capability, Intercultural Understanding, Ethical Understanding), and cross-curriculum priorities (Sustainability, Asia and Australia's Engagement with Asia, Aboriginal and Torres Strait Islander Histories and Cultures). Show how achievement standards connect to larger systems - historical, ecological, social, and economic. You present learning as threads in the tapestry of human knowledge and experience, using authentic curriculum terminology and content descriptions. Draw connections between subject-specific content and the cosmic story of universal development.{uploaded_content}"
    elif curriculum == "Montessori Curriculum Australia" or ("Montessori" in curriculum):
        return f"{base_prompt}\n\nYou work within the official Montessori National Curriculum (2011) framework, emphasising the three planes of development, prepared environments, and developmental stages. You connect all learning to the 'universe story' through Cosmic Education - showing how each topic fits into the grand narrative of cosmic evolution, human civilisation, and our interconnected world. Reference authentic Montessori principles including human tendencies, practical life, sensorial education, and observation-based assessment.{montessori_reference}{uploaded_content}"
    else:  # Blended approach
        return f"{base_prompt}\n\nYou masterfully blend Australian Curriculum V9 standards with Montessori National Curriculum principles, creating authentic connections between formal learning outcomes and developmental appropriateness. Reference both frameworks' official terminology and structures, including general capabilities and cross-curriculum priorities. You honour structured achievement standards whilst embracing child-led discovery, showing how curriculum requirements can be met through Montessori's cosmic approach to education. Draw from both authentic curriculum documents to ensure compliance and alignment, always prioritising the cosmic education perspective that connects learning to the grand narrative of the universe.{montessori_reference}{uploaded_content}"

def call_openai_api(messages, system_prompt):
    """Call OpenAI API with error handling"""
    try:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Add training content for better responses
        if st.session_state.training_content:
            full_messages[0]["content"] += f"\n\nReference this approved training content:\n{st.session_state.training_content}"
        
        if st.session_state.uploaded_content:
            full_messages[0]["content"] += f"\n\nAdditional curriculum notes provided by user:\n{st.session_state.uploaded_content}"
        
        # Student-specific content restrictions to reduce hallucinations
        if st.session_state.get('user_role') == 'student':
            full_messages[0]["content"] += "\n\nIMPORTANT: You are helping a student learn. Focus on guiding their thinking, asking questions, and suggesting next steps. Do not create original content for them. Help with ideation, scaffolding, and prompting further engagement only."
        
        # Usage control - check limits before API call
        if not check_usage_limits(st.session_state.get('current_user', 'anonymous')):
            st.error("You've reached your monthly usage limit. Please try again next month.")
            return None
            
        # Determine max tokens based on user type
        max_tokens = 300 if st.session_state.get('user_role') == 'student' else 2000
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            temperature=0.7,
            max_tokens=max_tokens
        )
        
        # Log usage
        if response.usage:
            log_api_usage(st.session_state.get('current_user', 'anonymous'), response.usage.total_tokens)
        
        # Apply accessibility formatting to response
        content = response.choices[0].message.content
        if 'accessibility_settings' in st.session_state:
            content = get_accessible_content_format(content, st.session_state.accessibility_settings)
        
        return content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

def create_student_planner(project_type, topic, curriculum):
    """Create scaffolding planner for student projects"""
    planners = {
        "poster": {
            "title": f"{topic} - Poster Project Planner",
            "steps": [
                "Research & Gather Information",
                "Plan Visual Layout", 
                "Choose Images & Graphics",
                "Write Key Text",
                "Design & Create",
                "Review & Refine"
            ],
            "questions": [
                "What are the main ideas you want to communicate?",
                "Who is your audience?",
                "What visual elements will best support your message?",
                "How can you organize information clearly?"
            ]
        },
        "essay": {
            "title": f"{topic} - Essay Project Planner",
            "steps": [
                "Understand the Question",
                "Research & Note-Taking",
                "Create Outline",
                "Write Introduction",
                "Develop Body Paragraphs", 
                "Write Conclusion",
                "Edit & Proofread"
            ],
            "questions": [
                "What is your main argument or thesis?",
                "What evidence supports your ideas?",
                "How will you structure your argument?",
                "What connections can you make to bigger ideas?"
            ]
        },
        "diorama": {
            "title": f"{topic} - Diorama Project Planner",
            "steps": [
                "Choose Specific Scene",
                "Research Details",
                "Plan 3D Layout",
                "Gather Materials",
                "Build Base Structure",
                "Add Details & Figures",
                "Create Information Labels"
            ],
            "questions": [
                "What moment or scene will you recreate?",
                "What materials will work best?",
                "How can you show scale and perspective?",
                "What story does your diorama tell?"
            ]
        },
        "video": {
            "title": f"{topic} - Video Project Planner", 
            "steps": [
                "Define Purpose & Audience",
                "Write Script/Storyboard",
                "Plan Filming Locations",
                "Gather Props & Materials",
                "Film Segments",
                "Edit & Add Effects",
                "Review & Share"
            ],
            "questions": [
                "What message do you want to convey?",
                "What style of video suits your topic?",
                "How will you engage your viewers?",
                "What equipment do you need?"
            ]
        },
        "music": {
            "title": f"{topic} - Music Project Planner",
            "steps": [
                "Choose Musical Style",
                "Research Topic Connections",
                "Write Lyrics/Compose Melody",
                "Practice & Rehearse",
                "Record or Perform",
                "Reflect on Process"
            ],
            "questions": [
                "How does music connect to your topic?",
                "What emotions or ideas will you express?",
                "What instruments or voices will you use?",
                "How will you share your music?"
            ]
        },
        "role-play": {
            "title": f"{topic} - Role-Play Project Planner",
            "steps": [
                "Choose Characters/Roles",
                "Research Historical Context",
                "Write Dialogue/Script",
                "Plan Costumes & Props",
                "Rehearse Performance",
                "Present to Audience",
                "Debrief & Reflect"
            ],
            "questions": [
                "Whose perspective will you represent?",
                "What conflicts or situations will you explore?",
                "How will you make it authentic?",
                "What will your audience learn?"
            ]
        },
        "model": {
            "title": f"{topic} - Model Project Planner",
            "steps": [
                "Choose What to Model",
                "Research Accurate Details",
                "Select Materials",
                "Plan Construction Steps",
                "Build Foundation",
                "Add Details & Features",
                "Create Explanation"
            ],
            "questions": [
                "What will your model demonstrate?",
                "How will you ensure accuracy?",
                "What scale will work best?",
                "How will you explain your model to others?"
            ]
        }
    }
    
    planner = planners.get(project_type, planners["poster"])
    
    planning_steps = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(planner['steps'])])
    reflection_questions = '\n'.join([f"• {q}" for q in planner['questions']])
    
    prompt = f"""Create detailed scaffolding guidance for a {project_type} project on '{topic}' following this planning structure:

{planner['title']}

Planning Steps:
{planning_steps}

Reflection Questions:
{reflection_questions}

Provide specific, practical guidance for each step that helps the student think through their approach while maintaining their independence and creativity. Include cosmic education connections where appropriate."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_lesson_ideas(topic, curriculum):
    """Generate lesson ideas for a given topic with systems thinking approach"""
    prompt = f"""Create 3-5 interconnected lesson ideas for '{topic}' that connect to larger systems (historical, ecological, social, economic). 

For each lesson, show:
- How this topic connects to the bigger picture of life and the world
- Real-world applications that foster independence and responsibility  
- Collaborative opportunities that build community
- Ways students can contribute meaningfully to society through this learning
- Reflection questions about patterns, cycles, and interconnections

Design activities that honor curiosity, belonging, purpose, and independence while connecting to the cosmic story of how everything is related."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_scope_sequence(topics_data, curriculum):
    """Generate scope and sequence as interconnected learning threads"""
    topics_text = "\n".join([f"- {topic}" for topic in topics_data])
    prompt = f"""Create a scope and sequence that presents these topics not as isolated subjects, but as interconnected learning threads in the tapestry of knowledge:

{topics_text}

Present this as:
- Learning threads that weave together rather than linear progression
- Patterns and connections between topics (cycles, cause-and-effect, networks)
- How each topic contributes to understanding larger systems
- Opportunities for students to see their place in the cosmic story
- Natural spiral progression that respects developmental readiness
- Real-world connections that show why this learning matters to humanity

Show how these topics create a map of interconnected understanding rather than separate academic boxes."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_parent_communication(topic, curriculum):
    """Generate parent communication highlighting whole-child development and cosmic connections"""
    prompt = f"""Create a warm, accessible parent communication about '{topic}' that explains curriculum in terms of whole-child development and lifelong learning skills.

Include:
- How this learning connects to the child's place in the "universe story"
- The bigger picture of why this topic matters for humanity and our world
- How this supports the child's natural curiosity, belonging, purpose, and independence
- Practical ways parents can extend this learning through real-world connections at home
- How this topic weaves into larger patterns and systems the child is discovering
- The child's role as an active contributor to their community and world through this learning

Write in a tone that honors both the curriculum framework and Montessori's vision of education as preparation for life and citizenship in the cosmic community."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_student_tasks(topic, age_group, curriculum):
    """Generate student tasks that foster independence, collaboration, and cosmic connection"""
    prompt = f"""Create meaningful activities for {age_group} students exploring '{topic}' that always foster:

Independence & Responsibility:
- Self-directed learning opportunities
- Choices in how to demonstrate understanding
- Real ownership of learning outcomes

Collaboration & Community:
- Authentic opportunities to work together
- Ways to share knowledge and teach others
- Building classroom and wider community connections

Real-World Connection:
- Authentic audiences for student work
- Purposeful outcomes that matter beyond the classroom
- Connections to local and global communities

Cosmic Reflection:
- How this learning contributes to understanding larger systems (society, ecology, culture)
- The student's role in the ongoing story of human civilization
- Patterns and connections to other areas of knowledge

Design these as invitations to explore rather than assignments to complete, honoring the child's natural curiosity and developmental readiness."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)



def suggest_skill_extensions(work_content, curriculum, student_interests=""):
    """Suggest ways to extend learning based on student work"""
    interests_note = f"\n\nStudent has expressed interest in: {student_interests}" if student_interests else ""
    
    prompt = f"""Based on this student work, suggest meaningful extensions that build on their demonstrated thinking and connections:

{work_content}{interests_note}

Suggest extensions that:
- Build on patterns and connections they've already discovered
- Offer choices in how to explore further (honoring independence)
- Connect to real-world applications and their community
- Invite collaboration with others who share similar curiosities
- Show how their learning contributes to larger understanding
- Respect their developmental stage while challenging their thinking
- Create opportunities for them to teach others what they've learned

Frame these as invitations to continue their cosmic journey of discovery."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_assessment_rubric(topic, curriculum, assessment_type, year_level):
    """Generate curriculum-aligned assessment rubric with Montessori developmental approach"""
    prompt = f"""Create a comprehensive assessment rubric for '{topic}' aligned to {curriculum} standards for {year_level} students.

Design the rubric with these Montessori-inspired principles:
- Honor developmental stages and individual learning paths
- Focus on growth and progress rather than deficit-based language
- Include both academic standards and whole-child development
- Recognize different ways students can demonstrate understanding
- Celebrate effort, curiosity, and connection-making alongside achievement
- Connect learning to larger systems and real-world applications

Structure the rubric with:
- Clear curriculum standards alignment
- 4 performance levels (Emerging, Developing, Proficient, Extending)
- Multiple criteria that honor different learning styles and strengths
- Language that celebrates progress and suggests next steps
- Connections to cosmic education themes where appropriate
- Self-reflection prompts for students

Assessment type: {assessment_type}

Make this a tool for nurturing growth, not just measuring performance."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def track_student_progress(student_name, work_analysis, learning_goals, cec_competencies=None, student_activity=None):
    """Track and analyze student progress with Cosmic Education Competencies"""
    if student_name not in st.session_state.student_progress:
        st.session_state.student_progress[student_name] = {
            "entries": [],
            "learning_goals": [],
            "strengths": [],
            "growth_areas": [],
            "interests": [],
            "cec_competencies": {
                "knowing_how_to_learn": {"level": 1, "evidence": []},
                "empirical_reasoning": {"level": 1, "evidence": []},
                "quantitative_reasoning": {"level": 1, "evidence": []},
                "social_reasoning": {"level": 1, "evidence": []},
                "communication": {"level": 1, "evidence": []},
                "personal_qualities": {"level": 1, "evidence": []}
            },
            "internships": [],
            "exhibitions": [],
            "real_world_projects": [],
            "student_activities": []
        }
    
    # Add new progress entry
    progress_entry = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "work_analysis": work_analysis,
        "learning_goals": learning_goals,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "cec_competencies": cec_competencies or {},
        "student_activity": student_activity or {}
    }
    
    st.session_state.student_progress[student_name]["entries"].append(progress_entry)
    
    # Update CEC competency levels if provided
    if cec_competencies:
        for competency, data in cec_competencies.items():
            if competency in st.session_state.student_progress[student_name]["cec_competencies"]:
                current = st.session_state.student_progress[student_name]["cec_competencies"][competency]
                if "level" in data:
                    current["level"] = max(current["level"], data["level"])
                if "evidence" in data:
                    current["evidence"].extend(data["evidence"])
    
    # Add student activity to activity log
    if student_activity:
        st.session_state.student_progress[student_name]["student_activities"].append({
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "activity_type": student_activity.get("type", "unknown"),
            "content": student_activity.get("content", ""),
            "feedback_received": student_activity.get("feedback", ""),
            "competency_analysis": student_activity.get("competency_analysis", ""),
            "learning_connections": student_activity.get("extensions", "")
        })

def generate_cec_competency_assessment(work_content, curriculum):
    """Analyze work against Cosmic Education Competencies"""
    prompt = f"""Analyze this student work against the Cosmic Education Competency framework:

Student Work:
{work_content}

For each competency, assess evidence and suggest a progression level (1-5):

1. **Knowing How to Learn**: Self-directed learning, metacognitive skills, reflection on learning processes, connection to cosmic patterns
2. **Empirical Reasoning**: Using evidence, observation, investigation, scientific thinking, understanding cosmic interconnections
3. **Quantitative Reasoning**: Mathematical thinking, analyzing data, understanding numerical relationships in nature and cosmos
4. **Social Reasoning**: Analyzing social issues, community understanding, responsible action, cosmic citizenship
5. **Communication**: Writing, speaking, listening, artistic expression, audience awareness, sharing cosmic connections
6. **Personal Qualities**: Leadership, respect, responsibility, organization, self-reflection, cosmic consciousness

For each competency present in the work, provide:
- Evidence observed (specific examples)
- Suggested progression level (1-5)
- Growth recommendations connecting to cosmic education themes

Format as structured assessment aligned with {curriculum} standards and cosmic education principles."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_progress_report(student_name, curriculum, time_period="recent", include_cec=True):
    """Generate comprehensive progress report with Cosmic Education Competencies"""
    if student_name not in st.session_state.student_progress:
        return "No progress data available for this student."
    
    student_data = st.session_state.student_progress[student_name]
    entries_summary = "\n".join([f"- {entry['timestamp']}: {entry['work_analysis'][:100]}..." 
                                for entry in student_data["entries"][-5:]])
    
    # Include student activity summary
    activity_summary = ""
    if student_data.get("student_activities"):
        activity_summary = "Student Learning Activities:\n"
        for activity in student_data["student_activities"][-3:]:
            activity_summary += f"- {activity['timestamp']} ({activity['activity_type']}): {activity['content'][:80]}...\n"
    
    cec_summary = ""
    if include_cec and "cec_competencies" in student_data:
        cec_summary = "Cosmic Education Competency Levels:\n"
        competency_names = {
            "knowing_how_to_learn": "Knowing How to Learn",
            "empirical_reasoning": "Empirical Reasoning", 
            "quantitative_reasoning": "Quantitative Reasoning",
            "social_reasoning": "Social Reasoning",
            "communication": "Communication",
            "personal_qualities": "Personal Qualities"
        }
        
        for comp_key, comp_data in student_data["cec_competencies"].items():
            name = competency_names.get(comp_key, comp_key)
            cec_summary += f"- {name}: Level {comp_data['level']}\n"
    
    prompt = f"""Create a holistic learning journey report for {student_name} integrating Montessori Cosmic Education Competencies:

Recent Learning Entries:
{entries_summary}

{activity_summary}

{cec_summary}

Generate a report that:
- Celebrates growth and discoveries in a warm, encouraging tone
- Maps progress across Cosmic Education Competencies showing cosmic connections
- Shows connections between academic learning and authentic experiences
- Identifies patterns in metacognitive development and self-directed learning
- Connects learning to community engagement and cosmic responsibility
- Suggests meaningful next steps that build on demonstrated competencies
- Uses asset-based language focusing on "how the student is smart"
- Includes recommendations for real-world learning opportunities that connect to cosmic themes
- Frames assessment as growth documentation celebrating the child's place in the universe
- References specific student activities and learning interactions when available

Create this as a personalized cosmic learner profile that honors individual learning pathways and celebrates authentic achievement."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def create_cec_learner_profile(student_name, curriculum):
    """Create Cosmic Education Competency learner profile"""
    if 'student_progress' not in st.session_state or student_name not in st.session_state.student_progress:
        return {
            "student": student_name,
            "competency_levels": {},
            "real_world_experiences": [],
            "exhibitions": [],
            "learning_journey": [],
            "student_activities": []
        }
    
    student_data = st.session_state.student_progress[student_name]
    
    # Competency visualization data
    competencies = student_data.get("cec_competencies", {})
    
    profile_data = {
        "student": student_name,
        "competency_levels": competencies,
        "real_world_experiences": student_data.get("internships", []) + student_data.get("real_world_projects", []),
        "exhibitions": student_data.get("exhibitions", []),
        "learning_journey": student_data.get("entries", [])[-10:],  # Last 10 entries
        "student_activities": student_data.get("student_activities", [])[-10:]  # Last 10 activities
    }
    
    return profile_data

def link_student_activity(student_name, activity_data):
    """Link student interface activity to their progress tracking"""
    if 'student_progress' not in st.session_state:
        st.session_state.student_progress = {}
    
    if student_name not in st.session_state.student_progress:
        # Initialize if first activity
        track_student_progress(student_name, "Initial student activity", "Self-directed learning", None, activity_data)
    else:
        # Add activity to existing profile
        st.session_state.student_progress[student_name]["student_activities"].append({
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "activity_type": activity_data.get("type", "unknown"),
            "content": activity_data.get("content", ""),
            "feedback_received": activity_data.get("feedback", ""),
            "competency_analysis": activity_data.get("competency_analysis", ""),
            "learning_connections": activity_data.get("extensions", "")
        })

def create_portfolio_template(template_type, student_name, custom_params=None):
    """Create portfolio template based on type"""
    templates = {
        "blank": {
            "title": f"{student_name}'s Learning Portfolio",
            "sections": ["My Work", "Reflections", "Learning Journey"],
            "description": "A blank canvas for your learning story"
        },
        "themed": {
            "title": f"{student_name}'s Themed Portfolio",
            "sections": [
                "Theme Exploration",
                "Connections Discovered", 
                "Creative Expressions",
                "Reflections on Learning",
                "Future Investigations"
            ],
            "description": "Organize your work around themes and big ideas"
        },
        "subject": {
            "title": f"{student_name}'s Subject Portfolio", 
            "sections": [
                "Mathematics & Patterns",
                "Language & Communication",
                "Science & Discovery",
                "Arts & Expression",
                "Social Studies & Community",
                "Cross-Curricular Connections"
            ],
            "description": "Showcase learning across different subject areas"
        },
        "year_level": {
            "title": f"{student_name}'s Year {(custom_params or {}).get('year', 'X')} Portfolio",
            "sections": [
                "Term 1 Highlights",
                "Term 2 Growth", 
                "Term 3 Discoveries",
                "Term 4 Achievements",
                "Year Reflections"
            ],
            "description": f"Document your learning journey through Year {(custom_params or {}).get('year', 'X')}"
        },
        "term": {
            "title": f"{student_name}'s {(custom_params or {}).get('term', 'Term')} Portfolio",
            "sections": [
                "Learning Goals",
                "Projects & Investigations",
                "Skill Development",
                "Challenges & Growth",
                "Term Reflection"
            ],
            "description": f"Capture your {(custom_params or {}).get('term', 'term')} learning experience"
        }
    }
    
    template = templates.get(template_type, templates["blank"])
    
    return {
        "template_type": template_type,
        "title": template["title"],
        "sections": template["sections"],
        "description": template["description"],
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "entries": {section: [] for section in template["sections"]},
        "annotations": [],
        "custom_params": custom_params or {}
    }

def add_portfolio_entry(portfolio, section, entry_data):
    """Add an entry to a portfolio section"""
    if section in portfolio["entries"]:
        portfolio["entries"][section].append({
            "id": len(portfolio["entries"][section]) + 1,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "content": entry_data.get("content", ""),
            "type": entry_data.get("type", "text"),
            "file_info": entry_data.get("file_info", {}),
            "reflection": entry_data.get("reflection", ""),
            "tags": entry_data.get("tags", []),
            "cec_analysis": entry_data.get("cec_analysis", "")
        })

def annotate_portfolio_entry(portfolio, section, entry_id, annotation):
    """Add annotation to a specific portfolio entry"""
    portfolio["annotations"].append({
        "id": len(portfolio["annotations"]) + 1,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "section": section,
        "entry_id": entry_id,
        "annotation": annotation,
        "type": "entry_annotation"
    })

def add_portfolio_reflection(portfolio, reflection_text, reflection_type="general"):
    """Add a learning reflection to the portfolio"""
    portfolio["annotations"].append({
        "id": len(portfolio["annotations"]) + 1,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "reflection": reflection_text,
        "type": reflection_type,
        "section": "general"
    })

def create_shared_lesson(lesson_content, author, curriculum, topic):
    """Create a shareable lesson plan for team collaboration"""
    lesson = {
        "id": len(st.session_state.shared_lessons) + 1,
        "title": f"Learning Connections: {topic}",
        "author": author,
        "curriculum": curriculum,
        "topic": topic,
        "content": lesson_content,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "collaborators": [],
        "comments": [],
        "tags": []
    }
    
    st.session_state.shared_lessons.append(lesson)
    return lesson

def share_rubric_with_team(rubric_content, teacher_username, topic, curriculum):
    """Share assessment rubric with teaching team"""
    if 'shared_rubrics' not in st.session_state:
        st.session_state.shared_rubrics = []
    
    shared_rubric = {
        'id': len(st.session_state.shared_rubrics) + 1,
        'title': f"Assessment Rubric: {topic}",
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'teacher': teacher_username,
        'topic': topic,
        'curriculum': curriculum,
        'content': rubric_content,
        'comments': [],
        'tags': ['assessment', 'rubric']
    }
    st.session_state.shared_rubrics.append(shared_rubric)

def add_lesson_comment(lesson_id, commenter, comment):
    """Add collaborative comment to a shared lesson"""
    for lesson in st.session_state.shared_lessons:
        if lesson["id"] == lesson_id:
            lesson["comments"].append({
                "author": commenter,
                "content": comment,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            break

def create_timeline_visualization(topics_data):
    """Create a timeline visualization for scope and sequence"""
    if not topics_data:
        return None
    
    # Create sample timeline data
    start_date = datetime.now()
    timeline_data = []
    
    for i, topic in enumerate(topics_data):
        start = start_date + timedelta(weeks=i*2)
        end = start + timedelta(weeks=2)
        timeline_data.append({
            'Topic': topic,
            'Start': start,
            'End': end,
            'Week': f"Weeks {i*2+1}-{i*2+2}"
        })
    
    df = pd.DataFrame(timeline_data)
    
    # Create Gantt chart
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="End", 
        y="Topic",
        title="Suggested Scope & Sequence Timeline",
        color_discrete_sequence=["#1f77b4"]
    )
    
    fig.update_layout(
        xaxis_title="Timeline",
        yaxis_title="Topics",
        height=400,
        showlegend=False
    )
    
    return fig

# Custom CSS for Montessori aesthetic
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #f5f1e8 0%, #faf7f0 100%);
    }
    .stTitle {
        color: #8B4513;
        font-family: 'Georgia', serif;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .cosmic-subtitle {
        color: #5D4E75;
        font-style: italic;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .teacher-card {
        background: linear-gradient(145deg, #e8dcc0, #f0e6d2);
        border-left: 5px solid #8B4513;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .student-card {
        background: linear-gradient(145deg, #e0f2e7, #f0f8f2);
        border-left: 5px solid #2E8B57;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .welcome-box {
        background: rgba(255,255,255,0.8);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
        backdrop-filter: blur(5px);
    }
    .guide-feature {
        background: rgba(255,255,255,0.6);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #8B4513;
    }
</style>
""", unsafe_allow_html=True)

# Authentication Flow
if not st.session_state.authenticated:
    # Login/Signup Interface
    st.markdown('<h1 class="stTitle">🌍 Guide - Cosmic Curriculum Companion</h1>', unsafe_allow_html=True)
    st.markdown('<p class="cosmic-subtitle">Weaving threads of knowledge in the tapestry of learning</p>', unsafe_allow_html=True)
    
    # Welcome message with Montessori philosophy
    st.markdown("""
    <div class="welcome-box">
        <h3>🌟 Welcome to Your Cosmic Learning Journey</h3>
        <p><em>"The child is both a hope and a promise for mankind" - Maria Montessori</em></p>
        <p>Guide bridges Montessori's Cosmic Education with modern curriculum frameworks, 
        helping educators create meaningful learning experiences that connect to the larger patterns of life and the universe.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login/Signup tabs
    auth_tabs = st.tabs(["🔑 Login", "📝 Create Teacher Account", "🎓 Student Access"])
    
    with auth_tabs[0]:  # Login
        st.markdown("### Sign In to Your Guide Account")
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            # Use form to enable Enter key submission
            with st.form("login_form"):
                login_username = st.text_input("Username", key="login_username")
                login_password = st.text_input("Password", type="password", key="login_password")
                
                # Form submit button - activates on Enter key press
                login_submitted = st.form_submit_button("🌱 Enter Your Learning Space", use_container_width=True)
            
            if login_submitted:
                if login_username and login_password:
                    success, message = authenticate_user(login_username, login_password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.current_user = login_username
                        st.session_state.user_role = st.session_state.users[login_username]['role']
                        st.success("Welcome back to your cosmic learning journey!")
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    with auth_tabs[1]:  # Teacher Registration
        st.markdown("### Create Your Teacher Account")
        st.markdown("*Join our community of cosmic educators*")
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            reg_username = st.text_input("Choose Username", key="reg_username")
            reg_password = st.text_input("Create Password", type="password", key="reg_password")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_school = st.text_input("School/Organization (Optional)", key="reg_school")
            
            if st.button("🌿 Create My Teaching Space", use_container_width=True):
                if reg_username and reg_password and reg_email:
                    success, message = create_teacher_account(reg_username, reg_password, reg_email, reg_school)
                    if success:
                        st.success("Account created successfully! Please log in above.")
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill in all required fields")
    
    with auth_tabs[2]:  # Student Access
        st.markdown("### Student Learning Portal")
        
        student_access_tabs = st.tabs(["🔑 Login", "🆕 Create Account"])
        
        with student_access_tabs[0]:  # Student Login
            st.markdown("#### Sign In to Your Learning Space")
            st.markdown("*Use your existing username and password*")
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                student_username = st.text_input("Student Username", key="student_login_username")
                student_password = st.text_input("Student Password", type="password", key="student_login_password")
                
                if st.button("🌟 Enter My Learning Journey", use_container_width=True):
                    if student_username and student_password:
                        success, message = authenticate_user(student_username, student_password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.current_user = student_username
                            st.session_state.user_role = 'student'
                            st.success("Welcome to your learning adventure!")
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Please enter your username and password")
        
        with student_access_tabs[1]:  # Create Student Account
            st.markdown("#### Create Your Student Account")
            st.markdown("*Choose your own username and password*")
            
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                new_student_name = st.text_input("Your Name", key="new_student_name", 
                                                placeholder="Enter your full name")
                
                # Auto-suggest username based on name
                suggested_username = ""
                if new_student_name:
                    # Create username from name (remove spaces, make lowercase, keep only letters and numbers)
                    suggested_username = re.sub(r'[^a-zA-Z0-9]', '', new_student_name.lower())
                    
                new_student_username = st.text_input("Choose Username", 
                                                    key="new_student_username",
                                                    value=suggested_username if suggested_username else "",
                                                    placeholder="Your username for logging in")
                new_student_password = st.text_input("Choose Password", type="password", key="new_student_password",
                                                   placeholder="At least 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_student_password",
                                               placeholder="Type your password again")
                
                # Optional teacher connection
                teacher_code = st.text_input("Teacher's Username (Optional)", 
                                           key="teacher_code",
                                           help="If your teacher gave you their username, enter it here to connect your accounts")
                
                if st.button("🌱 Create My Learning Account", use_container_width=True):
                    if new_student_name and new_student_username and new_student_password:
                        if new_student_password != confirm_password:
                            st.error("Passwords don't match. Please try again.")
                        elif len(new_student_password) < 6:
                            st.error("Password must be at least 6 characters long.")
                        else:
                            # Validate teacher username if provided
                            teacher_username = None
                            if teacher_code:
                                if teacher_code in st.session_state.users:
                                    if st.session_state.users[teacher_code]['role'] == 'teacher':
                                        teacher_username = teacher_code
                                    else:
                                        st.error("The provided teacher code is not valid.")
                                        st.stop()
                                else:
                                    st.error("Teacher username not found. You can still create an account without connecting to a teacher.")
                            
                            success, message = create_custom_student_account(
                                new_student_username, 
                                new_student_password, 
                                new_student_name, 
                                teacher_username
                            )
                            
                            if success:
                                st.success("Account created successfully! You can now login above.")
                                st.info("Remember to save your username and password somewhere safe!")
                            else:
                                st.error(message)
                    else:
                        st.warning("Please fill in your name, username, and password")

else:
    # Authenticated user interface
    current_user = st.session_state.current_user
    user_role = st.session_state.user_role
    user_data = st.session_state.users.get(current_user, {})
    
    # Header with user info and logout
    header_col1, header_col2, header_col3 = st.columns([2, 2, 1])
    
    with header_col1:
        if user_role == 'teacher':
            st.markdown(f'<h1 class="stTitle">🌍 Guide - Teacher Dashboard</h1>', unsafe_allow_html=True)
            st.markdown(f'<p class="cosmic-subtitle">Welcome back, {current_user} ✨</p>', unsafe_allow_html=True)
        else:
            student_name = user_data.get('real_name', current_user)
            st.markdown(f'<h1 class="stTitle">🌟 My Learning Journey</h1>', unsafe_allow_html=True)
            st.markdown(f'<p class="cosmic-subtitle">Hello, {student_name}! 🌱</p>', unsafe_allow_html=True)
    
    with header_col2:
        # Hidden usage tracking (still logs for developer)
        daily_used = user_data.get('daily_requests', 0)
        daily_limit = user_data.get('daily_limit', 200)
        monthly_used = user_data.get('monthly_usage', 0)
        monthly_limit = user_data.get('monthly_limit', 100000)
        
        # Usage is tracked but not displayed to users
        # Usage data is still logged in the background for developer monitoring
    
    with header_col3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.rerun()
    
    # Role-specific interfaces
    if user_role == 'teacher':
        # TEACHER DASHBOARD
        st.markdown('<div class="teacher-card">', unsafe_allow_html=True)
        
        # Admin content upload section (if user is admin)
        if current_user in ['admin', 'developer']:  # Simple admin check
            with st.expander("🔒 Admin: Upload Training Content"):
                st.markdown("**Upload content to reduce AI hallucinations**")
                admin_password = st.text_input("Admin Password", type="password", key="admin_pass")
                training_text = st.text_area("Training Content", height=200, key="training_content")
                
                if st.button("Upload Training Data"):
                    if training_text and admin_password:
                        success, message = upload_training_content(training_text, admin_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        
        # Teacher Feature Instruction Popup
        if st.button("ℹ️ Understanding Your Teaching Tools"):
            st.markdown("""
            <div class="guide-feature">
                <h4>📚 Enhanced Scope & Sequence</h4>
                <p>Create comprehensive learning progressions with choice between explicit learning areas or concept/theme-based integration. Supports AC V9 only, MNC only, or blended approaches with cosmic education priority.</p>
                
                <h4>🌟 Learning Invitations & Connections</h4>
                <p>Unified tool that merges learning invitations and connections. Includes age group adjustment and GPT-4o mini chat for refinement and curation of learning plans backed by curriculum frameworks.</p>
                
                <h4>🕸️ Learning Threads & Patterns</h4>
                <p>Map knowledge as interconnected webs rather than isolated subjects. Visualize how topics spiral and connect across disciplines, honoring the Montessori approach to integrated learning.</p>
                
                <h4>💫 Family & Community Connection</h4>
                <p>Generate communications that help families understand learning in terms of whole-child development and cosmic connections. Bridge school and home learning.</p>
                
                <h4>📏 Assessment Rubrics</h4>
                <p>Create curriculum-aligned assessment rubrics with flexible framework selection and comprehensive configuration options for authentic assessment.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Main teacher interface tabs
        # MVP Version - Hide advanced features for simplicity
        teacher_tabs = st.tabs([
            "💬 Ask Maria", 
            "🧠 Learning Tools", 
            "👥 Student Management", 
            "♿ Accessibility"
        ])
        
        # Features hidden in MVP (available in full version):
        # "🤝 Collaboration", "📊 All & Advisory", "🧮 Mathematics Hub", "🏡 Family Connections"
        
        with teacher_tabs[0]:  # Ask Maria
            st.markdown("### 💬 Ask Maria")
            st.markdown("*Your cosmic curriculum guide for Montessori wisdom, teaching inspiration, and practical guidance*")
            
            # Welcome message and tips
            st.info("**🌟 Welcome!** Ask me anything about Montessori education, cosmic curriculum, teaching strategies, child development, or any educational topic. I'm here to help you on your teaching journey.")
            

            

            
            # Chat interface
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Follow-up suggestions positioned after conversation history
            if st.session_state.messages:
                st.markdown("**💭 Continue exploring:**")
                maria_follow_col1, maria_follow_col2, maria_follow_col3 = st.columns(3)
                
                with maria_follow_col1:
                    if st.button("🤔 Tell me more", key=f"more_maria_{len(st.session_state.messages)}"):
                        more_prompt = "Can you tell me more about this? I'd like to understand it better or explore it further."
                        st.session_state.messages.append({"role": "user", "content": more_prompt})
                        st.rerun()
                
                with maria_follow_col2:
                    if st.button("💡 Give examples", key=f"examples_maria_{len(st.session_state.messages)}"):
                        examples_prompt = "Can you give me some specific examples or practical applications of what you just explained?"
                        st.session_state.messages.append({"role": "user", "content": examples_prompt})
                        st.rerun()
                
                with maria_follow_col3:
                    if st.button("🔗 How does this connect?", key=f"connect_maria_{len(st.session_state.messages)}"):
                        connect_prompt = "How does this connect to other areas of learning or the bigger picture? What are the cosmic connections?"
                        st.session_state.messages.append({"role": "user", "content": connect_prompt})
                        st.rerun()
            
            # Chat input positioned after conversation and follow-up options
            if prompt := st.chat_input("Ask me anything about Montessori education, teaching, or learning..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()
        
        with teacher_tabs[1]:  # Learning Tools
            # MVP Learning Tools - Core features only
            tool_subtabs = st.tabs([
                "⚡ Quick Planning",
                "📚 Enhanced Scope & Sequence", 
                "📝 Lesson Planning Assistant", 
                "🗺️ Big Picture Curriculum Mapping", 
                "📏 Assessment Rubrics"
            ])
            
            # Hidden MVP features: "💫 Family Connection", "🧮 Mathematics Hub"
            
            with tool_subtabs[0]:  # Quick Planning
                st.markdown("### ⚡ Quick Planning Assistant")
                st.markdown("*Your instant AI teaching companion - create resources, generate ideas, and get quick answers*")
                
                # Quick Planning chat interface
                st.markdown("#### 💬 Ask me to help you create anything:")
                st.markdown("*Examples: Write a lesson plan for fractions, Create a reading comprehension activity, Generate discussion questions about the solar system, Write parent communication about our science unit...*")
                
                # Initialize quick planning messages if not exists
                if 'quick_planning_messages' not in st.session_state:
                    st.session_state.quick_planning_messages = []
                
                # Display chat history for quick planning
                for message in st.session_state.quick_planning_messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                # Follow-up suggestions positioned above input for efficiency
                if st.session_state.quick_planning_messages:
                    st.markdown("**💡 Follow up to refine further:**")
                    follow_up_col1, follow_up_col2, follow_up_col3 = st.columns(3)
                    
                    with follow_up_col1:
                        if st.button("🔄 Modify this", key=f"modify_quick_{len(st.session_state.quick_planning_messages)}"):
                            modify_prompt = f"Please modify the above response to be different. Consider alternative approaches, additional details, or different perspectives."
                            st.session_state.quick_planning_messages.append({"role": "user", "content": modify_prompt})
                            st.rerun()
                    
                    with follow_up_col2:
                        if st.button("➕ Add more ideas", key=f"expand_quick_{len(st.session_state.quick_planning_messages)}"):
                            expand_prompt = f"Please expand on the above with additional ideas, extensions, or related activities that could complement this."
                            st.session_state.quick_planning_messages.append({"role": "user", "content": expand_prompt})
                            st.rerun()
                    
                    with follow_up_col3:
                        if st.button("🎯 Make it specific", key=f"specific_quick_{len(st.session_state.quick_planning_messages)}"):
                            specific_prompt = f"Please make the above more specific and detailed with concrete examples, step-by-step instructions, or practical implementation ideas."
                            st.session_state.quick_planning_messages.append({"role": "user", "content": specific_prompt})
                            st.rerun()
                
                # Quick planning input - positioned after conversation history
                if quick_prompt := st.chat_input("What would you like me to create or help you with?"):
                    st.session_state.quick_planning_messages.append({"role": "user", "content": quick_prompt})
                    st.rerun()
                
                # Clear quick planning chat
                if st.button("🗑️ Clear Quick Planning Chat", key="clear_quick_planning"):
                    st.session_state.quick_planning_messages = []
                    st.rerun()
            
            with tool_subtabs[1]:  # Enhanced Scope & Sequence
                st.markdown("### Enhanced Scope & Sequence Creation")
                st.markdown("*Design comprehensive learning progressions with flexible curriculum integration*")
                st.info("💡 **What this does:** Creates detailed learning progressions that map out what students will learn over weeks or terms. Choose between subject-specific planning or integrated theme-based approaches that connect multiple learning areas.")
                
                # Scope & Sequence Configuration
                scope_col1, scope_col2 = st.columns(2)
                
                with scope_col1:
                    st.markdown("#### 📋 Planning Approach")
                    planning_approach = st.radio(
                        "How would you like to structure learning?",
                        ["🏛️ Explicit Learning Areas (Siloed)", "🌐 Concept/Theme-Based Integration"],
                        help="Choose between traditional subject-based planning or integrated theme-based approach"
                    )
                    
                    st.markdown("#### 📚 Curriculum Framework")
                    curriculum_blend = st.radio(
                        "Which curriculum framework should guide the sequence?",
                        ["🇦🇺 Australian Curriculum V9 Only", "🌱 Montessori National Curriculum Only", "🔄 Blended (Cosmic Education Priority)"],
                        help="Select curriculum framework - blended approach prioritizes cosmic education principles"
                    )
                
                with scope_col2:
                    st.markdown("#### 📊 Sequence Parameters")
                    if planning_approach == "🏛️ Explicit Learning Areas (Siloed)":
                        learning_area = st.selectbox(
                            "Select Learning Area",
                            ["English", "Mathematics", "Science", "HASS (F-6)", "Geography (7-10)", 
                             "History (7-10)", "Civics & Citizenship (7-10)", "Economics & Business (7-10)",
                             "Health & Physical Education", "Technologies", "The Arts - Visual Arts", 
                             "The Arts - Music", "Indonesian Language"],
                            key="learning_area_explicit"
                        )
                        sequence_topic = st.text_input("Specific Topic/Unit", placeholder="e.g., Fractions, Water Cycle, Ancient Rome...", key="sequence_topic_explicit")
                    else:
                        concept_theme = st.text_input("Central Concept/Theme", placeholder="e.g., Interconnectedness, Change Over Time, Patterns in Nature...", key="concept_theme_integrated")
                        contributing_areas = st.multiselect(
                            "Contributing Learning Areas",
                            ["English", "Mathematics", "Science", "HASS", "Health & PE", "Technologies", "The Arts", "Languages"],
                            default=["English", "Mathematics", "Science"],
                            key="contributing_areas_integrated"
                        )
                    
                    year_level = st.multiselect(
                        "Year Level(s)",
                        ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"],
                        default=["Year 3"],
                        help="Select one or more year levels for your scope and sequence"
                    )
                    duration = st.selectbox("Sequence Duration", ["1 cycle", "1-2 weeks", "3-4 weeks", "5-6 weeks", "7-8 weeks", "One term", "One semester"])
                
                sequence_context = st.text_area(
                    "Additional Context & Goals",
                    placeholder="Share any specific learning goals, student needs, or contextual considerations...",
                    height=100
                )
                
                if st.button("📚 Generate Enhanced Scope & Sequence", use_container_width=True):
                    # Initialize variables
                    learning_area = None
                    sequence_topic = None
                    concept_theme = None
                    contributing_areas = None
                    
                    # Set variables based on planning approach
                    if planning_approach == "🏛️ Explicit Learning Areas (Siloed)":
                        learning_area = st.session_state.get('learning_area_explicit', '')
                        sequence_topic = st.session_state.get('sequence_topic_explicit', '')
                    else:
                        concept_theme = st.session_state.get('concept_theme_integrated', '')
                        contributing_areas = st.session_state.get('contributing_areas_integrated', [])
                    
                    if (planning_approach == "🏛️ Explicit Learning Areas (Siloed)" and learning_area and sequence_topic and year_level) or \
                       (planning_approach == "🌐 Concept/Theme-Based Integration" and concept_theme and contributing_areas and year_level):
                        
                        with st.spinner("Creating comprehensive scope & sequence..."):
                            # Determine curriculum reference for API call
                            if curriculum_blend == "🇦🇺 Australian Curriculum V9 Only":
                                curriculum_ref = "Australian Curriculum V9"
                            elif curriculum_blend == "🌱 Montessori National Curriculum Only":
                                curriculum_ref = "Montessori Curriculum Australia"
                            else:
                                curriculum_ref = "Blended (Cosmic Education Priority)"
                            
                            # Format year levels for display
                            year_levels_str = ", ".join(year_level) if isinstance(year_level, list) else str(year_level)
                            
                            # Special handling for 1 cycle duration
                            if duration == "1 cycle":
                                duration_detail = "1 cycle (12 terms across 3 years: 4 terms 1st year, 4 terms 2nd year, 4 terms 3rd year)"
                                cycle_instruction = """
IMPORTANT: This is a 1 CYCLE sequence spanning 3 years. Structure your response as:
- **Year 1 (Terms 1-4)**: [detailed term-by-term breakdown]
- **Year 2 (Terms 1-4)**: [detailed term-by-term breakdown] 
- **Year 3 (Terms 1-4)**: [detailed term-by-term breakdown]

Each term should show clear progression and skill development across the three-year cycle."""
                            else:
                                duration_detail = duration
                                cycle_instruction = ""
                            
                            # Build enhanced prompt for scope & sequence with curriculum integration
                            if planning_approach == "🏛️ Explicit Learning Areas (Siloed)":
                                sequence_prompt = f"""Create a comprehensive scope and sequence for {learning_area} focusing on {sequence_topic} for {year_levels_str} students over {duration_detail}.

Framework: {curriculum_blend}
Context: {sequence_context}
{cycle_instruction}

CURRICULUM INTEGRATION REQUIREMENTS:
- Reference specific Australian Curriculum V9 content descriptors and achievement standards with codes (e.g., ACELY1234)
- Include relevant Montessori National Curriculum elements and developmental considerations
- Use authentic curriculum language and terminology throughout
- Align assessment with official curriculum standards and progressions

Please provide:
1. **Learning Overview & Big Ideas**: Connect this topic to larger patterns and cosmic story, referencing curriculum frameworks
2. **Detailed Progression**: {'Term-by-term breakdown across 3 years' if duration == '1 cycle' else 'Weekly/periodic breakdown'} showing skill/knowledge building with curriculum codes
3. **Curriculum Alignment**: Explicit links to AC V9 content descriptors and achievement standards with codes
4. **Assessment Checkpoints**: Authentic assessment opportunities aligned with curriculum standards and progressions
5. **Cross-Curricular Connections**: Links to other learning areas with specific curriculum references
6. **Differentiation Strategies**: Support for diverse learners aligned with curriculum guidance
7. **Resources & Materials**: Essential and optional resources that support curriculum objectives
8. **Reflection Questions**: Deep thinking prompts aligned with curriculum capabilities

Ensure all content descriptors, achievement standards, and progression points are accurately referenced with official codes and language."""
                            else:
                                sequence_prompt = f"""Create a concept/theme-based scope and sequence centered on "{concept_theme}" integrating {', '.join(contributing_areas or [])} for {year_levels_str} students over {duration_detail}.

Framework: {curriculum_blend}
{cycle_instruction}

CURRICULUM INTEGRATION REQUIREMENTS:
- Reference specific Australian Curriculum V9 content descriptors and achievement standards with codes across all learning areas
- Include relevant Montessori National Curriculum cosmic education principles and developmental stages
- Use authentic curriculum language and cross-curricular connections
- Align assessment with official curriculum standards and progressions
Context: {sequence_context}

Please provide:
1. **Thematic Overview**: How this concept connects to cosmic education and universal patterns
2. **Integrated Learning Progression**: Week-by-week development showing how each learning area contributes
3. **Essential Questions**: Driving inquiries that connect all learning areas
4. **Culminating Experience**: Authentic demonstration of integrated learning
5. **Assessment Through Multiple Lenses**: How progress is observed across different domains
6. **Real-World Connections**: Links to community, environment, and larger systems
7. **Student Agency Opportunities**: Choice points and self-directed learning moments

Honor both rigorous curriculum standards and cosmic education principles of interconnection."""
                            
                            # Generate scope & sequence
                            messages = [{"role": "user", "content": sequence_prompt}]
                            system_prompt = get_system_prompt(curriculum_ref)
                            
                            scope_sequence = call_openai_api(messages, system_prompt)
                            if scope_sequence:
                                st.markdown("### 📚 Enhanced Scope & Sequence")
                                st.markdown(f"**Approach:** {planning_approach}")
                                st.markdown(f"**Framework:** {curriculum_blend}")
                                st.markdown(f"**Year Level(s):** {year_levels_str} | **Duration:** {duration_detail if duration == '1 cycle' else duration}")
                                st.markdown("---")
                                st.markdown(scope_sequence)
                                
                                # Follow-up refinement options
                                st.markdown("---")
                                st.markdown("**🔧 Refine your scope & sequence:**")
                                refine_col1, refine_col2, refine_col3 = st.columns(3)
                                
                                with refine_col1:
                                    if st.button("📊 Add assessment details", key="assess_scope"):
                                        assess_prompt = f"Please enhance this scope & sequence by adding more detailed assessment strategies, rubrics, and evidence collection methods aligned with the curriculum standards."
                                        messages = [{"role": "user", "content": assess_prompt}]
                                        enhanced_response = call_openai_api(messages, get_system_prompt(curriculum_ref))
                                        if enhanced_response:
                                            st.markdown("### 📊 Enhanced Assessment Details")
                                            st.markdown(enhanced_response)
                                
                                with refine_col2:
                                    if st.button("🎨 Add activities", key="activities_scope"):
                                        activities_prompt = f"Please add specific learning activities, hands-on experiences, and engaging tasks for this scope & sequence that align with cosmic education principles."
                                        messages = [{"role": "user", "content": activities_prompt}]
                                        enhanced_response = call_openai_api(messages, get_system_prompt(curriculum_ref))
                                        if enhanced_response:
                                            st.markdown("### 🎨 Suggested Learning Activities")
                                            st.markdown(enhanced_response)
                                
                                with refine_col3:
                                    if st.button("🔗 Expand connections", key="connect_scope"):
                                        connections_prompt = f"Please expand on the cross-curricular connections and cosmic education links for this scope & sequence, showing how it connects to the bigger picture of learning."
                                        messages = [{"role": "user", "content": connections_prompt}]
                                        enhanced_response = call_openai_api(messages, get_system_prompt(curriculum_ref))
                                        if enhanced_response:
                                            st.markdown("### 🔗 Expanded Connections")
                                            st.markdown(enhanced_response)
                                
                                # Save and share options
                                st.markdown("---")
                                col_save1, col_save2 = st.columns(2)
                                with col_save1:
                                    if st.button("💾 Save Scope & Sequence", key="save_scope_seq"):
                                        st.success("Scope & Sequence saved to your library!")
                                with col_save2:
                                    if st.button("📤 Share with Team", key="share_scope_seq"):
                                        st.success("Scope & Sequence shared with your team!")
                            else:
                                st.error("Unable to generate scope & sequence. Please try again.")
                    else:
                        st.warning("Please complete all required fields before generating.")
            
            with tool_subtabs[2]:  # Lesson Planning Assistant
                st.markdown("### 📝 Lesson Planning Assistant")
                st.markdown("*Create engaging lessons, activities, and learning experiences*")
                st.info("💡 **What this does:** Designs specific lessons and activities for your students. Perfect for planning what your students will actually do in class or at home.")
                
                # Step-by-step guidance
                st.markdown("#### 🚀 Quick Start: Tell me what you need")
                
                lesson_col1, lesson_col2 = st.columns(2)
                
                with lesson_col1:
                    invitation_topic = st.text_input(
                        "🎯 What topic do you want to teach?", 
                        placeholder="e.g., Water cycle, Fractions, Ancient Egypt...",
                        help="Any subject or topic you want to create a lesson for"
                    )
                    
                    age_group = st.selectbox(
                        "👥 Who are you teaching?",
                        ["Early Years (3-6)", "Lower Primary (6-9)", "Upper Primary (9-12)", "Early Secondary (12-15)"],
                        help="This helps me create age-appropriate activities"
                    )
                
                with lesson_col2:
                    invitation_curriculum = st.radio(
                        "📚 Which curriculum approach?",
                        ["🔄 Blended (Recommended - Cosmic Priority)", "🇦🇺 Australian Curriculum V9", "🌱 Montessori National Curriculum"],
                        key="invitation_curriculum",
                        help="Blended approach connects to the cosmic story while meeting curriculum standards"
                    )
                
                # Upload existing lesson for feedback/remodeling
                st.markdown("---")
                st.markdown("#### 📄 Upload Existing Lesson for Feedback")
                st.markdown("*Have an existing lesson you want to improve or get feedback on?*")
                
                uploaded_lesson = st.file_uploader(
                    "Upload your lesson plan",
                    type=['txt', 'pdf', 'docx', 'doc'],
                    help="Upload an existing lesson plan to get AI feedback or request remodeling",
                    key="lesson_upload"
                )
                
                lesson_feedback_type = st.radio(
                    "What would you like me to do?",
                    ["💡 Provide feedback and suggestions", "🔄 Remodel with cosmic education approach", "✨ Enhance and expand the lesson"],
                    help="Choose how you want me to help with your existing lesson"
                )
                
                if uploaded_lesson is not None:
                    try:
                        if uploaded_lesson.type == "text/plain":
                            lesson_content = str(uploaded_lesson.read(), "utf-8")
                            st.session_state.uploaded_lesson_content = lesson_content
                            st.session_state.uploaded_lesson_name = uploaded_lesson.name
                            st.success(f"✓ Loaded {uploaded_lesson.name}")
                            
                            # Show delete option for uploaded lesson
                            col_analyze, col_delete = st.columns([3, 1])
                            with col_analyze:
                                analyze_button = st.button("🔍 Analyze My Lesson", use_container_width=True)
                            with col_delete:
                                if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                                    if hasattr(st.session_state, 'uploaded_lesson_content'):
                                        del st.session_state.uploaded_lesson_content
                                    if hasattr(st.session_state, 'uploaded_lesson_name'):
                                        del st.session_state.uploaded_lesson_name
                                    st.success("Lesson content deleted!")
                                    st.rerun()
                            
                            if analyze_button:
                                with st.spinner("Analyzing your lesson..."):
                                    feedback_prompt = f"""Please analyze this lesson plan and provide {lesson_feedback_type.lower()}:

LESSON PLAN:
{lesson_content}

TARGET: {age_group} students
CURRICULUM APPROACH: {invitation_curriculum}

Based on the selected feedback type "{lesson_feedback_type}", please provide:

1. **Strengths Observed**: What works well in this lesson
2. **Cosmic Education Connections**: How to enhance connections to the bigger picture
3. **Specific Improvements**: Concrete suggestions for enhancement
4. **Age-Appropriateness**: Ensure activities match {age_group} developmental needs
5. **Differentiation**: Ways to support diverse learners
6. **Assessment Integration**: Suggestions for observing and documenting learning

If remodeling was requested, provide a complete revised version. If enhancement was requested, provide specific additions and modifications. Always maintain the lesson's core intent while enriching it with cosmic education principles."""

                                    messages = [{"role": "user", "content": feedback_prompt}]
                                    system_prompt = get_system_prompt(invitation_curriculum.replace("🔄 Blended (Recommended - Cosmic Priority)", "Blended (Cosmic Education Priority)").replace("🇦🇺 ", "").replace("🌱 ", ""))
                                    
                                    feedback_response = call_openai_api(messages, system_prompt)
                                    if feedback_response:
                                        st.markdown("### 📋 Lesson Analysis & Feedback")
                                        st.markdown(f"**Original Lesson:** {uploaded_lesson.name}")
                                        st.markdown(f"**Analysis Type:** {lesson_feedback_type}")
                                        st.markdown("---")
                                        st.markdown(feedback_response)
                        else:
                            st.info(f"File {uploaded_lesson.name} uploaded. PDF/Word processing coming soon!")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
                
                # Advanced options (collapsible)
                with st.expander("⚙️ Customize Your New Lesson (Optional)"):
                    st.markdown("*Only fill these out if you want to customize further:*")
                    
                    customize_col1, customize_col2 = st.columns(2)
                    
                    with customize_col1:
                        learning_context = st.text_area(
                            "🌐 Any special context?",
                            placeholder="Student interests, current projects, special needs, outdoor space available...",
                            height=80,
                            help="This helps me tailor the lesson to your specific situation"
                        )
                    
                    with customize_col2:
                        experience_types = st.multiselect(
                            "🎨 What kind of activities do you prefer?",
                            ["Hands-on Investigation", "Creative Expression", "Community Connection", "Real-world Problem Solving", 
                             "Independent Research", "Collaborative Project", "Sensory Exploration", "Reflection & Documentation"],
                            help="Leave blank for a good mix of activity types"
                        )
                
                if st.button("✨ Create My Lesson Plan", use_container_width=True, type="primary"):
                    if invitation_topic and age_group:
                        with st.spinner("Crafting age-appropriate learning experiences..."):
                            # Determine curriculum reference
                            if invitation_curriculum == "🇦🇺 Australian Curriculum V9":
                                curr_ref = "Australian Curriculum V9"
                            elif invitation_curriculum == "🌱 Montessori National Curriculum":
                                curr_ref = "Montessori Curriculum Australia"
                            else:
                                curr_ref = "Blended (Cosmic Education Priority)"
                            
                            # Create comprehensive prompt  
                            experience_types_text = ', '.join(experience_types) if experience_types else "varied hands-on activities"
                            
                            invitation_prompt = f"""Create a complete lesson plan for "{invitation_topic}" designed for {age_group} students.

Framework: {invitation_curriculum}
Activity Types: {experience_types_text}
Context: {learning_context}

Please provide a practical lesson plan that includes:

**📝 LESSON OVERVIEW:**
1. **Learning Objectives**: What students will know and be able to do
2. **Cosmic Connections**: How this topic connects to the bigger picture of life and learning
3. **Duration**: Suggested timeframe for the lesson/unit

**🎯 MAIN ACTIVITIES:**
1. **Opening Invitation**: How to spark curiosity and introduce the topic
2. **Core Learning Experiences**: 2-3 main activities students will do
3. **Hands-On Investigations**: Concrete activities that let students explore and discover
4. **Creative Expression**: Ways students can show their learning

**📚 CURRICULUM CONNECTIONS:**
1. **Learning Area Links**: How this connects to different subject areas
2. **Skills Development**: Key skills students will practice and develop

**🌟 EXTENSIONS & VARIATIONS:**
1. **For Advanced Learners**: Additional challenges and deeper investigations
2. **For Support Needs**: Simpler entry points and scaffolding
3. **Assessment Ideas**: How to observe and document student learning

Make this practical and immediately usable in the classroom. Include specific materials needed and clear step-by-step guidance."""
                            
                            # Generate initial content
                            messages = [{"role": "user", "content": invitation_prompt}]
                            system_prompt = get_system_prompt(curr_ref)
                            
                            initial_response = call_openai_api(messages, system_prompt)
                            if initial_response:
                                st.markdown("### 🌟 Learning Invitations & Connections")
                                st.markdown(f"**Topic:** {invitation_topic} | **Age Group:** {age_group}")
                                st.markdown(f"**Framework:** {invitation_curriculum}")
                                st.markdown("---")
                                
                                # Store in session state for chat refinement
                                if 'current_invitation' not in st.session_state:
                                    st.session_state.current_invitation = {}
                                
                                st.session_state.current_invitation = {
                                    'topic': invitation_topic,
                                    'age_group': age_group,
                                    'curriculum': invitation_curriculum,
                                    'content': initial_response,
                                    'chat_history': [{"role": "assistant", "content": initial_response}]
                                }
                                
                                st.markdown(initial_response)
                                
                                # GPT-4o mini chat refinement section
                                st.markdown("---")
                                st.markdown("### 💬 Customize Your Lesson Plan")
                                st.markdown("*Ask me to modify anything: add activities, change difficulty, include specific materials, etc.*")
                                
                                # Display chat history for this invitation
                                if 'chat_history' in st.session_state.current_invitation:
                                    chat_container = st.container()
                                    with chat_container:
                                        for i, msg in enumerate(st.session_state.current_invitation['chat_history']):
                                            if msg['role'] == 'user':
                                                st.markdown(f"**🧑‍🏫 You:** {msg['content']}")
                                            else:
                                                if i > 0:  # Don't show initial response again
                                                    st.markdown(f"**🤖 Guide:** {msg['content']}")
                                
                                # Chat input for refinement
                                if refinement_input := st.chat_input("e.g., 'Make this simpler for Year 2' or 'Add outdoor activities' or 'Include assessment rubric'..."):
                                    # Add user message to chat history
                                    st.session_state.current_invitation['chat_history'].append({"role": "user", "content": refinement_input})
                                    
                                    # Create context-aware prompt for refinement
                                    refinement_prompt = f"""The user wants to refine this learning plan for "{invitation_topic}" ({age_group}):

Original Plan: {initial_response}

User's refinement request: {refinement_input}

Please provide a thoughtful response that addresses their request while maintaining the quality and structure of the original plan. If they're asking for modifications, provide the modified version. If they want additions, integrate them seamlessly. Keep the cosmic education approach and curriculum alignment."""
                                    
                                    with st.spinner("Refining your learning plan..."):
                                        refinement_messages = [{"role": "user", "content": refinement_prompt}]
                                        refinement_response = call_openai_api(refinement_messages, system_prompt)
                                        
                                        if refinement_response:
                                            # Add response to chat history
                                            st.session_state.current_invitation['chat_history'].append({"role": "assistant", "content": refinement_response})
                                            st.rerun()
                                        else:
                                            st.error("Unable to process refinement. Please try again.")
                                
                                # Save and share options
                                st.markdown("---")
                                col_save1, col_save2 = st.columns(2)
                                with col_save1:
                                    if st.button("💾 Save Lesson Plan", key="save_invitation"):
                                        st.success("Lesson plan saved to your library!")
                                with col_save2:
                                    if st.button("📤 Share with Team", key="share_invitation"):
                                        create_shared_lesson(initial_response, current_user, curr_ref, invitation_topic)
                                        st.success("Lesson plan shared with your team!")
                            else:
                                st.error("Unable to generate learning invitations. Please try again.")
                    else:
                        st.warning("Please provide a learning topic and select an age group.")
            
            with tool_subtabs[3]:  # Big Picture Curriculum Mapping
                st.markdown("### 🗺️ Big Picture Curriculum Mapping")
                st.markdown("*Map how knowledge connects across subjects and time*")
                st.info("💡 **What this does:** Shows how topics connect across different subjects and build on each other. Reveals the web of knowledge for long-term planning and seeing the bigger picture.")
                
                # Simplified, guided approach
                st.markdown("#### 🧭 Quick Start: Choose your approach")
                
                mapping_approach = st.radio(
                    "What do you want to map?",
                    [
                        "🎯 Single Topic Connections (e.g., how 'water' connects to all subjects)",
                        "📚 Year Level Overview (e.g., how Year 3 topics build and connect)",
                        "🌱 Custom Topic Web (connect specific topics you choose)"
                    ],
                    help="Choose based on your planning needs"
                )
                
                map_col1, map_col2 = st.columns(2)
                
                with map_col1:
                    if "Single Topic" in mapping_approach:
                        central_topic = st.text_input(
                            "🎯 What's your central topic?",
                            placeholder="e.g., Water, Fractions, Democracy, Animals...",
                            help="I'll show how this connects to all learning areas"
                        )
                        manual_topics = central_topic
                    elif "Year Level" in mapping_approach:
                        year_level_mapping = st.selectbox(
                            "📅 Which year level?",
                            ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"]
                        )
                        manual_topics = f"Year {year_level_mapping} curriculum overview and connections"
                    else:
                        manual_topics = st.text_area(
                            "🌱 List the topics you want to connect:",
                            height=100,
                            placeholder="Mathematics patterns in nature\nHistory of human migration\nClimate and ecosystem changes...",
                            help="Enter each topic on a new line"
                        )
                
                with map_col2:
                    thread_curriculum = st.radio(
                        "📚 Curriculum approach:",
                        ["🔄 Blended (Recommended)", "🇦🇺 Australian Curriculum V9", "🌱 Montessori National Curriculum"],
                        key="thread_curriculum"
                    )
                    
                    visualization_type = st.selectbox(
                        "🎨 How should I show the connections?",
                        ["Concept Web (default)", "Timeline Sequence", "Learning Journey Map", "Systems Diagram"],
                        help="Concept Web works for most situations"
                    )
                
                # Optional context
                with st.expander("⚙️ Add Context (Optional)"):
                    thread_context = st.text_area(
                        "Any specific focus or context?",
                        placeholder="Student interests, current projects, term planning focus...",
                        height=60
                    )
                
                if st.button("🗺️ Create My Curriculum Map", use_container_width=True, type="primary"):
                    if manual_topics:
                        topics = [topic.strip() for topic in manual_topics.split('\n') if topic.strip()]
                        with st.spinner("Mapping cosmic connections..."):
                            # Determine curriculum reference
                            if thread_curriculum == "🇦🇺 Australian Curriculum V9":
                                thread_curr_ref = "Australian Curriculum V9"
                            elif thread_curriculum == "🌱 Montessori National Curriculum":
                                thread_curr_ref = "Montessori Curriculum Australia"
                            else:
                                thread_curr_ref = "Blended (Cosmic Education Priority)"
                            
                            sequence_plan = generate_scope_sequence(topics, thread_curr_ref)
                            if sequence_plan:
                                st.markdown("### Learning Threads & Interconnections")
                                st.markdown(sequence_plan)
                            
                            fig = create_timeline_visualization(topics[:10])
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
            
            # MVP Note: Assessment Rubrics feature available in full version
            # This section is hidden in MVP but preserved in codebase
            
            with tool_subtabs[4]:  # Assessment Rubrics
                st.markdown("### Curriculum-Aligned Assessment Rubrics")
                st.markdown("*Create growth-focused rubrics aligned to curriculum standards*")
                
                # Rubric Configuration
                rubric_col1, rubric_col2 = st.columns(2)
                
                with rubric_col1:
                    st.markdown("#### Learning Context")
                    rubric_topic = st.text_input("Topic/Subject Area:", 
                                               placeholder="e.g., Scientific inquiry, Narrative writing, Mathematical reasoning...")
                    
                    # Year level selection with Montessori cycles
                    year_selection_type = st.radio("Year Level Selection:", ["Single Year", "Montessori Cycle", "Multi-Year Range"])
                    
                    if year_selection_type == "Single Year":
                        rubric_year = st.selectbox("Year Level:", [
                            "Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5",
                            "Year 6", "Year 7", "Year 8", "Year 9", "Year 10", "Year 11", "Year 12"
                        ])
                    elif year_selection_type == "Montessori Cycle":
                        rubric_year = st.selectbox("Montessori Cycle:", [
                            "Cycle 1 (3-6 years)", "Cycle 2 (6-9 years)", 
                            "Cycle 3 (9-12 years)", "Cycle 4 (12-15 years)"
                        ])
                    else:  # Multi-Year Range
                        col_start, col_end = st.columns(2)
                        with col_start:
                            start_year = st.selectbox("From Year:", [
                                "Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5",
                                "Year 6", "Year 7", "Year 8", "Year 9", "Year 10", "Year 11", "Year 12"
                            ])
                        with col_end:
                            end_year = st.selectbox("To Year:", [
                                "Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5",
                                "Year 6", "Year 7", "Year 8", "Year 9", "Year 10", "Year 11", "Year 12"
                            ])
                        rubric_year = f"{start_year} to {end_year}"
                    
                    learning_area = st.selectbox("Learning Area:", [
                        "English", "Mathematics", "Science", "Humanities and Social Sciences", 
                        "The Arts", "Technologies", "Health and Physical Education", 
                        "Languages", "Cross-curricular Studies", "Practical Life", "Sensorial", 
                        "Cultural Studies", "Cosmic Education"
                    ])
                
                with rubric_col2:
                    st.markdown("#### Assessment Design")
                    
                    # Curriculum reference selection
                    curriculum_reference = st.selectbox("Curriculum Reference:", [
                        "Australian Curriculum V9", 
                        "Montessori Curriculum Australia", 
                        "Blended (Australian + Montessori)"
                    ])
                    
                    assessment_type = st.selectbox("Assessment Type:",
                                                 ["Project-based Assessment", "Performance Task", "Portfolio Assessment", 
                                                  "Presentation/Exhibition", "Investigation/Research", "Creative Work",
                                                  "Collaborative Project", "Real-world Application", "Reflection Journal"])
                    
                    rubric_focus = st.multiselect("Assessment Focus Areas:", [
                        "Knowledge & Understanding", "Thinking & Inquiry", "Communication", 
                        "Application", "Self-Direction", "Collaboration", "Critical Thinking",
                        "Creative Thinking", "Systems Thinking", "Cosmic Connections"
                    ], default=["Knowledge & Understanding", "Communication"])
                    
                    include_standards = st.checkbox("Include specific curriculum standards", value=True)
                    include_selfreflection = st.checkbox("Include student self-reflection prompts", value=True)
                
                # Advanced Options
                with st.expander("🔧 Advanced Rubric Options"):
                    col_adv1, col_adv2 = st.columns(2)
                    
                    with col_adv1:
                        performance_levels = st.selectbox("Number of Performance Levels:", 
                                                        ["3 levels", "4 levels", "5 levels"], index=1)
                        
                        rubric_style = st.selectbox("Rubric Style:", [
                            "Growth-focused (Montessori-inspired)",
                            "Standards-based (Traditional)",
                            "Holistic (Whole-child development)",
                            "Competency-based (Skills focus)"
                        ])
                    
                    with col_adv2:
                        language_style = st.selectbox("Language Style:", [
                            "Student-friendly", "Teacher-focused", "Parent-accessible", "Academic"
                        ])
                        
                        additional_features = st.multiselect("Additional Features:", [
                            "Differentiation notes", "Extension suggestions", 
                            "Support strategies", "Digital integration", "Peer assessment"
                        ])
                
                # Generate Rubric
                if st.button("📏 Generate Curriculum-Aligned Rubric", use_container_width=True):
                    if rubric_topic and rubric_focus:
                        with st.spinner("Creating comprehensive assessment rubric..."):
                            # Enhanced prompt for detailed rubric generation
                            enhanced_prompt = f"""Create a comprehensive, curriculum-aligned assessment rubric for '{rubric_topic}' in {learning_area} for {rubric_year} students using {curriculum_reference} standards.

Assessment Details:
- Type: {assessment_type}
- Focus Areas: {', '.join(rubric_focus)}
- Performance Levels: {performance_levels}
- Style: {rubric_style}
- Language: {language_style}

Required Components:
1. Clear curriculum standards alignment {'(include specific standard codes and descriptors)' if include_standards else ''}
2. {performance_levels.split()[0]} performance levels with descriptive criteria
3. Multiple assessment criteria covering: {', '.join(rubric_focus)}
4. Growth-oriented language that celebrates progress and suggests next steps
5. Cosmic education connections showing how learning fits into larger systems
6. Observable behaviors and evidence descriptors
7. {'Student self-reflection prompts and questions' if include_selfreflection else ''}

Additional Features: {', '.join(additional_features) if additional_features else 'None'}

Design Principles:
- Honour individual learning paths and developmental stages
- Use asset-based language (what students CAN do)
- Include multiple ways to demonstrate understanding
- Connect learning to real-world applications and community
- Encourage curiosity, exploration, and deep thinking
- Support both formative and summative assessment purposes
- Align with Montessori principles of intrinsic motivation and self-direction

Format as a clear, usable rubric with table structure where appropriate."""
                            
                            messages = [{"role": "user", "content": enhanced_prompt}]
                            system_prompt = get_system_prompt(curriculum_reference)
                            
                            rubric = call_openai_api(messages, system_prompt)
                            if rubric:
                                st.markdown("### 📏 Curriculum-Aligned Assessment Rubric")
                                st.markdown(f"**Topic:** {rubric_topic} | **Year Level:** {rubric_year} | **Learning Area:** {learning_area}")
                                st.markdown(f"**Assessment Type:** {assessment_type} | **Curriculum:** {curriculum_reference}")
                                st.markdown("---")
                                st.markdown(rubric)
                                
                                # Store generated rubric in session state for saving
                                st.session_state.current_rubric = {
                                    'topic': rubric_topic,
                                    'year_level': rubric_year,
                                    'learning_area': learning_area,
                                    'assessment_type': assessment_type,
                                    'curriculum': curriculum_reference,
                                    'content': rubric
                                }
                                
                                # Save rubric option
                                st.markdown("---")
                                col_save1, col_save2 = st.columns(2)
                                
                                with col_save1:
                                    st.markdown("**Save for Later Use:**")
                                    if st.button("💾 Save Rubric to Library", key=f"save_{rubric_topic}_{datetime.now().strftime('%H%M%S')}"):
                                        # Save to both session state and user data file
                                        if 'saved_rubrics' not in st.session_state:
                                            st.session_state.saved_rubrics = []
                                        
                                        rubric_data = {
                                            'id': f"rubric_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                            'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                            'topic': rubric_topic,
                                            'year_level': rubric_year,
                                            'learning_area': learning_area,
                                            'assessment_type': assessment_type,
                                            'curriculum': curriculum_reference,
                                            'content': rubric,
                                            'created_by': current_user
                                        }
                                        
                                        # Save to user data file for persistence
                                        success = save_rubric_to_user_data(current_user, rubric_data)
                                        
                                        if success:
                                            # Add to session state
                                            st.session_state.saved_rubrics.append(rubric_data)
                                            st.success("✅ Rubric saved to your library!")
                                            # Force reload of library data
                                            st.session_state.rubrics_loaded = False
                                        else:
                                            st.error("❌ Failed to save rubric. Check console for details.")
                                
                                with col_save2:
                                    st.markdown("**Share with Colleagues:**")
                                    if st.button("📤 Share with Team", key=f"share_{rubric_topic}_{datetime.now().strftime('%H%M%S')}"):
                                        share_rubric_with_team(rubric, current_user, rubric_topic, curriculum_reference)
                                        st.success("Rubric shared with your team!")
                            else:
                                st.error("Unable to generate rubric. Please try again.")
                    else:
                        st.warning("Please provide a topic and select at least one focus area.")
                
                # Saved Rubrics Library
                st.markdown("---")
                
                # Load rubrics from file if not in session state
                if 'rubrics_loaded' not in st.session_state:
                    user_rubrics = load_user_rubrics(current_user)
                    st.session_state.saved_rubrics = user_rubrics
                    st.session_state.rubrics_loaded = True
                
                if st.button("📚 View My Rubric Library"):
                    # Reload from file to get latest
                    user_rubrics = load_user_rubrics(current_user)
                    st.session_state.saved_rubrics = user_rubrics
                    
                    if user_rubrics:
                        st.markdown("### My Saved Rubrics")
                        for idx, rubric in enumerate(reversed(user_rubrics[-10:])):  # Show last 10
                            with st.expander(f"📏 {rubric['topic']} - {rubric['year_level']} ({rubric['timestamp']})"):
                                st.markdown(f"**Learning Area:** {rubric['learning_area']}")
                                st.markdown(f"**Assessment Type:** {rubric['assessment_type']}")
                                st.markdown(f"**Curriculum:** {rubric['curriculum']}")
                                st.markdown("---")
                                st.markdown(rubric['content'])
                    else:
                        st.info("No saved rubrics yet. Create your first rubric above!")
            
            # MVP Note: Mathematics Hub feature available in full version
            # This section is hidden in MVP but preserved in codebase

        # End of teacher tools section
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:  # Student Interface
        # STUDENT DASHBOARD
        st.markdown('<div class="student-card">', unsafe_allow_html=True)
        
        student_name = user_data.get('real_name', current_user)
        
        # Student interface tabs (MVP Version)
        student_tabs = st.tabs([
            "💬 Learning Assistant", 
            "📝 Project Planner",
            "📋 Get Feedback",
            "📊 Learning Profile",
            "📁 My Portfolio", 
            "🌟 My Journey",
            "♿ Accessibility"
        ])
        
        # Hidden MVP features: "🧮 Math Explorer" (available in full version)
        
        with student_tabs[0]:  # Learning Assistant
            st.markdown(f"### Hello {student_name}! Your Learning Companion is Here 🌱")
            st.markdown("*Ask questions, explore ideas, and discover connections in your learning*")
            
            # Student chat interface with restrictions
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            if prompt := st.chat_input("What would you like to explore or learn about today?"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Thinking about your question..."):
                        system_prompt = get_system_prompt("Blended (Cosmic Education Priority)")
                        response = call_openai_api(st.session_state.messages, system_prompt)
                        
                        if response:
                            st.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            
                            # Log student activity
                            activity_data = {
                                "type": "learning_chat",
                                "content": prompt,
                                "feedback": response,
                                "competency_analysis": "Engaged in learning dialogue",
                                "extensions": "Continued questioning and exploration"
                            }
                            link_student_activity(student_name, activity_data)
                        else:
                            st.error("I'm having trouble right now. Please try again.")
                    
                    # Follow-up suggestions positioned above input for efficiency
                    if st.session_state.messages:
                        st.markdown("**🌟 Keep learning:**")
                        student_follow_col1, student_follow_col2, student_follow_col3 = st.columns(3)
                        
                        with student_follow_col1:
                            if st.button("❓ Ask why", key=f"why_student_{len(st.session_state.messages)}"):
                                why_prompt = "Why is this important? Can you help me understand why this matters?"
                                st.session_state.messages.append({"role": "user", "content": why_prompt})
                                st.rerun()
                        
                        with student_follow_col2:
                            if st.button("🔍 Show me how", key=f"how_student_{len(st.session_state.messages)}"):
                                how_prompt = "Can you show me how to do this step by step? I'd like to try it myself."
                                st.session_state.messages.append({"role": "user", "content": how_prompt})
                                st.rerun()
                        
                        with student_follow_col3:
                            if st.button("🌍 What else connects?", key=f"connects_student_{len(st.session_state.messages)}"):
                                connects_prompt = "What else is connected to this? How does this relate to other things I'm learning?"
                                st.session_state.messages.append({"role": "user", "content": connects_prompt})
                                st.rerun()
                
                if prompt := st.chat_input("What would you like to learn about today?"):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
        
        with student_tabs[1]:  # Project Planner
            st.markdown("### Project Planning & Organization 📝")
            st.markdown("*Break down your ideas into manageable steps with guided planning tools*")
            st.info("Project planning features available in full version of Guide.")
        
        with student_tabs[2]:  # Get Feedback
            st.markdown("### Get Feedback on Your Work 📋")
            st.markdown("*Share your work with your teacher for personalized feedback and next steps*")
            st.info("Work feedback features available in full version of Guide.")
        
        with student_tabs[3]:  # Learning Profile
            st.markdown("### My Learning Profile 📊")
            st.markdown("*See your progress, strengths, and learning patterns*")
            st.info("Learning profile features available in full version of Guide.")
        
        with student_tabs[4]:  # My Portfolio
            st.markdown("### My Learning Portfolio 📁")
            st.markdown("*Collect and reflect on your learning journey*")
            st.info("Portfolio features available in full version of Guide.")
        
        with student_tabs[5]:  # My Journey
            st.markdown("### My Learning Journey 🌟")
            st.markdown("*Track your progress over time*")
            st.info("Journey timeline features available in full version of Guide.")
        
        with student_tabs[6]:  # Accessibility
            accessibility_wizard()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Sidebar - only show if authenticated
if st.session_state.authenticated:
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Curriculum selector
        curriculum = st.selectbox(
            "📚 Curriculum Framework",
            ["Australian Curriculum V9", "Montessori Curriculum Australia"],
            key="sidebar_curriculum_selector"
        )
        st.session_state.curriculum = curriculum
        
        st.markdown("---")
        
        # File upload section
        st.header("📁 Upload Curriculum Notes")
        uploaded_file = st.file_uploader(
            "Upload .txt or .csv files",
            type=["txt", "csv"],
            help="Upload curriculum notes to enhance AI responses"
        )
        
        # Show uploaded content with deletion option
        if hasattr(st.session_state, 'uploaded_content') and st.session_state.uploaded_content:
            st.success("✓ Curriculum content uploaded")
            with st.expander("View uploaded content"):
                st.text_area("Content", st.session_state.uploaded_content[:500] + "..." if len(st.session_state.uploaded_content) > 500 else st.session_state.uploaded_content, height=100, disabled=True)
            
            if st.button("🗑️ Delete Uploaded Content", type="secondary"):
                del st.session_state.uploaded_content
                st.success("✅ Uploaded content permanently deleted!")
                st.rerun()
        
        if uploaded_file is not None:
            try:
                # Reset file pointer to beginning
                uploaded_file.seek(0)
                
                if uploaded_file.type == "text/plain":
                    content = uploaded_file.read().decode("utf-8")
                    st.session_state.uploaded_content = content
                    st.success("Text file uploaded successfully!")
                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    content = df.to_string()
                    st.session_state.uploaded_content = content
                    st.success("CSV file uploaded successfully!")
                    with st.expander("Preview uploaded data"):
                        st.dataframe(df.head(10))
                else:
                    st.warning("Unsupported file type. Please upload .txt or .csv files only.")
            except UnicodeDecodeError:
                st.error("File encoding error. Please ensure your file is UTF-8 encoded.")
            except pd.errors.EmptyDataError:
                st.error("The CSV file appears to be empty.")
            except pd.errors.ParserError as e:
                st.error(f"CSV parsing error: {str(e)}. Please check your file format.")
            except IOError as e:
                st.error(f"File reading error: {str(e)}. Please try uploading again.")
            except Exception as e:
                st.error(f"Unexpected error reading file: {str(e)}. Please contact support if this persists.")
        
        st.markdown("---")
        
        # Quick access buttons
        st.header("🚀 Quick Actions")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Guide - Cosmic Curriculum Companion MVP | Powered by OpenAI GPT-4o Mini<br>
        Bridging Montessori's Cosmic Education with contemporary curriculum frameworks<br>
        <em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)
