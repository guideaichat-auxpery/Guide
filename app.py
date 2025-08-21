import streamlit as st
import openai
import pandas as pd
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configure page
st.set_page_config(
    page_title="Guide - AI Curriculum Assistant",
    page_icon="🎓",
    layout="wide"
)

# Initialize OpenAI client
@st.cache_resource
def init_openai():
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        return client
    except Exception as e:
        st.error("OpenAI API key not found. Please add your API key to Streamlit secrets.")
        return None

client = init_openai()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'curriculum' not in st.session_state:
    st.session_state.curriculum = "Australian Curriculum V9"
if 'uploaded_content' not in st.session_state:
    st.session_state.uploaded_content = ""

# System prompts based on curriculum
def get_system_prompt(curriculum, feature_type="chat"):
    base_prompt = f"You are an AI trained on both the Australian Curriculum V9 and Montessori Curriculum Australia. You are currently working with the {curriculum}. Always answer with practical, accurate, and teacher-friendly guidance."
    
    if st.session_state.uploaded_content:
        base_prompt += f"\n\nAdditional context from uploaded files:\n{st.session_state.uploaded_content}"
    
    if feature_type == "lesson":
        return base_prompt + "\n\nGenerate detailed lesson ideas that are curriculum-aligned, practical, and include learning objectives, activities, and assessment strategies."
    elif feature_type == "sequence":
        return base_prompt + "\n\nCreate a logical scope and sequence for the given topics, considering learning progression, prerequisites, and curriculum requirements."
    elif feature_type == "parent":
        return base_prompt + "\n\nWrite clear, informative parent communication that explains curriculum content and student learning in accessible language."
    elif feature_type == "task":
        return base_prompt + "\n\nSuggest age-appropriate, engaging activities and scaffolds that support diverse learning needs and curriculum objectives."
    
    return base_prompt

# Chat function
def chat_with_ai(prompt, feature_type="chat"):
    if not client:
        return "OpenAI client not initialized. Please check your API key."
    
    try:
        system_prompt = get_system_prompt(st.session_state.curriculum, feature_type)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# File processing functions
def process_uploaded_file(uploaded_file):
    try:
        if uploaded_file.type == "text/plain":
            content = str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type == "text/csv":
            df = pd.read_csv(uploaded_file)
            content = df.to_string()
        else:
            content = "Unsupported file type"
        
        st.session_state.uploaded_content = content
        return content
    except Exception as e:
        return f"Error processing file: {str(e)}"

# Scope & Sequence Visualizer
def create_sequence_timeline(topics_data):
    try:
        if isinstance(topics_data, str):
            # Parse string data into a simple timeline
            topics = [topic.strip() for topic in topics_data.split('\n') if topic.strip()]
            df = pd.DataFrame({
                'Topic': topics,
                'Week': range(1, len(topics) + 1),
                'Duration': [1] * len(topics)
            })
        else:
            df = topics_data
        
        fig = px.timeline(df, x_start='Week', x_end='Week', y='Topic', 
                         title='Curriculum Scope & Sequence Timeline')
        fig.update_layout(height=400)
        return fig
    except Exception as e:
        st.error(f"Error creating timeline: {str(e)}")
        return None

# Sidebar
st.sidebar.title("🎓 Guide")
st.sidebar.markdown("*Your AI Curriculum Assistant*")

# Curriculum selector
curriculum = st.sidebar.selectbox(
    "Select Curriculum Framework:",
    ["Australian Curriculum V9", "Montessori Curriculum Australia"],
    key="curriculum_selector"
)
st.session_state.curriculum = curriculum

st.sidebar.markdown("---")

# File upload section
st.sidebar.subheader("📁 Upload Files")
uploaded_file = st.sidebar.file_uploader(
    "Upload curriculum notes (.txt or .csv):",
    type=['txt', 'csv']
)

if uploaded_file is not None:
    content = process_uploaded_file(uploaded_file)
    st.sidebar.success("File uploaded successfully!")
    with st.sidebar.expander("View uploaded content"):
        st.text(content[:500] + "..." if len(content) > 500 else content)

st.sidebar.markdown("---")

# Quick access buttons
st.sidebar.subheader("🚀 Quick Actions")

if st.sidebar.button("🎯 Generate Lesson", use_container_width=True):
    st.session_state.current_feature = "lesson"

if st.sidebar.button("📋 Scope & Sequence", use_container_width=True):
    st.session_state.current_feature = "sequence"

if st.sidebar.button("👨‍👩‍👧‍👦 Parent Letter", use_container_width=True):
    st.session_state.current_feature = "parent"

if st.sidebar.button("✏️ Student Task", use_container_width=True):
    st.session_state.current_feature = "task"

if st.sidebar.button("🗑️ Clear Chat", use_container_width=True):
    st.session_state.messages = []
    st.session_state.uploaded_content = ""
    st.rerun()

