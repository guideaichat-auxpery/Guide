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

def track_student_progress(student_name, work_analysis, learning_goals):
    """Track and analyze student progress over time"""
    if student_name not in st.session_state.student_progress:
        st.session_state.student_progress[student_name] = {
            "entries": [],
            "learning_goals": [],
            "strengths": [],
            "growth_areas": [],
            "interests": []
        }
    
    # Add new progress entry
    progress_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "work_analysis": work_analysis,
        "learning_goals": learning_goals,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    
    st.session_state.student_progress[student_name]["entries"].append(progress_entry)

def generate_progress_report(student_name, curriculum, time_period="recent"):
    """Generate comprehensive progress report for a student"""
    if student_name not in st.session_state.student_progress:
        return "No progress data available for this student."
    
    student_data = st.session_state.student_progress[student_name]
    entries_summary = "\n".join([f"- {entry['timestamp']}: {entry['work_analysis'][:100]}..." 
                                for entry in student_data["entries"][-5:]])
    
    prompt = f"""Create a holistic progress report for {student_name} based on their learning journey data:

Recent Learning Entries:
{entries_summary}

Generate a report that:
- Celebrates growth and discoveries in a warm, encouraging tone
- Identifies patterns in their learning and thinking development
- Shows connections between different areas of learning
- Honors their individual learning path and developmental stage
- Suggests meaningful next steps that build on their interests and strengths
- Connects their progress to the bigger picture of their cosmic education
- Uses language that could be shared with families
- Focuses on the whole child, not just academic achievement

Frame this as a story of their learning journey with {curriculum} principles."""
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

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
    
    # Student Progress Tracking
    with st.expander("📈 Student Progress Tracking"):
        progress_student = st.text_input("Student name:", key="progress_student")
        
        if progress_student:
            col1, col2 = st.columns(2)
            
            with col1:
                work_observation = st.text_area("Learning observation or work analysis:", 
                                              height=100, key="work_observation")
                learning_goals = st.text_input("Learning goals/focus:", key="learning_goals")
                
                if st.button("Record Progress Entry", key="record_progress"):
                    if work_observation:
                        track_student_progress(progress_student, work_observation, learning_goals)
                        st.success(f"Progress recorded for {progress_student}!")
                    else:
                        st.warning("Please add a learning observation.")
            
            with col2:
                if st.button("Generate Progress Report", key="gen_report"):
                    with st.spinner("Creating holistic progress report..."):
                        report = generate_progress_report(progress_student, st.session_state.curriculum)
                        if report:
                            st.markdown(f"### Learning Journey Report: {progress_student}")
                            st.markdown(report)
                
                # Show recent entries
                if progress_student in st.session_state.student_progress:
                    entries = st.session_state.student_progress[progress_student]["entries"]
                    if entries:
                        st.markdown("**Recent Entries:**")
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
                    
                    if feedback and extensions:
                        # Store in history
                        st.session_state.student_feedback_history.append({
                            "work": st.session_state.student_work,
                            "feedback": feedback,
                            "extensions": extensions,
                            "interests": student_interests,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        
                        # Display feedback
                        st.success("Here's what I discovered in your work!")
                        
                        with st.expander("🌟 Celebrating Your Thinking", expanded=True):
                            st.markdown(feedback)
                        
                        with st.expander("🚀 Ways to Explore Further", expanded=True):
                            st.markdown(extensions)
                    else:
                        st.error("I'm having trouble analyzing your work right now. Please try again!")
            else:
                st.warning("Please share your work first so I can explore it with you!")
    
    with col2:
        st.subheader("💭 Your Learning Journey")
        
        # Display recent feedback
        if st.session_state.student_feedback_history:
            st.markdown("### Recent Explorations")
            for i, entry in enumerate(reversed(st.session_state.student_feedback_history[-3:])):
                with st.expander(f"📚 Learning from {entry['timestamp']}", expanded=(i == 0)):
                    st.markdown("**Your work:**")
                    st.markdown(entry['work'][:200] + "..." if len(entry['work']) > 200 else entry['work'])
                    
                    if st.button(f"View full feedback", key=f"view_feedback_{len(st.session_state.student_feedback_history)-i}"):
                        st.markdown("**Feedback:**")
                        st.markdown(entry['feedback'])
                        st.markdown("**Extensions:**")
                        st.markdown(entry['extensions'])
        
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
        
        # Clear student work button
        if st.button("🗑️ Start Fresh", use_container_width=True):
            st.session_state.student_work = ""
            st.session_state.student_feedback_history = []
            st.rerun()

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
