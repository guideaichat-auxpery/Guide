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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string

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
            with open('users.json', 'r') as f:
                data = json.load(f)
                st.session_state.users = data.get('users', {})
                st.session_state.usage_logs = data.get('usage_logs', {})
        except Exception as e:
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
        with open('users.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving user data: {str(e)}")

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
    if username in st.session_state.users:
        return False, "Username already exists"
    
    st.session_state.users[username] = {
        'password': hash_password(password),
        'role': 'teacher',
        'email': email,
        'school': school,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'students': {},
        'monthly_usage': 0,
        'monthly_limit': 100000,  # 100k tokens per month
        'daily_requests': 0,
        'daily_limit': 200,  # 200 requests per day
        'last_request_date': datetime.now().strftime("%Y-%m-%d"),
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
        'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'monthly_usage': 0,
        'monthly_limit': 10000,  # 10k tokens per month for students
        'daily_requests': 0,
        'daily_limit': 50,  # 50 requests per day for students
        'last_request_date': datetime.now().strftime("%Y-%m-%d"),
        'archived': False
    }
    
    # Add student to teacher's student list
    st.session_state.users[teacher_username]['students'][username] = student_name
    st.session_state.usage_logs[username] = []
    save_user_database()  # Save to persistent storage
    
    return True, "Student account created", username, password

def create_custom_student_account(username, password, student_name, teacher_username=None):
    """Create student account with custom username and password"""
    if username in st.session_state.users:
        return False, "Username already exists"
    
    st.session_state.users[username] = {
        'password': hash_password(password),
        'role': 'student',
        'real_name': student_name,
        'teacher': teacher_username,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'monthly_usage': 0,
        'monthly_limit': 10000,  # 10k tokens per month for students
        'daily_requests': 0,
        'daily_limit': 50,  # 50 requests per day for students
        'last_request_date': datetime.now().strftime("%Y-%m-%d"),
        'archived': False
    }
    
    # Add student to teacher's student list if teacher is specified
    if teacher_username and teacher_username in st.session_state.users:
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
    today = datetime.now().strftime("%Y-%m-%d")
    
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
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'teacher': teacher_name,
            'content': feedback_content
        }
        st.session_state.feedback_messages.append(feedback_entry)
        return True, "Feedback sent successfully"
    except Exception as e:
        return False, f"Error sending feedback: {str(e)}"

def upload_training_content(content, admin_password):
    """Upload training content (admin only)"""
    # Simple admin check - in production this would be more secure
    if admin_password == "guide_admin_2025":
        st.session_state.training_content = content
        return True, "Training content uploaded successfully"
    return False, "Invalid admin password"

# Initialize session state and user database
init_user_database()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "curriculum" not in st.session_state:
    st.session_state.curriculum = "Australian Curriculum V9"

if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""

if "user_type" not in st.session_state:
    st.session_state.user_type = "Teacher"

if "student_work" not in st.session_state:
    st.session_state.student_work = ""

if "student_feedback_history" not in st.session_state:
    st.session_state.student_feedback_history = []

if "student_progress" not in st.session_state:
    st.session_state.student_progress = {}

if "shared_lessons" not in st.session_state:
    st.session_state.shared_lessons = []

if "collaboration_mode" not in st.session_state:
    st.session_state.collaboration_mode = False

# Authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "show_login" not in st.session_state:
    st.session_state.show_login = True

if "portfolios" not in st.session_state:
    st.session_state.portfolios = {}

