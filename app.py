import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI
import io
import json

# Configure page
st.set_page_config(
    page_title="Guide - AI Curriculum Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.stop()
    return OpenAI(api_key=api_key)

client = get_openai_client()

# Initialize session state
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
        if st.session_state.uploaded_content:
            full_messages[0]["content"] += f"\n\nAdditional curriculum notes provided by user:\n{st.session_state.uploaded_content}"
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

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

# Main app layout
st.title("🌍 Guide - Cosmic Curriculum Companion")
st.markdown("*Weaving threads of knowledge in the tapestry of learning*")

# User type selector at the top
user_type = st.radio(
    "Who are you today?",
    ["Teacher", "Student"],
    horizontal=True,
    key="user_type_selector"
)
st.session_state.user_type = user_type

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Curriculum selector
    curriculum = st.selectbox(
        "📚 Curriculum Framework",
        ["Australian Curriculum V9", "Montessori Curriculum Australia"],
        key="curriculum_selector"
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

# Main content area based on user type
if st.session_state.user_type == "Teacher":
    # Teacher interface
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("💬 Teacher Chat Interface")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Share your curiosity about learning, teaching, or how knowledge connects to the bigger picture..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate AI response
            with st.chat_message("assistant"):
                with st.spinner("Reflecting on connections..."):
                    system_prompt = get_system_prompt(st.session_state.curriculum)
                    response = call_openai_api(st.session_state.messages, system_prompt)
                    
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble connecting right now. Please try again.")

    with col2:
        st.header("🛠️ Tools & Generators")
    
    # Lesson Idea Generator
    with st.expander("🌱 Learning Connections", expanded=True):
        lesson_topic = st.text_input("What topic would you like to explore?", key="lesson_topic", placeholder="e.g., Water cycle, Ancient civilizations, Fractions...")
        if st.button("Discover Connections", key="gen_lesson"):
            if lesson_topic:
                with st.spinner("Weaving connections across the cosmic curriculum..."):
                    ideas = generate_lesson_ideas(lesson_topic, st.session_state.curriculum)
                    if ideas:
                        st.markdown("### Learning Connections & Invitations")
                        st.markdown(ideas)
            else:
                st.info("Share a topic you're curious about exploring with students.")
    
    # Learning Threads Visualizer
    with st.expander("🕸️ Learning Threads & Patterns"):
        st.markdown("**Map the interconnected web of knowledge:**")
        
        # Manual topic entry
        manual_topics = st.text_area(
            "What learning threads would you like to weave together?",
            height=100,
            key="manual_topics",
            placeholder="Mathematics patterns in nature\nHistory of human migration\nClimate and ecosystem changes..."
        )
        
        if st.button("Weave Learning Threads", key="gen_scope"):
            topics = []
            
            # Get topics from manual input
            if manual_topics:
                topics.extend([topic.strip() for topic in manual_topics.split('\n') if topic.strip()])
            
            # Get topics from uploaded CSV if available
            if st.session_state.uploaded_content and uploaded_file is not None and uploaded_file.type == "text/csv":
                try:
                    df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
                    if 'topic' in df.columns:
                        topics.extend(df['topic'].tolist())
                    elif len(df.columns) > 0:
                        topics.extend(df.iloc[:, 0].tolist())
                except:
                    pass
            
            if topics:
                with st.spinner("Mapping connections in the cosmic curriculum..."):
                    # Generate AI suggestions
                    sequence_plan = generate_scope_sequence(topics, st.session_state.curriculum)
                    if sequence_plan:
                        st.markdown("### Learning Threads & Interconnections")
                        st.markdown(sequence_plan)
                    
                    # Create timeline visualization
                    fig = create_timeline_visualization(topics[:10])  # Limit to 10 topics for readability
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Share the learning topics you'd like to connect in meaningful ways.")
    
    # Parent Communication Helper
    with st.expander("💫 Family & Community Connection"):
        parent_topic = st.text_input("What learning would you like to share with families?", key="parent_topic", placeholder="e.g., Our exploration of ecosystems, Understanding fractions through real life...")
        if st.button("Craft Family Letter", key="gen_parent"):
            if parent_topic:
                with st.spinner("Crafting meaningful family connection..."):
                    parent_content = generate_parent_communication(parent_topic, st.session_state.curriculum)
                    if parent_content:
                        st.markdown("### Family Learning Connection")
                        st.markdown(parent_content)
            else:
                st.info("Share what learning experience you'd like to connect with families.")
    
    # Student Task Generator
    with st.expander("🌟 Learning Invitations"):
        task_topic = st.text_input("What learning would you like to invite students into?", key="task_topic", placeholder="e.g., Understanding democracy, Exploring geometric patterns, Investigating local water systems...")
        age_group = st.selectbox(
            "Developmental Stage:",
            ["Early Years (3-5)", "Primary Years (6-11)", "Middle Years (12-15)"],
            key="age_group"
        )
        if st.button("Create Learning Invitations", key="gen_tasks"):
            if task_topic:
                with st.spinner("Crafting meaningful invitations to explore..."):
                    tasks = generate_student_tasks(task_topic, age_group, st.session_state.curriculum)
                    if tasks:
                        st.markdown("### Learning Invitations & Explorations")
                        st.markdown(tasks)
                        
                        # Option to share lesson
                        if st.button("Share with Team", key="share_tasks"):
                            teacher_name = st.text_input("Your name:", key="teacher_name_tasks")
                            if teacher_name:
                                create_shared_lesson(tasks, teacher_name, st.session_state.curriculum, task_topic)
                                st.success("Lesson shared with your team!")
            else:
                st.info("Share what learning experience you'd like to create for students.")
    
    # Assessment Rubric Generator
    with st.expander("📏 Assessment Rubric Creator"):
        rubric_topic = st.text_input("Topic for assessment:", key="rubric_topic", placeholder="e.g., Scientific inquiry, Creative writing, Mathematical reasoning...")
        
        col1, col2 = st.columns(2)
        with col1:
            rubric_year = st.selectbox("Year Level:", 
                                     ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", 
                                      "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"],
                                     key="rubric_year")
        with col2:
            assessment_type = st.selectbox("Assessment Type:",
                                         ["Project-based", "Performance task", "Portfolio", 
                                          "Presentation", "Investigation", "Creative work"],
                                         key="assessment_type")
        
        if st.button("Create Growth-Focused Rubric", key="gen_rubric"):
            if rubric_topic:
                with st.spinner("Creating developmental assessment rubric..."):
                    rubric = generate_assessment_rubric(rubric_topic, st.session_state.curriculum, assessment_type, rubric_year)
                    if rubric:
                        st.markdown("### Developmental Assessment Rubric")
                        st.markdown(rubric)
            else:
                st.info("Enter a topic to create an assessment rubric.")
    
    # Enhanced Student Progress Tracking with CEC
    with st.expander("📈 Cosmic Education Competency Tracking"):
        progress_student = st.text_input("Student name:", key="progress_student")
        
        if progress_student:
            # Tabs for different tracking aspects
            tab1, tab2, tab3 = st.tabs(["📝 Record Progress", "🌟 CEC Profile", "📊 Reports"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    work_observation = st.text_area("Learning observation or work analysis:", 
                                                  height=100, key="work_observation")
                    learning_goals = st.text_input("Learning goals/focus:", key="learning_goals")
                    
                    # CEC Competency Assessment
                    st.markdown("**Assess Cosmic Education Competencies (optional):**")
                    cec_assessment = st.checkbox("Auto-assess CEC competencies from work", key="auto_cec")
                    
                    if st.button("Record Progress Entry", key="record_progress"):
                        if work_observation:
                            cec_data = None
                            if cec_assessment:
                                with st.spinner("Analyzing work against Cosmic Education Competencies..."):
                                    cec_analysis = generate_cec_competency_assessment(work_observation, st.session_state.curriculum)
                                    if cec_analysis:
                                        st.info("CEC competency analysis included in progress record")
                            
                            track_student_progress(progress_student, work_observation, learning_goals, cec_data)
                            st.success(f"Progress recorded for {progress_student}!")
                        else:
                            st.warning("Please add a learning observation.")
                
                with col2:
                    # Real-world learning tracking
                    st.markdown("**Real-World Learning Experiences:**")
                    
                    experience_type = st.selectbox("Experience type:", 
                                                 ["Internship", "Community Project", "Exhibition", "Research Project", "Social Action"])
                    experience_desc = st.text_area("Describe the experience:", height=80, key="experience_desc")
                    
                    if st.button("Add Real-World Experience", key="add_experience"):
                        if experience_desc and progress_student in st.session_state.student_progress:
                            experience_entry = {
                                "type": experience_type,
                                "description": experience_desc,
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            
                            if experience_type == "Internship":
                                st.session_state.student_progress[progress_student]["internships"].append(experience_entry)
                            elif experience_type == "Exhibition":
                                st.session_state.student_progress[progress_student]["exhibitions"].append(experience_entry)
                            else:
                                st.session_state.student_progress[progress_student]["real_world_projects"].append(experience_entry)
                            
                            st.success(f"{experience_type} experience recorded!")
            
            with tab2:
                # CEC Competency Profile Visualization
                if progress_student in st.session_state.student_progress:
                    student_data = st.session_state.student_progress[progress_student]
                    
                    st.markdown("### Cosmic Education Competency Profile")
                    
                    competency_names = {
                        "knowing_how_to_learn": "Knowing How to Learn",
                        "empirical_reasoning": "Empirical Reasoning", 
                        "quantitative_reasoning": "Quantitative Reasoning",
                        "social_reasoning": "Social Reasoning",
                        "communication": "Communication",
                        "personal_qualities": "Personal Qualities"
                    }
                    
                    if "cec_competencies" in student_data:
                        # Create visual competency profile
                        competencies = []
                        levels = []
                        
                        for comp_key, comp_data in student_data["cec_competencies"].items():
                            competencies.append(competency_names.get(comp_key, comp_key))
                            levels.append(comp_data["level"])
                        
                        # Create radar chart style visualization
                        import plotly.graph_objects as go
                        
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatterpolar(
                            r=levels,
                            theta=competencies,
                            fill='toself',
                            name=progress_student,
                            line_color='#1f77b4'
                        ))
                        
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 5]
                                )
                            ),
                            title=f"{progress_student}'s Cosmic Education Competency Profile",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Detailed competency breakdown
                        st.markdown("**Competency Details:**")
                        for comp_key, comp_data in student_data["cec_competencies"].items():
                            name = competency_names.get(comp_key, comp_key)
                            level = comp_data["level"]
                            evidence_count = len(comp_data.get("evidence", []))
                            
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{name}**: Level {level}")
                            with col2:
                                st.write(f"{evidence_count} evidence items")
                    
                    # Student Activity Summary
                    st.markdown("### Student Learning Activities")
                    activities = student_data.get("student_activities", [])
                    
                    if activities:
                        # Separate final submissions from other activities
                        final_submissions = [a for a in activities if a.get('activity_type') == 'final_submission']
                        other_activities = [a for a in activities if a.get('activity_type') != 'final_submission']
                        
                        if final_submissions:
                            st.markdown("**📤 Final Work Submissions:**")
                            for submission in final_submissions[-3:]:
                                file_info = submission.get('file_info', {})
                                file_name = file_info.get('name', 'Unknown file')
                                file_type = file_info.get('type', 'Unknown type')
                                st.markdown(f"- *{submission['timestamp']}*: **{file_name}** ({file_type})")
                                if st.button(f"View submission details", key=f"view_submission_{submission['timestamp']}"):
                                    st.markdown("**Content Summary:**")
                                    st.markdown(submission['content'][:200] + "..." if len(submission['content']) > 200 else submission['content'])
                                    if submission.get('competency_analysis'):
                                        st.markdown("**CEC Analysis:**")
                                        st.markdown(submission['competency_analysis'][:300] + "..." if len(submission['competency_analysis']) > 300 else submission['competency_analysis'])
                        
                        if other_activities:
                            st.markdown("**📝 Learning Activities:**")
                            for activity in other_activities[-3:]:
                                activity_type = activity.get('activity_type', 'work_submission')
                                st.markdown(f"- *{activity['timestamp']}* ({activity_type}): {activity['content'][:60]}...")
                    
                    # Real-world experiences summary
                    st.markdown("### Real-World Learning Portfolio")
                    internships = student_data.get("internships", [])
                    exhibitions = student_data.get("exhibitions", [])
                    projects = student_data.get("real_world_projects", [])
                    
                    if internships:
                        st.markdown("**Internships:**")
                        for exp in internships[-3:]:
                            st.markdown(f"- *{exp['date']}*: {exp['description'][:80]}...")
                    
                    if exhibitions:
                        st.markdown("**Exhibitions:**")
                        for exp in exhibitions[-3:]:
                            st.markdown(f"- *{exp['date']}*: {exp['description'][:80]}...")
                    
                    if projects:
                        st.markdown("**Community Projects:**")
                        for exp in projects[-3:]:
                            st.markdown(f"- *{exp['date']}*: {exp['description'][:80]}...")
                    
                    # Student Portfolio Summary
                    st.markdown("### Student Portfolio Overview")
                    student_portfolios = st.session_state.student_portfolios.get(selected_student, [])
                    
                    if student_portfolios:
                        for i, portfolio in enumerate(student_portfolios):
                            total_entries = sum(len(entries) for entries in portfolio['entries'].values())
                            total_annotations = len(portfolio.get('annotations', []))
                            
                            with st.expander(f"📁 {portfolio['title']}", expanded=len(student_portfolios) == 1):
                                st.markdown(f"**Template:** {portfolio['template_type'].title()}")
                                st.markdown(f"**Created:** {portfolio['created']}")
                                st.markdown(f"**Total Entries:** {total_entries}")
                                st.markdown(f"**Student Annotations:** {total_annotations}")
                                
                                # Show section breakdown
                                st.markdown("**Section Overview:**")
                                for section in portfolio['sections']:
                                    entries_count = len(portfolio['entries'].get(section, []))
                                    st.markdown(f"- {section}: {entries_count} entries")
                                
                                # Recent portfolio reflections
                                portfolio_reflections = [ann for ann in portfolio.get('annotations', []) 
                                                       if ann.get('type') in ['portfolio_reflection', 'general']]
                                if portfolio_reflections:
                                    st.markdown("**Recent Reflections:**")
                                    latest_reflection = portfolio_reflections[-1]
                                    reflection_text = latest_reflection.get('reflection', latest_reflection.get('annotation', ''))
                                    st.markdown(f"*{latest_reflection['timestamp']}*: {reflection_text[:150]}..." if len(reflection_text) > 150 else reflection_text)
                                
                                if st.button(f"View Full Portfolio", key=f"view_portfolio_{selected_student}_{i}"):
                                    st.session_state.selected_portfolio = (selected_student, i)
                                    st.rerun()
                    else:
                        st.info(f"{selected_student} hasn't created any portfolios yet.")
                
                else:
                    st.info("No profile data available yet. Record some progress entries first.")
            
            with tab3:
                # Reports and Analysis
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Generate CEC Learning Journey Report", key="gen_cec_report"):
                        with st.spinner("Creating comprehensive Cosmic Education learning journey..."):
                            report = generate_progress_report(progress_student, st.session_state.curriculum, include_cec=True)
                            if report:
                                st.markdown(f"### Cosmic Education Learning Journey: {progress_student}")
                                st.markdown(report)
                
                with col2:
                    if st.button("Create Learner Profile", key="create_profile"):
                        profile_data = create_cec_learner_profile(progress_student, st.session_state.curriculum)
                        if profile_data and profile_data != "No profile data available.":
                            st.markdown(f"### Cosmic Learner Profile: {progress_student}")
                            st.json(profile_data)
                        else:
                            st.info("No profile data available yet.")
                
                # Show recent entries
                if progress_student in st.session_state.student_progress:
                    entries = st.session_state.student_progress[progress_student]["entries"]
                    if entries:
                        st.markdown("**Recent Learning Entries:**")
                        for entry in entries[-3:]:
                            st.markdown(f"*{entry['date']}*: {entry['work_analysis'][:80]}...")
    
    # Collaborative Lesson Sharing
    with st.expander("🤝 Team Collaboration Hub"):
        st.markdown("**Share and explore lessons with your teaching team**")
        
        # Toggle collaboration mode
        collab_mode = st.checkbox("Enable collaboration features", key="collab_toggle")
        st.session_state.collaboration_mode = collab_mode
        
        if collab_mode:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**Shared Lessons:**")
                if st.session_state.shared_lessons:
                    for lesson in st.session_state.shared_lessons[-5:]:
                        with st.expander(f"📚 {lesson['title']} by {lesson['author']}"):
                            st.markdown(f"**Topic:** {lesson['topic']}")
                            st.markdown(f"**Curriculum:** {lesson['curriculum']}")
                            st.markdown(f"**Created:** {lesson['created']}")
                            st.markdown("**Content:**")
                            st.markdown(lesson['content'][:300] + "..." if len(lesson['content']) > 300 else lesson['content'])
                            
                            # Comments section
                            if lesson['comments']:
                                st.markdown("**Team Comments:**")
                                for comment in lesson['comments'][-3:]:
                                    st.markdown(f"*{comment['author']} ({comment['timestamp']}):* {comment['content']}")
                            
                            # Add comment
                            new_comment = st.text_input(f"Add comment to {lesson['title']}", key=f"comment_{lesson['id']}")
                            commenter_name = st.text_input("Your name:", key=f"commenter_{lesson['id']}")
                            
                            if st.button(f"Add Comment", key=f"add_comment_{lesson['id']}"):
                                if new_comment and commenter_name:
                                    add_lesson_comment(lesson['id'], commenter_name, new_comment)
                                    st.success("Comment added!")
                                    st.rerun()
                else:
                    st.info("No shared lessons yet. Create and share lessons using the tools above!")
            
            with col2:
                st.markdown("**Quick Share:**")
                share_title = st.text_input("Lesson title:", key="share_title")
                share_content = st.text_area("Lesson content or idea:", height=150, key="share_content")
                share_author = st.text_input("Your name:", key="share_author")
                share_topic = st.text_input("Topic/subject:", key="share_topic")
                
                if st.button("Share with Team", key="quick_share"):
                    if share_content and share_author and share_topic:
                        create_shared_lesson(share_content, share_author, st.session_state.curriculum, share_topic)
                        st.success("Lesson shared with your team!")
                        st.rerun()
                    else:
                        st.warning("Please fill in all fields to share.")

