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

# Helper functions
def get_system_prompt(curriculum):
    """Get system prompt based on selected curriculum"""
    base_prompt = "You are an AI trained on both the Australian Curriculum V9 and Montessori Curriculum Australia. Always answer with practical, accurate, and teacher-friendly guidance."
    
    if curriculum == "Australian Curriculum V9":
        return f"{base_prompt} Focus your responses on the Australian Curriculum V9 framework, including learning areas, general capabilities, and cross-curriculum priorities."
    else:
        return f"{base_prompt} Focus your responses on the Montessori Curriculum Australia framework, emphasizing child-led learning, prepared environments, and developmental stages."

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
    """Generate lesson ideas for a given topic"""
    prompt = f"Generate 3-5 creative lesson ideas for the topic '{topic}' aligned with {curriculum}. Include learning objectives, activities, and assessment strategies. Format as a structured response with clear headings."
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_scope_sequence(topics_data, curriculum):
    """Generate scope and sequence suggestions"""
    topics_text = "\n".join([f"- {topic}" for topic in topics_data])
    prompt = f"Analyze these curriculum topics and suggest an optimal teaching sequence with rationale:\n{topics_text}\n\nProvide a structured scope and sequence plan for {curriculum} with timing recommendations and prerequisite relationships."
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_parent_communication(topic, curriculum):
    """Generate parent communication content"""
    prompt = f"Create a parent information letter or newsletter about '{topic}' for {curriculum}. Include what students will learn, how parents can support at home, and key vocabulary or concepts. Make it friendly and informative."
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

def generate_student_tasks(topic, age_group, curriculum):
    """Generate student tasks and activities"""
    prompt = f"Create age-appropriate activities and scaffolds for {age_group} students learning about '{topic}' in {curriculum}. Include differentiation strategies for various learning needs and abilities."
    
    messages = [{"role": "user", "content": prompt}]
    system_prompt = get_system_prompt(curriculum)
    
    return call_openai_api(messages, system_prompt)

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
st.title("🎓 Guide - AI Curriculum Assistant")
st.markdown("*Your intelligent companion for curriculum-aligned teaching*")

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

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Chat Interface")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about curriculum, lesson planning, or teaching strategies..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                system_prompt = get_system_prompt(st.session_state.curriculum)
                response = call_openai_api(st.session_state.messages, system_prompt)
                
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("Failed to generate response. Please try again.")

with col2:
    st.header("🛠️ Tools & Generators")
    
    # Lesson Idea Generator
    with st.expander("📝 Lesson Idea Generator", expanded=True):
        lesson_topic = st.text_input("Enter a topic:", key="lesson_topic")
        if st.button("Generate Lesson Ideas", key="gen_lesson"):
            if lesson_topic:
                with st.spinner("Generating lesson ideas..."):
                    ideas = generate_lesson_ideas(lesson_topic, st.session_state.curriculum)
                    if ideas:
                        st.markdown("### Generated Lesson Ideas")
                        st.markdown(ideas)
            else:
                st.warning("Please enter a topic first.")
    
    # Scope & Sequence Visualizer
    with st.expander("📊 Scope & Sequence Visualizer"):
        st.markdown("**Upload CSV or enter topics manually:**")
        
        # Manual topic entry
        manual_topics = st.text_area(
            "Enter topics (one per line):",
            height=100,
            key="manual_topics"
        )
        
        if st.button("Generate Scope & Sequence", key="gen_scope"):
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
                with st.spinner("Generating scope and sequence..."):
                    # Generate AI suggestions
                    sequence_plan = generate_scope_sequence(topics, st.session_state.curriculum)
                    if sequence_plan:
                        st.markdown("### Scope & Sequence Plan")
                        st.markdown(sequence_plan)
                    
                    # Create timeline visualization
                    fig = create_timeline_visualization(topics[:10])  # Limit to 10 topics for readability
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Please enter topics or upload a CSV file with topics.")
    
    # Parent Communication Helper
    with st.expander("👨‍👩‍👧‍👦 Parent Communication Helper"):
        parent_topic = st.text_input("Topic for parent communication:", key="parent_topic")
        if st.button("Generate Parent Letter", key="gen_parent"):
            if parent_topic:
                with st.spinner("Generating parent communication..."):
                    parent_content = generate_parent_communication(parent_topic, st.session_state.curriculum)
                    if parent_content:
                        st.markdown("### Parent Communication")
                        st.markdown(parent_content)
            else:
                st.warning("Please enter a topic first.")
    
    # Student Task Generator
    with st.expander("🎯 Student Task Generator"):
        task_topic = st.text_input("Topic for student tasks:", key="task_topic")
        age_group = st.selectbox(
            "Age Group:",
            ["Early Years (3-5)", "Primary Years (6-11)", "Middle Years (12-15)"],
            key="age_group"
        )
        if st.button("Generate Student Tasks", key="gen_tasks"):
            if task_topic:
                with st.spinner("Generating student tasks..."):
                    tasks = generate_student_tasks(task_topic, age_group, st.session_state.curriculum)
                    if tasks:
                        st.markdown("### Student Tasks & Activities")
                        st.markdown(tasks)
            else:
                st.warning("Please enter a topic first.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Guide - AI Curriculum Assistant | Powered by OpenAI GPT-4o<br>
        Supporting Australian Curriculum V9 and Montessori Curriculum Australia
    </div>
    """,
    unsafe_allow_html=True
)