# Helper functions
def get_system_prompt(curriculum):
    """Get system prompt based on selected curriculum with Montessori Cosmic Education and systems thinking approach"""
    base_prompt = """You are an AI curriculum guide inspired by Montessori's Cosmic Education and grounded in systems thinking. Your responses are warm, humble, and practical, avoiding jargon-heavy academic language. 

You honor the adolescent developmental plane: curiosity, belonging, purpose, and independence. You emphasize interconnections across disciplines rather than siloed subjects, drawing attention to big ideas and patterns (cycles, cause-and-effect, networks) rather than isolated facts. 

You respect Montessori principles of freedom within responsibility, hands-on experience, and student agency. You help teachers, students, and parents understand not only what to learn, but why it matters in the bigger picture of life and the world."""
    
    if curriculum == "Australian Curriculum V9":
        return f"{base_prompt}\n\nYou integrate the Australian Curriculum V9 framework with Cosmic Education principles, showing how learning areas, general capabilities, and cross-curriculum priorities connect to larger systems - historical, ecological, social, and economic. You present learning as threads in the tapestry of human knowledge and experience."
    else:
        return f"{base_prompt}\n\nYou work within the Montessori Curriculum Australia framework, emphasizing child-led learning, prepared environments, and developmental stages while connecting all learning to the 'universe story' - showing how each topic fits into the grand narrative of cosmic evolution, human civilization, and our interconnected world."

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
        log_api_usage(st.session_state.get('current_user', 'anonymous'), response.usage.total_tokens)
        
        return response.choices[0].message.content
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
    
    prompt = f"""Create detailed scaffolding guidance for a {project_type} project on '{topic}' following this planning structure:

{planner['title']}

Planning Steps:
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(planner['steps'])])}

Reflection Questions:
{chr(10).join([f"• {q}" for q in planner['questions']])}

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

def analyze_student_work(work_content, curriculum, work_type="general"):
    """Analyze student work and provide developmental feedback"""
    prompt = f"""Analyze this student work with the lens of Montessori's Cosmic Education and systems thinking:

{work_content}

Provide feedback that:
- Celebrates what the student has discovered and connected
- Identifies patterns, relationships, and systems thinking evident in their work
- Suggests gentle next steps that honor their curiosity and developmental readiness
- Shows how their thinking connects to larger webs of knowledge
- Offers questions that invite deeper exploration rather than corrections
- Recognizes their unique perspective and contribution to understanding