# Main content area
st.title("Guide - AI Curriculum Assistant")
st.markdown(f"*Currently using: {st.session_state.curriculum}*")

# Feature-specific interfaces
if 'current_feature' in st.session_state:
    feature = st.session_state.current_feature
    
    if feature == "lesson":
        st.subheader("🎯 Lesson Idea Generator")
        topic = st.text_input("Enter a topic for lesson ideas:")
        year_level = st.selectbox("Select year level:", 
                                 ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", 
                                  "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"])
        
        if st.button("Generate Lesson Ideas"):
            if topic:
                prompt = f"Generate detailed lesson ideas for the topic '{topic}' suitable for {year_level} students."
                response = chat_with_ai(prompt, "lesson")
                st.markdown(response)
                
                # Add to chat history
                st.session_state.messages.append({
                    "role": "user", 
                    "content": f"Lesson ideas for {topic} ({year_level})",
                    "timestamp": datetime.now().strftime("%H:%M")
                })
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now().strftime("%H:%M")
                })
    
    elif feature == "sequence":
        st.subheader("📋 Scope & Sequence Visualizer")
        
        col1, col2 = st.columns(2)
        
        with col1:
            topics_text = st.text_area(
                "Enter topics (one per line) or upload a CSV:",
                height=200,
                placeholder="Mathematics - Number sense\nScience - Living things\nEnglish - Reading comprehension"
            )
        
        with col2:
            if st.button("Generate Scope & Sequence"):
                if topics_text or st.session_state.uploaded_content:
                    content_to_process = topics_text if topics_text else st.session_state.uploaded_content
                    prompt = f"Create a logical scope and sequence for these topics, considering learning progression and curriculum alignment:\n\n{content_to_process}"
                    response = chat_with_ai(prompt, "sequence")
                    st.markdown(response)
                    
                    # Create timeline visualization
                    fig = create_sequence_timeline(content_to_process)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
    
    elif feature == "parent":
        st.subheader("👨‍👩‍👧‍👦 Parent Communication Helper")
        
        communication_type = st.selectbox(
            "Type of communication:",
            ["General curriculum information", "Unit overview", "Assessment explanation", 
             "Home learning suggestions", "Student progress update"]
        )
        
        subject_area = st.text_input("Subject area or topic:")
        year_level = st.selectbox("Year level:", 
                                 ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", 
                                  "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"])
        
        if st.button("Generate Parent Communication"):
            if subject_area:
                prompt = f"Write a {communication_type.lower()} for parents about {subject_area} for {year_level} students. Make it clear, informative, and accessible."
                response = chat_with_ai(prompt, "parent")
                st.markdown(response)
    
    elif feature == "task":
        st.subheader("✏️ Student Task Generator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            subject = st.text_input("Subject area:")
            topic = st.text_input("Specific topic:")
            year_level = st.selectbox("Year level:", 
                                     ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", 
                                      "Year 5", "Year 6", "Year 7", "Year 8", "Year 9", "Year 10"])
        
        with col2:
            task_type = st.selectbox(
                "Task type:",
                ["Individual activity", "Group project", "Assessment task", 
                 "Home learning", "Extension activity", "Support activity"]
            )
            
            difficulty = st.selectbox("Difficulty level:", ["Basic", "Standard", "Advanced"])
        
        if st.button("Generate Student Tasks"):
            if subject and topic:
                prompt = f"Create {task_type.lower()} tasks for {subject} focusing on {topic} for {year_level} students at {difficulty.lower()} level. Include scaffolds and differentiation options."
                response = chat_with_ai(prompt, "task")
                st.markdown(response)

# Chat interface
st.markdown("---")
st.subheader("💬 Chat with Guide")

# Display chat history
if st.session_state.messages:
    for message in st.session_state.messages[-10:]:  # Show last 10 messages
        with st.chat_message(message["role"]):
            st.markdown(f"**{message['timestamp']}** - {message['content']}")

# Chat input
user_input = st.chat_input("Ask me anything about curriculum, teaching, or education...")

if user_input:
    # Add user message to history
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input,
        "timestamp": datetime.now().strftime("%H:%M")
    })
    
    # Get AI response
    response = chat_with_ai(user_input)
    
    # Add assistant message to history
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response,
        "timestamp": datetime.now().strftime("%H:%M")
    })
    
    # Display the new messages
    with st.chat_message("user"):
        st.markdown(f"**{datetime.now().strftime('%H:%M')}** - {user_input}")
    
    with st.chat_message("assistant"):
        st.markdown(f"**{datetime.now().strftime('%H:%M')}** - {response}")

# Footer
st.markdown("---")
st.markdown("*Guide - Powered by AI to support Australian and Montessori curriculum teaching*")