else:
    # Student interface
    st.header("🌟 Welcome, Young Explorer!")
    st.markdown("*Share your discoveries and let's explore connections together*")
    
    # Initialize student session state
    if 'student_work' not in st.session_state:
        st.session_state.student_work = ""
    if 'student_feedback_history' not in st.session_state:
        st.session_state.student_feedback_history = []
    if 'current_student_name' not in st.session_state:
        st.session_state.current_student_name = ""
    
    # Student identification for progress linking
    with st.sidebar:
        st.markdown("### Your Learning Profile")
        student_name_input = st.text_input(
            "What's your name?", 
            value=st.session_state.current_student_name,
            help="This helps us track your amazing learning journey and connect your work to your progress profile"
        )
        if student_name_input:
            st.session_state.current_student_name = student_name_input
            st.success(f"Great to see you, {student_name_input}! 🌟")
            
            # Show basic progress info if available
            if (st.session_state.current_student_name in 
                st.session_state.get('student_progress', {})):
                progress_data = st.session_state.student_progress[st.session_state.current_student_name]
                activity_count = len(progress_data.get('student_activities', []))
                st.info(f"Your learning activities: {activity_count}")
        else:
            st.info("Enter your name to connect your work to your learning profile!")
    
    # Initialize portfolio session state
    if 'student_portfolios' not in st.session_state:
        st.session_state.student_portfolios = {}
    
    # Portfolio Management Tab System
    portfolio_tabs = st.tabs(["📝 Share Work", "📁 My Portfolios", "💭 Learning Journey"])
    
    with portfolio_tabs[0]:
        # Student work upload and analysis section
        col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("📝 Share Your Work & Thinking")
        
        # Work upload options
        work_upload_type = st.selectbox(
            "How would you like to share your work?",
            ["Type or paste text", "Upload a file", "Describe your project"]
        )
        
        if work_upload_type == "Type or paste text":
            student_work_text = st.text_area(
                "Share your work, thoughts, or discoveries here:",
                height=200,
                placeholder="I discovered that... / I'm wondering about... / My project shows that...",
                key="student_work_text"
            )
            if student_work_text:
                st.session_state.student_work = student_work_text
        
        elif work_upload_type == "Upload a file":
            uploaded_student_file = st.file_uploader(
                "Upload your work (text, images, or documents):",
                type=['txt', 'pdf', 'jpg', 'jpeg', 'png', 'docx'],
                help="Share your writing, drawings, photos of your work, or documents"
            )
            
            if uploaded_student_file is not None:
                try:
                    if uploaded_student_file.type == "text/plain":
                        content = str(uploaded_student_file.read(), "utf-8")
                        st.session_state.student_work = content
                        st.success("Your work has been uploaded! ✨")
                        with st.expander("Preview your work"):
                            st.text(content[:500] + "..." if len(content) > 500 else content)
                    else:
                        st.success("Your file has been uploaded! ✨")
                        st.info("Now tell me about what you discovered or learned!")
                        
                        # Add description field for uploaded files
                        file_description = st.text_area(
                            "Describe what you discovered, learned, or created:",
                            height=120,
                            placeholder="This shows... / I learned that... / I discovered... / My project demonstrates...",
                            key="file_description"
                        )
                        
                        if file_description:
                            st.session_state.student_work = f"Student uploaded a {uploaded_student_file.type} file: {uploaded_student_file.name}\n\nStudent's description: {file_description}"
                        else:
                            st.session_state.student_work = f"Student uploaded a {uploaded_student_file.type} file: {uploaded_student_file.name}"
                            
                except Exception as e:
                    st.error(f"Having trouble reading your file: {str(e)}")
        
        else:  # Describe your project
            project_description = st.text_area(
                "Tell me about your project or what you're exploring:",
                height=150,
                placeholder="I'm working on... / I discovered... / I'm curious about...",
                key="project_description"
            )
            if project_description:
                st.session_state.student_work = project_description
        
        # Student interests and goals
        st.markdown("---")
        student_interests = st.text_input(
            "What topics fascinate you? (This helps me suggest connections to your work)",
            placeholder="Space, animals, how things work, art, music, math patterns...",
            key="student_interests",
            help="Sharing your interests helps me connect your work to things you're curious about"
        )
        
        # Get feedback button
        if st.button("🔍 Get Feedback & Discover Connections", use_container_width=True):
            if st.session_state.student_work:
                with st.spinner("Exploring your work and finding connections..."):
                    feedback = analyze_student_work(st.session_state.student_work, st.session_state.curriculum)
                    extensions = suggest_skill_extensions(st.session_state.student_work, st.session_state.curriculum, student_interests)
                    
                    # Also generate CEC competency analysis for student
                    cec_analysis = generate_cec_competency_assessment(st.session_state.student_work, st.session_state.curriculum)
                    
                    if feedback and extensions:
                        # Store in history
                        st.session_state.student_feedback_history.append({
                            "work": st.session_state.student_work,
                            "feedback": feedback,
                            "extensions": extensions,
                            "cec_analysis": cec_analysis,
                            "interests": student_interests,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        
                        # Link to progress tracking if student name available
                        if 'current_student_name' in st.session_state and st.session_state.current_student_name:
                            activity_data = {
                                "type": "work_submission",
                                "content": st.session_state.student_work,
                                "feedback": feedback,
                                "competency_analysis": cec_analysis,
                                "extensions": extensions
                            }
                            link_student_activity(st.session_state.current_student_name, activity_data)
                        
                        # Display feedback
                        st.success("Here's what I discovered in your work!")
                        
                        with st.expander("🌟 Celebrating Your Thinking", expanded=True):
                            st.markdown(feedback)
                        
                        with st.expander("🚀 Ways to Explore Further", expanded=True):
                            st.markdown(extensions)
                        
                        # Show CEC competency insights
                        if cec_analysis:
                            with st.expander("💪 Real-World Skills in Your Work", expanded=False):
                                st.markdown("**This analysis shows the amazing real-world skills your work demonstrates:**")
                                st.markdown(cec_analysis)
                                st.info("These are skills that help you succeed in life, not just school! Keep developing them through your projects and interests.")
                    else:
                        st.error("I'm having trouble analyzing your work right now. Please try again!")
            else:
                st.warning("Please share your work first so I can explore it with you!")
    
    with col2:
        st.subheader("💭 Your Learning Journey")
        
        # Display recent feedback
        if st.session_state.student_feedback_history:
            st.markdown("### Your Learning Journey")
            for i, entry in enumerate(reversed(st.session_state.student_feedback_history[-3:])):
                # Different display for final submissions vs regular work
                if entry.get('type') == 'final_submission':
                    title = f"🎯 Final Work: {entry.get('filename', 'Submission')}"
                else:
                    title = f"📚 Learning from {entry['timestamp']}"
                
                with st.expander(title, expanded=(i == 0)):
                    if entry.get('type') == 'final_submission':
                        st.markdown(f"**File:** {entry.get('filename', 'Unknown')} ({entry.get('file_type', 'Unknown type')})")
                        if entry.get('reflection'):
                            st.markdown("**Your Reflection:**")
                            st.markdown(entry['reflection'][:150] + "..." if len(entry.get('reflection', '')) > 150 else entry.get('reflection', ''))
                    else:
                        st.markdown("**Your work:**")
                        work_content = entry.get('work', entry.get('content', ''))
                        st.markdown(work_content[:200] + "..." if len(work_content) > 200 else work_content)
                    
                    if st.button(f"View full feedback", key=f"view_feedback_{len(st.session_state.student_feedback_history)-i}"):
                        st.markdown("**Feedback:**")
                        st.markdown(entry.get('feedback', 'No feedback available'))
                        
                        if entry.get('extensions'):
                            st.markdown("**Ways to Explore Further:**")
                            st.markdown(entry['extensions'])
                        
                        if entry.get('cec_analysis'):
                            st.markdown("**Real-World Skills:**")
                            st.markdown(entry['cec_analysis'])
        
        # Combined chat interface
        st.markdown("---")
        st.markdown("### 🤔 Ask Questions & Explore Ideas")
        st.markdown("*Ask anything about your work or topics you're curious about*")
        
        if student_question := st.text_input(
            "What would you like to explore or understand better?", 
            key="student_chat",
            placeholder="How does this connect to...? / Why do you think...? / What if...?",
            help="Ask questions about your work, wonder about connections, or explore new ideas"
        ):
            if st.button("Let's Explore Together 🌍"):
                with st.spinner("Thinking about your question..."):
                    student_system_prompt = """You are speaking directly to a curious student. Use warm, encouraging language appropriate for their age. Help them see connections to the bigger picture of how everything in the universe is related. Ask questions that spark their curiosity rather than giving direct answers. Honor their natural desire to explore and discover."""
                    
                    full_prompt = f"Student question: {student_question}"
                    if st.session_state.student_work:
                        full_prompt += f"\n\nContext from their recent work: {st.session_state.student_work[:300]}"
                    
                    messages = [{"role": "user", "content": full_prompt}]
                    response = call_openai_api(messages, student_system_prompt)
                    
                    if response:
                        st.markdown("**Guide's Response:**")
                        st.markdown(response)
        
        # Final Work Submission Section
        st.markdown("---")
        st.markdown("### 📤 Submit Your Final Work")
        st.markdown("*Ready to share your completed project, essay, or creation? Upload your final work here!*")
        
        final_work_upload = st.file_uploader(
            "Upload your final work:",
            type=['txt', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mp4'],
            help="Share your completed work - writing, artwork, presentations, recordings, or any creative project",
            key="final_work_upload"
        )
        
        if final_work_upload is not None:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # File information
                file_info = f"📁 **{final_work_upload.name}**\n"
                file_info += f"Size: {final_work_upload.size / 1024:.1f} KB\n"
                file_info += f"Type: {final_work_upload.type}"
                st.markdown(file_info)
                
                # Reflection questions for final submission
                st.markdown("**Tell us about your final work:**")
                final_reflection = st.text_area(
                    "Reflect on your learning journey:",
                    placeholder="What did you discover while creating this? What are you most proud of? How does this connect to bigger ideas you're exploring?",
                    height=120,
                    key="final_reflection"
                )
                
                learning_process = st.text_area(
                    "Describe your creative/learning process:",
                    placeholder="How did you approach this work? What challenges did you overcome? What would you do differently?",
                    height=100,
                    key="learning_process"
                )
                
            with col2:
                st.markdown("**Final Submission**")
                
                if st.button("🌟 Submit Final Work", use_container_width=True):
                    if final_reflection and learning_process:
                        # Process the final submission
                        with st.spinner("Analyzing your final work and celebrating your learning..."):
                            
                            # Create comprehensive analysis combining file and reflection
                            submission_content = f"""
FINAL WORK SUBMISSION
File: {final_work_upload.name} ({final_work_upload.type})

STUDENT REFLECTION:
{final_reflection}

LEARNING PROCESS:
{learning_process}
"""
                            
                            # Try to read text-based files
                            file_content = ""
                            try:
                                if final_work_upload.type == "text/plain":
                                    file_content = str(final_work_upload.read(), "utf-8")
                                    submission_content += f"\n\nFILE CONTENT:\n{file_content[:1000]}..." if len(file_content) > 1000 else f"\n\nFILE CONTENT:\n{file_content}"
                                elif final_work_upload.type == "application/pdf":
                                    submission_content += "\n\n[PDF file uploaded - content analysis available to teacher]"
                                else:
                                    submission_content += f"\n\n[{final_work_upload.type} file uploaded - multimedia content submitted]"
                            except:
                                submission_content += f"\n\n[File uploaded successfully - {final_work_upload.type} format]"
                            
                            # Generate comprehensive feedback
                            feedback = analyze_student_work(submission_content, st.session_state.curriculum)
                            extensions = suggest_skill_extensions(submission_content, st.session_state.curriculum, st.session_state.get('student_interests', ''))
                            cec_analysis = generate_cec_competency_assessment(submission_content, st.session_state.curriculum)
                            
                            if feedback:
                                # Store final submission in history
                                final_submission = {
                                    "type": "final_submission",
                                    "filename": final_work_upload.name,
                                    "file_type": final_work_upload.type,
                                    "reflection": final_reflection,
                                    "process": learning_process,
                                    "content": submission_content,
                                    "feedback": feedback,
                                    "extensions": extensions,
                                    "cec_analysis": cec_analysis,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                
                                # Add to feedback history
                                st.session_state.student_feedback_history.append(final_submission)
                                
                                # Link to progress tracking
                                if st.session_state.current_student_name:
                                    activity_data = {
                                        "type": "final_submission",
                                        "content": submission_content,
                                        "feedback": feedback,
                                        "competency_analysis": cec_analysis,
                                        "extensions": extensions,
                                        "file_info": {
                                            "name": final_work_upload.name,
                                            "type": final_work_upload.type,
                                            "size": final_work_upload.size
                                        }
                                    }
                                    link_student_activity(st.session_state.current_student_name, activity_data)
                                
                                # Display celebration and feedback
                                st.success("🎉 Your final work has been submitted! What an amazing learning journey!")
                                
                                with st.expander("🏆 Celebrating Your Achievement", expanded=True):
                                    st.markdown(feedback)
                                
                                with st.expander("🌟 Your Cosmic Education Skills", expanded=True):
                                    if cec_analysis:
                                        st.markdown("**Your final work demonstrates these incredible skills:**")
                                        st.markdown(cec_analysis)
                                    else:
                                        st.markdown("Your work shows amazing growth across multiple areas of learning!")
                                
                                with st.expander("🚀 Continue Your Learning Adventure", expanded=False):
                                    st.markdown(extensions)
                                
                                st.balloons()
                            else:
                                st.error("Having trouble analyzing your work. Please try again!")
                    else:
                        st.warning("Please share your reflections about your final work!")
        
        # Clear student work button
        if st.button("🗑️ Start Fresh", use_container_width=True):
            st.session_state.student_work = ""
            st.session_state.student_feedback_history = []
    
    with portfolio_tabs[1]:
        # Portfolio Management Interface
        st.subheader("📁 My Learning Portfolios")
        
        if st.session_state.current_student_name:
            student_portfolios = st.session_state.student_portfolios.get(st.session_state.current_student_name, [])
            
            # Create new portfolio section
            with st.expander("➕ Create New Portfolio", expanded=len(student_portfolios) == 0):
                col1, col2 = st.columns(2)
                
                with col1:
                    template_type = st.selectbox(
                        "Choose a portfolio template:",
                        ["blank", "themed", "subject", "year_level", "term"],
                        format_func=lambda x: {
                            "blank": "🎨 Blank Canvas - Design your own layout",
                            "themed": "🎭 Themed - Organize by big ideas and themes", 
                            "subject": "📚 Subject-Based - Organize by learning areas",
                            "year_level": "📅 Year Level - Track your yearly journey",
                            "term": "⏱️ Term-Based - Focus on a specific term"
                        }[x]
                    )
                
                with col2:
                    custom_params = {}
                    if template_type == "year_level":
                        year_input = st.text_input("Year Level:", placeholder="e.g., 7, 8, 9...")
                        if year_input:
                            custom_params["year"] = year_input
                    elif template_type == "term":
                        term_input = st.selectbox("Term:", ["Term 1", "Term 2", "Term 3", "Term 4"])
                        custom_params["term"] = term_input
                    elif template_type == "themed":
                        theme_input = st.text_input("Theme:", placeholder="e.g., Water Cycle, Community, Space...")
                        if theme_input:
                            custom_params["theme"] = theme_input
                
                portfolio_name = st.text_input("Portfolio Name (optional):", placeholder="Leave blank to use default name")
                
                if st.button("Create Portfolio"):
                    # Create new portfolio
                    new_portfolio = create_portfolio_template(template_type, st.session_state.current_student_name, custom_params)
                    if portfolio_name:
                        new_portfolio["title"] = portfolio_name
                    
                    # Add to student's portfolios
                    if st.session_state.current_student_name not in st.session_state.student_portfolios:
                        st.session_state.student_portfolios[st.session_state.current_student_name] = []
                    
                    st.session_state.student_portfolios[st.session_state.current_student_name].append(new_portfolio)
                    st.success(f"Portfolio '{new_portfolio['title']}' created! 🎉")
                    st.rerun()
            
            # Display existing portfolios
            if student_portfolios:
                st.markdown("### Your Portfolios")
                
                for i, portfolio in enumerate(student_portfolios):
                    with st.expander(f"📁 {portfolio['title']}", expanded=len(student_portfolios) == 1):
                        st.markdown(f"**Created:** {portfolio['created']}")
                        st.markdown(f"**Type:** {portfolio['template_type'].title()} Template")
                        st.markdown(f"**Description:** {portfolio['description']}")
                        
                        # Portfolio sections
                        st.markdown("### Portfolio Sections")
                        
                        for section in portfolio['sections']:
                            section_entries = portfolio['entries'].get(section, [])
                            
                            with st.expander(f"📋 {section} ({len(section_entries)} items)"):
                                # Add entry to section
                                st.markdown("**Add New Entry:**")
                                
                                entry_type = st.selectbox(
                                    "Entry type:",
                                    ["text", "work_sample", "reflection", "image", "file"],
                                    key=f"entry_type_{i}_{section}"
                                )
                                
                                if entry_type == "text":
                                    entry_content = st.text_area(
                                        "Content:",
                                        height=100,
                                        key=f"entry_content_{i}_{section}",
                                        placeholder="Write about your learning, discoveries, or thoughts..."
                                    )
                                    
                                elif entry_type == "work_sample":
                                    entry_file = st.file_uploader(
                                        "Upload work sample:",
                                        type=['txt', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                                        key=f"entry_file_{i}_{section}"
                                    )
                                    entry_content = st.text_area(
                                        "Describe this work:",
                                        height=80,
                                        key=f"work_desc_{i}_{section}",
                                        placeholder="What does this work show about your learning?"
                                    )
                                
                                elif entry_type == "reflection":
                                    entry_content = st.text_area(
                                        "Learning reflection:",
                                        height=120,
                                        key=f"reflection_{i}_{section}",
                                        placeholder="What did you learn? How did you grow? What connections did you make?"
                                    )
                                
                                else:  # image or file
                                    entry_file = st.file_uploader(
                                        f"Upload {entry_type}:",
                                        key=f"upload_{i}_{section}"
                                    )
                                    entry_content = st.text_area(
                                        "Caption or description:",
                                        height=60,
                                        key=f"caption_{i}_{section}"
                                    )
                                
                                # Entry reflection and tags
                                col1, col2 = st.columns(2)
                                with col1:
                                    entry_reflection = st.text_input(
                                        "Personal reflection:",
                                        key=f"personal_reflection_{i}_{section}",
                                        placeholder="How does this connect to your learning journey?"
                                    )
                                with col2:
                                    entry_tags = st.text_input(
                                        "Tags (comma-separated):",
                                        key=f"tags_{i}_{section}",
                                        placeholder="creativity, problem-solving, collaboration..."
                                    )
                                
                                if st.button(f"Add to {section}", key=f"add_entry_{i}_{section}"):
                                    entry_data = {
                                        "content": entry_content if 'entry_content' in locals() else "",
                                        "type": entry_type,
                                        "reflection": entry_reflection,
                                        "tags": [tag.strip() for tag in entry_tags.split(",")] if entry_tags else []
                                    }
                                    
                                    if 'entry_file' in locals() and entry_file:
                                        entry_data["file_info"] = {
                                            "name": entry_file.name,
                                            "type": entry_file.type,
                                            "size": entry_file.size
                                        }
                                    
                                    add_portfolio_entry(portfolio, section, entry_data)
                                    st.success(f"Entry added to {section}! 📚")
                                    st.rerun()
                                
                                # Display existing entries
                                if section_entries:
                                    st.markdown("**Current Entries:**")
                                    for j, entry in enumerate(section_entries):
                                        with st.container():
                                            st.markdown(f"**Entry {entry['id']}** - *{entry['timestamp']}*")
                                            
                                            if entry['file_info']:
                                                st.markdown(f"📎 **File:** {entry['file_info'].get('name', 'Unknown')}")
                                            
                                            if entry['content']:
                                                st.markdown(f"**Content:** {entry['content'][:200]}..." if len(entry['content']) > 200 else entry['content'])
                                            
                                            if entry['reflection']:
                                                st.markdown(f"**Reflection:** {entry['reflection']}")
                                            
                                            if entry['tags']:
                                                st.markdown(f"**Tags:** {', '.join(entry['tags'])}")
                                            
                                            # Annotation system
                                            annotation_text = st.text_input(
                                                "Add learning annotation:",
                                                key=f"annotation_{i}_{section}_{j}",
                                                placeholder="Looking back, what do you notice about this work?"
                                            )
                                            
                                            if st.button(f"Annotate Entry {entry['id']}", key=f"annotate_{i}_{section}_{j}"):
                                                if annotation_text:
                                                    annotate_portfolio_entry(portfolio, section, entry['id'], annotation_text)
                                                    st.success("Annotation added! 📝")
                                                    st.rerun()
                                            
                                            st.markdown("---")
                        
                        # Portfolio-wide reflections
                        st.markdown("### Portfolio Reflection")
                        portfolio_reflection = st.text_area(
                            "Reflect on your learning journey in this portfolio:",
                            height=100,
                            key=f"portfolio_reflection_{i}",
                            placeholder="What patterns do you see in your learning? How have you grown? What are you most proud of?"
                        )
                        
                        if st.button(f"Add Portfolio Reflection", key=f"add_portfolio_reflection_{i}"):
                            if portfolio_reflection:
                                add_portfolio_reflection(portfolio, portfolio_reflection, "portfolio_reflection")
                                st.success("Portfolio reflection added! 🌟")
                                st.rerun()
                        
                        # Display portfolio annotations
                        portfolio_annotations = [ann for ann in portfolio.get('annotations', []) if ann.get('type') in ['portfolio_reflection', 'general']]
                        if portfolio_annotations:
                            st.markdown("**Your Portfolio Reflections:**")
                            for ann in portfolio_annotations[-3:]:
                                st.markdown(f"*{ann['timestamp']}*: {ann.get('reflection', ann.get('annotation', ''))}")
            else:
                st.info("Create your first portfolio to start documenting your learning journey! 📚")
        
        else:
            st.warning("Please enter your name in the sidebar to create and manage portfolios.")
    
    with portfolio_tabs[2]:
        # Learning Journey Overview
        st.subheader("💭 Your Learning Journey")
        
        if st.session_state.current_student_name:
            # Display recent feedback as before
            if st.session_state.student_feedback_history:
                st.markdown("### Recent Learning Experiences")
                for i, entry in enumerate(reversed(st.session_state.student_feedback_history[-3:])):
                    if entry.get('type') == 'final_submission':
                        title = f"🎯 Final Work: {entry.get('filename', 'Submission')}"
                    else:
                        title = f"📚 Learning from {entry['timestamp']}"
                    
                    with st.expander(title, expanded=(i == 0)):
                        if entry.get('type') == 'final_submission':
                            st.markdown(f"**File:** {entry.get('filename', 'Unknown')} ({entry.get('file_type', 'Unknown type')})")
                            if entry.get('reflection'):
                                st.markdown("**Your Reflection:**")
                                st.markdown(entry['reflection'][:150] + "..." if len(entry.get('reflection', '')) > 150 else entry.get('reflection', ''))
                        else:
                            st.markdown("**Your work:**")
                            work_content = entry.get('work', entry.get('content', ''))
                            st.markdown(work_content[:200] + "..." if len(work_content) > 200 else work_content)
                        
                        # Add to portfolio option
                        if st.session_state.current_student_name in st.session_state.student_portfolios:
                            portfolios = st.session_state.student_portfolios[st.session_state.current_student_name]
                            if portfolios:
                                selected_portfolio = st.selectbox(
                                    "Add to portfolio:",
                                    ["Select portfolio..."] + [p['title'] for p in portfolios],
                                    key=f"portfolio_select_{i}"
                                )
                                
                                if selected_portfolio != "Select portfolio...":
                                    portfolio = next(p for p in portfolios if p['title'] == selected_portfolio)
                                    selected_section = st.selectbox(
                                        "Add to section:",
                                        portfolio['sections'],
                                        key=f"section_select_{i}"
                                    )
                                    
                                    if st.button(f"Add to Portfolio", key=f"add_to_portfolio_{i}"):
                                        entry_data = {
                                            "content": work_content if 'work_content' in locals() else entry.get('content', ''),
                                            "type": "learning_experience",
                                            "reflection": entry.get('reflection', ''),
                                            "cec_analysis": entry.get('cec_analysis', ''),
                                            "tags": ["learning_experience", "feedback_session"]
                                        }
                                        
                                        if entry.get('filename'):
                                            entry_data["file_info"] = {
                                                "name": entry['filename'],
                                                "type": entry.get('file_type', 'unknown')
                                            }
                                        
                                        add_portfolio_entry(portfolio, selected_section, entry_data)
                                        st.success(f"Added to {selected_portfolio}! 📁")
                                        st.rerun()
            else:
                st.info("Start sharing your work to build your learning journey!")
        else:
            st.warning("Please enter your name in the sidebar to view your learning journey.")

# Detailed Portfolio View for Teachers (appears when teacher clicks "View Full Portfolio")
if 'selected_portfolio' in st.session_state and st.session_state.selected_portfolio:
    student_name, portfolio_index = st.session_state.selected_portfolio
    if student_name in st.session_state.student_portfolios:
        portfolio = st.session_state.student_portfolios[student_name][portfolio_index]
        
        st.markdown("---")
        st.markdown(f"## 📁 {portfolio['title']} - Detailed Teacher View")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("← Back to Student Overview"):
                del st.session_state.selected_portfolio
                st.rerun()
        
        with col1:
            st.markdown(f"**Student:** {student_name}")
            st.markdown(f"**Template:** {portfolio['template_type'].title()}")
            st.markdown(f"**Created:** {portfolio['created']}")
            st.markdown(f"**Description:** {portfolio['description']}")
        
        # Display all portfolio sections with entries
        for section in portfolio['sections']:
            entries = portfolio['entries'].get(section, [])
            
            with st.expander(f"📋 {section} ({len(entries)} entries)", expanded=len(entries) > 0):
                if entries:
                    for entry in entries:
                        st.markdown(f"**Entry {entry['id']}** - *{entry['timestamp']}*")
                        
                        if entry['file_info']:
                            st.markdown(f"📎 **File:** {entry['file_info'].get('name', 'Unknown')} ({entry['file_info'].get('type', 'Unknown')})")
                        
                        if entry['content']:
                            st.markdown(f"**Content:** {entry['content']}")
                        
                        if entry['reflection']:
                            st.markdown(f"**Student Reflection:** {entry['reflection']}")
                        
                        if entry['tags']:
                            st.markdown(f"**Tags:** {', '.join(entry['tags'])}")
                        
                        if entry['cec_analysis']:
                            st.markdown(f"**CEC Skills Demonstrated:** {entry['cec_analysis']}")
                        
                        # Show annotations for this entry
                        entry_annotations = [ann for ann in portfolio.get('annotations', []) 
                                           if ann.get('section') == section and ann.get('entry_id') == entry['id']]
                        if entry_annotations:
                            st.markdown("**Student Annotations:**")
                            for ann in entry_annotations:
                                st.markdown(f"- *{ann['timestamp']}*: {ann.get('annotation', '')}")
                        
                        st.markdown("---")
                else:
                    st.info(f"No entries in {section} yet.")
        
        # Portfolio-wide reflections
        portfolio_reflections = [ann for ann in portfolio.get('annotations', []) 
                               if ann.get('type') in ['portfolio_reflection', 'general']]
        if portfolio_reflections:
            st.markdown("### Student Portfolio Reflections")
            for reflection in portfolio_reflections:
                st.markdown(f"**{reflection['timestamp']}**")
                reflection_text = reflection.get('reflection', reflection.get('annotation', ''))
                st.markdown(reflection_text)
                st.markdown("---")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Guide - Cosmic Curriculum Companion | Powered by OpenAI GPT-4o<br>
        Bridging Montessori's Cosmic Education with contemporary curriculum frameworks<br>
        <em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)