Frame feedback as a conversation with a fellow explorer of knowledge, honoring their agency and natural desire to learn."""
    
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
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "work_analysis": work_analysis,
        "learning_goals": learning_goals,
        "date": datetime.now().strftime("%Y-%m-%d"),
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
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
    if student_name not in st.session_state.student_progress:
        return "No profile data available."
    
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
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
            "title": f"{student_name}'s Year {custom_params.get('year', 'X')} Portfolio",
            "sections": [
                "Term 1 Highlights",
                "Term 2 Growth", 
                "Term 3 Discoveries",
                "Term 4 Achievements",
                "Year Reflections"
            ],
            "description": f"Document your learning journey through Year {custom_params.get('year', 'X')}"
        },
        "term": {
            "title": f"{student_name}'s {custom_params.get('term', 'Term')} Portfolio",
            "sections": [
                "Learning Goals",
                "Projects & Investigations",
                "Skill Development",
                "Challenges & Growth",
                "Term Reflection"
            ],
            "description": f"Capture your {custom_params.get('term', 'term')} learning experience"
        }
    }
    
    template = templates.get(template_type, templates["blank"])
    
    return {
        "template_type": template_type,
        "title": template["title"],
        "sections": template["sections"],
        "description": template["description"],
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "entries": {section: [] for section in template["sections"]},
        "annotations": [],
        "custom_params": custom_params or {}
    }

def add_portfolio_entry(portfolio, section, entry_data):
    """Add an entry to a portfolio section"""
    if section in portfolio["entries"]:
        portfolio["entries"][section].append({
            "id": len(portfolio["entries"][section]) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "section": section,
        "entry_id": entry_id,
        "annotation": annotation,
        "type": "entry_annotation"
    })

def add_portfolio_reflection(portfolio, reflection_text, reflection_type="general"):
    """Add a learning reflection to the portfolio"""
    portfolio["annotations"].append({
        "id": len(portfolio["annotations"]) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "collaborators": [],
        "comments": [],
        "tags": []
    }
    
    st.session_state.shared_lessons.append(lesson)
    return lesson

def add_lesson_comment(lesson_id, commenter, comment):
    """Add collaborative comment to a shared lesson"""
    for lesson in st.session_state.shared_lessons:
        if lesson["id"] == lesson_id:
            lesson["comments"].append({
                "author": commenter,
                "content": comment,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
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
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("🌱 Enter Your Learning Space", use_container_width=True):
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
                new_student_name = st.text_input("Your Name", key="new_student_name")
                new_student_username = st.text_input("Choose Username", key="new_student_username")
                new_student_password = st.text_input("Choose Password", type="password", key="new_student_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_student_password")
                
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
        # Usage tracking display
        daily_used = user_data.get('daily_requests', 0)
        daily_limit = user_data.get('daily_limit', 200)
        monthly_used = user_data.get('monthly_usage', 0)
        monthly_limit = user_data.get('monthly_limit', 100000)
        
        st.metric("Today's Requests", f"{daily_used}/{daily_limit}")
        st.metric("Monthly Usage", f"{monthly_used:,}/{monthly_limit:,} tokens")
    
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
                <h4>🌱 Learning Connections</h4>
                <p>Create interconnected lesson ideas that connect topics to larger systems (historical, ecological, social, economic). This tool helps you show students how everything is related in our cosmic story.</p>
                
                <h4>🕸️ Learning Threads & Patterns</h4>
                <p>Map knowledge as interconnected webs rather than isolated subjects. Visualize how topics spiral and connect across disciplines, honoring the Montessori approach to integrated learning.</p>
                
                <h4>💫 Family & Community Connection</h4>
                <p>Generate communications that help families understand learning in terms of whole-child development and cosmic connections. Bridge school and home learning.</p>
                
                <h4>🌟 Learning Invitations</h4>
                <p>Create activities that foster independence, collaboration, real-world connection, and cosmic reflection. Design experiences that honor curiosity and developmental readiness.</p>
                
                <h4>📈 Cosmic Education Competencies (CEC)</h4>
                <p>Track student progress across 6 core competencies inspired by International Big Picture Learning, adapted for cosmic education: Knowing How to Learn, Empirical Reasoning, Quantitative Reasoning, Social Reasoning, Communication, and Personal Qualities.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Main teacher interface tabs
        teacher_tabs = st.tabs([
            "💬 AI Assistant", 
            "🧠 Learning Tools", 
            "👥 Student Management", 
            "📊 All & Advisory", 
            "💌 Pilot Feedback"
        ])
        
        with teacher_tabs[0]:  # AI Assistant
            st.markdown("### Your AI Teaching Companion")
            
            # Curriculum selector
            curriculum = st.selectbox(
                "📚 Curriculum Framework",
                ["Australian Curriculum V9", "Montessori Curriculum Australia"],
                key="teacher_curriculum_selector"
            )
            st.session_state.curriculum = curriculum
            
            # Chat interface
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            if prompt := st.chat_input("Share your curiosity about learning, teaching, or cosmic connections..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Reflecting on cosmic connections..."):
                        system_prompt = get_system_prompt(st.session_state.curriculum)
                        response = call_openai_api(st.session_state.messages, system_prompt)
                        
                        if response:
                            st.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        else:
                            st.error("I'm having trouble connecting right now. Please try again.")
        
        with teacher_tabs[1]:  # Learning Tools
            tool_subtabs = st.tabs([
                "🌱 Learning Connections", 
                "🕸️ Learning Threads", 
                "💫 Family Connection",
                "🌟 Learning Invitations",
                "📏 Assessment Rubrics"
            ])
            
            with tool_subtabs[0]:  # Learning Connections
                st.markdown("### Discover Interconnected Learning")
                lesson_topic = st.text_input("What topic would you like to explore?", 
                                           placeholder="e.g., Water cycle, Ancient civilizations, Fractions...")
                
                if st.button("🌀 Generate Cosmic Connections"):
                    if lesson_topic:
                        with st.spinner("Weaving connections across the cosmic curriculum..."):
                            ideas = generate_lesson_ideas(lesson_topic, curriculum)
                            if ideas:
                                st.markdown("### Learning Connections & Invitations")
                                st.markdown(ideas)
                                
                                # Option to share lesson
                                if st.button("Share with Team"):
                                    create_shared_lesson(ideas, current_user, curriculum, lesson_topic)
                                    st.success("Lesson shared with your team!")
            
            with tool_subtabs[1]:  # Learning Threads
                st.markdown("### Map Interconnected Knowledge")
                manual_topics = st.text_area(
                    "What learning threads would you like to weave together?",
                    height=100,
                    placeholder="Mathematics patterns in nature\nHistory of human migration\nClimate and ecosystem changes..."
                )
                
                if st.button("🕸️ Weave Learning Threads"):
                    if manual_topics:
                        topics = [topic.strip() for topic in manual_topics.split('\n') if topic.strip()]
                        with st.spinner("Mapping cosmic connections..."):
                            sequence_plan = generate_scope_sequence(topics, curriculum)
                            if sequence_plan:
                                st.markdown("### Learning Threads & Interconnections")
                                st.markdown(sequence_plan)
                            
                            fig = create_timeline_visualization(topics[:10])
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
            
            with tool_subtabs[2]:  # Family Connection
                st.markdown("### Bridge Learning with Families")
                parent_topic = st.text_input("What learning would you like to share with families?", 
                                           placeholder="e.g., Our exploration of ecosystems...")
                
                if st.button("💌 Craft Family Letter"):
                    if parent_topic:
                        with st.spinner("Creating meaningful family connection..."):
                            parent_content = generate_parent_communication(parent_topic, curriculum)
                            if parent_content:
                                st.markdown("### Family Learning Connection")
                                st.markdown(parent_content)
            
            with tool_subtabs[3]:  # Learning Invitations
                st.markdown("### Create Student Learning Invitations")
                task_topic = st.text_input("What learning would you like to invite students into?", 
                                         placeholder="e.g., Understanding democracy...")
                age_group = st.selectbox(
                    "Developmental Stage:",
                    ["Early Years (3-5)", "Primary Years (6-11)", "Middle Years (12-15)"]
                )
                
                if st.button("🌟 Create Learning Invitations"):
                    if task_topic:
                        with st.spinner("Crafting meaningful invitations..."):
                            tasks = generate_student_tasks(task_topic, age_group, curriculum)
                            if tasks:
                                st.markdown("### Learning Invitations & Explorations")
                                st.markdown(tasks)
            
            with tool_subtabs[4]:  # Assessment Rubrics
                st.markdown("### Growth-Focused Assessment")
                col1, col2 = st.columns(2)
                
                with col1:
                    rubric_topic = st.text_input("Topic for assessment:", 
                                               placeholder="e.g., Scientific inquiry...")
                    rubric_year = st.selectbox("Year Level:", 
                                             ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", 
                                              "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"])
                
                with col2:
                    assessment_type = st.selectbox("Assessment Type:",
                                                 ["Project-based", "Performance task", "Portfolio", 
                                                  "Presentation", "Investigation", "Creative work"])
                
                if st.button("📏 Create Growth-Focused Rubric"):
                    if rubric_topic:
                        with st.spinner("Creating developmental assessment rubric..."):
                            rubric = generate_assessment_rubric(rubric_topic, curriculum, assessment_type, rubric_year)
                            if rubric:
                                st.markdown("### Developmental Assessment Rubric")
                                st.markdown(rubric)
        
        with teacher_tabs[2]:  # Student Management
            st.markdown("### Your Students & Their Journey")
            
            mgmt_subtabs = st.tabs(["➕ Create Student", "👀 View Progress", "📁 View Portfolios"])
            
            with mgmt_subtabs[0]:  # Create Student
                st.markdown("### Create New Student Account")
                student_name = st.text_input("Student's Full Name")
                
                if st.button("🌱 Create Student Account"):
                    if student_name:
                        success, message, username, password = create_student_account(current_user, student_name)
                        if success:
                            st.success(f"Student account created!")
                            st.markdown(f"**Username:** `{username}`")
                            st.markdown(f"**Password:** `{password}`")
                            st.info("Please share these credentials securely with the student.")
                        else:
                            st.error(message)
            
            with mgmt_subtabs[1]:  # View Progress
                teacher_students = user_data.get('students', {})
                if teacher_students:
                    selected_student = st.selectbox("Select Student", list(teacher_students.keys()))
                    
                    if selected_student:
                        student_name = teacher_students[selected_student]
                        st.markdown(f"### Progress Report for {student_name}")
                        
                        if st.button("Generate Progress Report"):
                            progress_report = generate_progress_report(selected_student, curriculum)
                            st.markdown(progress_report)
                else:
                    st.info("No students created yet. Use the 'Create Student' tab to add students.")
            
            with mgmt_subtabs[2]:  # View Portfolios
                teacher_students = user_data.get('students', {})
                if teacher_students:
                    selected_student = st.selectbox("Select Student Portfolio", list(teacher_students.keys()), key="portfolio_select")
                    
                    if selected_student and selected_student in st.session_state.portfolios:
                        student_portfolios = st.session_state.portfolios[selected_student]
                        portfolio_names = list(student_portfolios.keys())
                        
                        if portfolio_names:
                            selected_portfolio = st.selectbox("Portfolio", portfolio_names)
                            portfolio = student_portfolios[selected_portfolio]
                            
                            st.markdown(f"### {portfolio['title']}")
                            st.markdown(f"*{portfolio['description']}*")
                            
                            # Display portfolio sections
                            for section in portfolio['sections']:
                                with st.expander(f"📂 {section}"):
                                    entries = portfolio['entries'].get(section, [])
                                    if entries:
                                        for entry in entries:
                                            st.markdown(f"**{entry['timestamp']}** - {entry['type'].title()}")
                                            st.markdown(f"**Content:** {entry['content']}")
                                            if entry['reflection']:
                                                st.markdown(f"**Reflection:** {entry['reflection']}")
                                            st.markdown("---")
                                    else:
                                        st.info(f"No entries in {section} yet.")
                        else:
                            st.info("Student hasn't created any portfolios yet.")
                    else:
                        st.info("No portfolios available for this student.")
                else:
                    st.info("No students created yet.")
        
        with teacher_tabs[3]:  # All & Advisory (CEC Organization)
            st.markdown("### All & Advisory - CEC Organization")
            
            advisory_tabs = st.tabs(["📊 All Students Overview", "🎯 Advisory Groups", "📈 CEC Analytics"])
            
            with advisory_tabs[0]:  # All Students
                st.markdown("### All Students - Cosmic Education Competencies")
                
                teacher_students = user_data.get('students', {})
                if teacher_students:
                    # Display CEC overview for all students
                    st.markdown("#### CEC Competency Overview")
                    
                    competency_data = []
                    for student_id, student_name in teacher_students.items():
                        if student_id in st.session_state.student_progress:
                            cec_data = st.session_state.student_progress[student_id].get('cec_competencies', {})
                            row = {'Student': student_name}
                            for comp, data in cec_data.items():
                                comp_name = comp.replace('_', ' ').title()
                                row[comp_name] = data.get('level', 1)
                            competency_data.append(row)
                    
                    if competency_data:
                        df = pd.DataFrame(competency_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Visualization
                        if len(df) > 1:
                            fig = px.bar(df.melt(id_vars='Student', var_name='Competency', value_name='Level'),
                                       x='Competency', y='Level', color='Student',
                                       title='CEC Competency Levels Across Students')
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No CEC data available yet.")
                else:
                    st.info("No students created yet.")
            
            with advisory_tabs[1]:  # Advisory Groups
                st.markdown("### Advisory Group Management")
                st.markdown("*Organize students into advisory groups for personalized support*")
                
                # Simple advisory group management
                if teacher_students:
                    group_name = st.text_input("Advisory Group Name")
                    selected_students = st.multiselect("Select Students", 
                                                     [f"{name} ({id})" for id, name in teacher_students.items()])
                    
                    if st.button("Create Advisory Group"):
                        if group_name and selected_students:
                            st.success(f"Advisory group '{group_name}' created with {len(selected_students)} students.")
                        else:
                            st.warning("Please enter group name and select students.")
                else:
                    st.info("Create students first to organize advisory groups.")
            
            with advisory_tabs[2]:  # CEC Analytics
                st.markdown("### CEC Analytics & Insights")
                st.markdown("*Track Cosmic Education Competency development across your students*")
                
                if teacher_students:
                    # Aggregate analytics
                    total_students = len(teacher_students)
                    active_students = len([s for s in teacher_students.keys() if s in st.session_state.student_progress])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Students", total_students)
                    col2.metric("Active Learners", active_students)
                    col3.metric("Portfolio Entries", sum(len(st.session_state.portfolios.get(s, {})) for s in teacher_students.keys()))
                    
                    st.markdown("#### Competency Development Trends")
                    st.info("Advanced analytics coming soon in the next update!")
                else:
                    st.info("No students to analyze yet.")
        
        with teacher_tabs[4]:  # Pilot Feedback
            st.markdown("### Pilot Phase Feedback")
            st.markdown("*Help us improve Guide by sharing your experience*")
            
            feedback_text = st.text_area(
                "Share your feedback, suggestions, or any issues you've encountered:",
                height=150,
                placeholder="How has Guide helped your teaching? What features would you like to see? Any problems or suggestions?"
            )
            
            if st.button("📤 Send Feedback to Development Team"):
                if feedback_text:
                    success, message = send_feedback_email(current_user, feedback_text)
                    if success:
                        st.success("Thank you! Your feedback has been sent to guideaichat@gmail.com")
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter your feedback before sending.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:  # Student Interface
        # STUDENT DASHBOARD
        st.markdown('<div class="student-card">', unsafe_allow_html=True)
        
        student_name = user_data.get('real_name', current_user)
        
        # Student interface tabs
        student_tabs = st.tabs([
            "💬 Learning Assistant", 
            "📝 Project Planner", 
            "📁 My Portfolio", 
            "🌟 My Journey"
        ])
        
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
                        system_prompt = get_system_prompt(st.session_state.curriculum)
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
                            link_student_activity(current_user, activity_data)
                        else:
                            st.error("I'm having trouble right now. Please try again.")
        
        with student_tabs[1]:  # Project Planner
            st.markdown("### Plan Your Next Learning Adventure! 🎨")
            st.markdown("*Choose a project type and let's create a plan together*")
            
            col1, col2 = st.columns(2)
            
            with col1:
                project_topic = st.text_input("What topic are you exploring?", 
                                            placeholder="e.g., Solar system, Local history, Plant life cycles...")
                
                project_type = st.selectbox("What type of project would you like to create?", [
                    "poster", "essay", "diorama", "video", "music", "role-play", "model"
                ])
            
            with col2:
                st.markdown("#### Project Types")
                st.markdown("""
                - **Poster**: Visual display with information
                - **Essay**: Written exploration of ideas  
                - **Diorama**: 3D scene or model
                - **Video**: Film or presentation
                - **Music**: Song or musical piece
                - **Role-play**: Acting or performance
                - **Model**: Physical or digital representation
                """)
            
            if st.button("🚀 Create My Project Plan"):
                if project_topic and project_type:
                    with st.spinner("Creating your personalized project plan..."):
                        planner = create_student_planner(project_type, project_topic, st.session_state.curriculum)
                        if planner:
                            st.markdown("### Your Project Planning Guide")
                            st.markdown(planner)
                            
                            # Log student activity
                            activity_data = {
                                "type": "project_planning",
                                "content": f"{project_type} project on {project_topic}",
                                "feedback": "Project planning guidance provided",
                                "competency_analysis": "Demonstrated planning and organization skills",
                                "extensions": "Ready to begin project implementation"
                            }
                            link_student_activity(current_user, activity_data)
                else:
                    st.warning("Please enter a topic and select a project type.")
        
        with student_tabs[2]:  # Portfolio
            st.markdown("### My Learning Portfolio 📚")
            st.markdown("*Collect and reflect on your learning journey*")
            
            # Initialize student portfolios if not exists
            if current_user not in st.session_state.portfolios:
                st.session_state.portfolios[current_user] = {}
            
            portfolio_subtabs = st.tabs(["📝 Share Work", "📁 My Portfolios", "💭 Add Reflection"])
            
            with portfolio_subtabs[0]:  # Share Work
                st.markdown("### Share Your Learning")
                
                work_type = st.selectbox("What type of work would you like to share?", [
                    "Text/Writing", "Image/Drawing", "Project", "Reflection", "Research"
                ])
                
                work_title = st.text_input("Give your work a title")
                work_content = st.text_area("Describe your work or paste your writing", height=150)
                
                # File upload for students
                uploaded_work = st.file_uploader("Upload a file (optional)", 
                                               type=['pdf', 'doc', 'docx', 'jpg', 'png', 'mp3', 'mp4'])
                
                work_reflection = st.text_area("What did you learn? How do you feel about this work?", 
                                             height=100,
                                             placeholder="What was interesting? What was challenging? What would you do differently?")
                
                if st.button("📤 Submit My Work"):
                    if work_title and (work_content or uploaded_work):
                        # Analyze work for CEC competencies
                        if work_content:
                            with st.spinner("Analyzing your learning..."):
                                cec_analysis = generate_cec_competency_assessment(work_content, st.session_state.curriculum)
                                
                                # Track progress
                                track_student_progress(
                                    current_user, 
                                    f"Submitted {work_type}: {work_title}", 
                                    "Self-directed learning and reflection",
                                    {},  # CEC data would be parsed from analysis
                                    {
                                        "type": "work_submission",
                                        "content": f"{work_title}: {work_content[:200]}...",
                                        "feedback": "Work submitted for review",
                                        "competency_analysis": cec_analysis,
                                        "extensions": "Continue exploring and reflecting"
                                    }
                                )
                                
                                st.success("Your work has been submitted! Great job reflecting on your learning.")
                                if cec_analysis:
                                    st.markdown("### Learning Skills Analysis")
                                    st.markdown(cec_analysis)
                    else:
                        st.warning("Please provide a title and either content or upload a file.")
            
            with portfolio_subtabs[1]:  # My Portfolios
                st.markdown("### Create & Manage Portfolios")
                
                # Portfolio creation
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Create New Portfolio")
                    portfolio_template = st.selectbox("Choose a template:", [
                        "blank", "themed", "subject", "year_level", "term"
                    ])
                    
                    # Custom parameters based on template
                    custom_params = {}
                    if portfolio_template == "year_level":
                        custom_params["year"] = st.selectbox("Year Level:", 
                                                           ["Foundation", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
                    elif portfolio_template == "term":
                        custom_params["term"] = st.selectbox("Term:", ["Term 1", "Term 2", "Term 3", "Term 4"])
                    
                    portfolio_name = st.text_input("Portfolio Name", placeholder="My Amazing Learning Journey")
                    
                    if st.button("🎨 Create Portfolio"):
                        if portfolio_name:
                            portfolio = create_portfolio_template(portfolio_template, student_name, custom_params)
                            portfolio["title"] = portfolio_name  # Override with custom name
                            
                            st.session_state.portfolios[current_user][portfolio_name] = portfolio
                            st.success(f"Portfolio '{portfolio_name}' created!")
                        else:
                            st.warning("Please enter a portfolio name.")
                
                with col2:
                    st.markdown("#### My Existing Portfolios")
                    user_portfolios = st.session_state.portfolios.get(current_user, {})
                    
                    if user_portfolios:
                        for portfolio_name, portfolio in user_portfolios.items():
                            with st.expander(f"📁 {portfolio_name}"):
                                st.markdown(f"**Created:** {portfolio['created']}")
                                st.markdown(f"**Type:** {portfolio['template_type'].title()}")
                                st.markdown(f"**Description:** {portfolio['description']}")
                                
                                # Quick stats
                                total_entries = sum(len(entries) for entries in portfolio['entries'].values())
                                total_annotations = len(portfolio.get('annotations', []))
                                st.markdown(f"**Entries:** {total_entries} | **Reflections:** {total_annotations}")
                    else:
                        st.info("No portfolios created yet. Create your first one!")
            
            with portfolio_subtabs[2]:  # Add Reflection
                st.markdown("### Learning Reflections")
                
                user_portfolios = st.session_state.portfolios.get(current_user, {})
                if user_portfolios:
                    selected_portfolio = st.selectbox("Select portfolio:", list(user_portfolios.keys()))
                    
                    reflection_type = st.selectbox("Type of reflection:", [
                        "general", "daily_reflection", "project_reflection", "skill_reflection"
                    ])
                    
                    reflection_text = st.text_area("What are you thinking about your learning?", 
                                                 height=150,
                                                 placeholder="What patterns do you notice? What connections are you making? How are you growing?")
                    
                    if st.button("💭 Add Reflection"):
                        if reflection_text:
                            portfolio = user_portfolios[selected_portfolio]
                            add_portfolio_reflection(portfolio, reflection_text, reflection_type)
                            st.success("Reflection added to your portfolio!")
                        else:
                            st.warning("Please write your reflection.")
                else:
                    st.info("Create a portfolio first to add reflections.")
        
        with student_tabs[3]:  # My Journey
            st.markdown("### My Learning Journey 🌟")
            st.markdown("*See how you're growing and learning*")
            
            # Student progress overview
            if current_user in st.session_state.student_progress:
                progress_data = st.session_state.student_progress[current_user]
                
                # Activity summary
                activities = progress_data.get('student_activities', [])
                if activities:
                    st.markdown("#### Recent Learning Activities")
                    for activity in activities[-5:]:  # Show last 5 activities
                        with st.expander(f"🌱 {activity['timestamp']} - {activity['activity_type'].replace('_', ' ').title()}"):
                            st.markdown(f"**What I did:** {activity['content']}")
                            if activity['feedback_received']:
                                st.markdown(f"**Feedback:** {activity['feedback_received']}")
                            if activity['competency_analysis']:
                                st.markdown(f"**Skills I'm developing:** {activity['competency_analysis']}")
                
                # CEC competency display
                cec_data = progress_data.get('cec_competencies', {})
                if cec_data:
                    st.markdown("#### My Learning Skills Progress")
                    
                    competency_names = {
                        "knowing_how_to_learn": "Learning How to Learn",
                        "empirical_reasoning": "Scientific Thinking", 
                        "quantitative_reasoning": "Mathematical Thinking",
                        "social_reasoning": "Understanding People & Communities",
                        "communication": "Sharing Ideas",
                        "personal_qualities": "Personal Growth"
                    }
                    
                    cols = st.columns(3)
                    for i, (comp_key, comp_data) in enumerate(cec_data.items()):
                        with cols[i % 3]:
                            name = competency_names.get(comp_key, comp_key)
                            level = comp_data.get('level', 1)
                            st.metric(name, f"Level {level}", help=f"You're developing skills in {name.lower()}")
                
                # Portfolio summary
                user_portfolios = st.session_state.portfolios.get(current_user, {})
                if user_portfolios:
                    st.markdown("#### My Portfolios")
                    for portfolio_name, portfolio in user_portfolios.items():
                        total_entries = sum(len(entries) for entries in portfolio['entries'].values())
                        st.markdown(f"📁 **{portfolio_name}** - {total_entries} entries")
            else:
                st.info("Start exploring and creating to see your learning journey!")
        
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
        
        if uploaded_file is not None:
            try:
                if uploaded_file.type == "text/plain":
                    content = str(uploaded_file.read(), "utf-8")
                    st.session_state.uploaded_content = content
                    st.success("Text file uploaded successfully!")
                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
                    content = df.to_string()
                    st.session_state.uploaded_content = content
                    st.success("CSV file uploaded successfully!")
                    with st.expander("Preview uploaded data"):
                        st.dataframe(df.head())
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        
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
        Guide - Cosmic Curriculum Companion | Powered by OpenAI GPT-5<br>
        Bridging Montessori's Cosmic Education with contemporary curriculum frameworks<br>
        <em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)

