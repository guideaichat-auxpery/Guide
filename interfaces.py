import streamlit as st
from utils import call_openai_api, get_max_tokens_for_user_type
import PyPDF2
from docx import Document
from PIL import Image
import pytesseract
import io
import uuid
import json
from database import get_db, log_student_activity, database_available

def show_lesson_planning_interface():
    """Educational planning interface for educators with Australian Curriculum alignment"""
    # Ensure planning messages are initialized separately
    if 'planning_messages' not in st.session_state:
        st.session_state.planning_messages = []
        
    st.markdown("### 📚 Montessori Educational Planning Tool")
    st.markdown("*Create comprehensive lesson plans and scope & sequence with Australian Curriculum V.9 alignment*")
    
    # Age group selector
    age_group = st.selectbox(
        "Select Age Group:",
        ["3-6", "6-9", "9-12", "12-15"],
        format_func=lambda x: {
            "3-6": "Early Years (3-6)",
            "6-9": "Lower Primary (6-9)", 
            "9-12": "Upper Primary (9-12)",
            "12-15": "Adolescent (12-15)"
        }[x]
    )
    
    # Planning type selector
    planning_type = st.selectbox(
        "Planning Type:",
        ["lesson_plan", "scope_sequence", "curriculum_alignment", "assessment_rubric"],
        format_func=lambda x: {
            "lesson_plan": "Individual Lesson Plan",
            "scope_sequence": "Scope & Sequence Creation",
            "curriculum_alignment": "Curriculum Alignment Review",
            "assessment_rubric": "Assessment Rubric"
        }[x]
    )
    
    # Display chat history
    for message in st.session_state.planning_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Document upload section
    st.markdown("#### 📄 Upload Documents for Review")
    uploaded_files = st.file_uploader(
        "Upload lesson plans, curriculum documents, or student work for feedback",
        accept_multiple_files=True,
        type=['txt', 'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png']
    )
    
    # Quick planning templates based on age group
    st.markdown(f"#### Quick {age_group} Planning Templates:")
    
    if age_group == "3-6":
        templates = [
            f"Create a practical life lesson for 3-6 year olds with AC V.9 alignment for {planning_type}",
            f"Design a sensorial exploration activity with Montessori materials for {planning_type}",
            f"Plan a grace and courtesy lesson with cultural connections for {planning_type}",
            f"Develop a language enrichment activity for early literacy for {planning_type}"
        ]
    elif age_group == "6-9":
        templates = [
            f"Create a cosmic education lesson connecting math and science for {planning_type}",
            f"Design a cultural studies project on Australian geography for {planning_type}",
            f"Plan a collaborative research activity for 6-9 year olds for {planning_type}",
            f"Develop mathematical concepts with concrete materials for {planning_type}"
        ]
    elif age_group == "9-12":
        templates = [
            f"Create a cosmic education Great Story extension for {planning_type}",
            f"Design an independent research project on Australian history for {planning_type}",
            f"Plan a mathematical exploration of real-world applications for {planning_type}",
            f"Develop a scientific investigation with hypothesis testing for {planning_type}"
        ]
    else:  # 12-15
        templates = [
            f"Create an adolescent community project with real-world impact for {planning_type}",
            f"Design a micro-economy activity for practical life skills for {planning_type}",
            f"Plan a leadership and social justice exploration for {planning_type}",
            f"Develop an interdisciplinary inquiry project for {planning_type}"
        ]
    
    # Display templates as clickable buttons
    cols = st.columns(2)
    for idx, template in enumerate(templates):
        with cols[idx % 2]:
            if st.button(template, key=f"template_{idx}"):
                st.session_state.planning_prompt = template
                st.rerun()
    
    # Chat input
    if prompt := st.chat_input("What would you like help planning today?"):
        # Add user message to chat history
        st.session_state.planning_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process uploaded documents
        document_context = ""
        if uploaded_files:
            for file in uploaded_files:
                file_content = extract_file_content(file)
                if file_content:
                    document_context += f"\n\n---\nDocument: {file.name}\n{file_content}\n---\n"
        
        # Prepare full prompt
        full_prompt = prompt
        if document_context:
            full_prompt = f"{prompt}\n\nRelevant documents:\n{document_context}"
        
        # Get AI response
        system_prompt = f"""You are a Montessori educational planning assistant with deep knowledge of:
        - Montessori philosophy and cosmic education principles
        - Australian Curriculum Version 9 (V.9) learning areas and content descriptors
        - Developmentally appropriate practices for {age_group} year olds
        - Scope and sequence planning
        - Assessment rubric design
        
        Current planning context:
        - Age Group: {age_group}
        - Planning Type: {planning_type}
        
        Provide practical, classroom-ready guidance that bridges Montessori principles with Australian Curriculum requirements.
        Include specific AC V.9 codes when relevant and suggest concrete Montessori materials or activities."""
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.planning_messages[-1:],
                    system_prompt,
                    is_student=False,
                    age_group=age_group
                )
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.planning_messages.append({"role": "assistant", "content": response})

def extract_file_content(file):
    """Extract text content from uploaded files"""
    try:
        if file.type == "text/plain":
            return file.read().decode('utf-8')
        elif file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            doc = Document(io.BytesIO(file.read()))
            return "\n".join([para.text for para in doc.paragraphs])
        elif file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(file)
            return pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"Error extracting content from {file.name}: {str(e)}")
        return None

def show_companion_interface():
    """Montessori companion interface for general educational conversations"""
    # Ensure companion messages are initialized separately
    if 'companion_messages' not in st.session_state:
        st.session_state.companion_messages = []
    
    st.markdown("### 🗨️ Montessori Companion")
    st.markdown("*Your philosophical guide to Montessori principles, cosmic education, and educational wisdom*")
    
    # Display chat history
    for message in st.session_state.companion_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Quick conversation starters
    st.markdown("#### Quick Conversation Starters:")
    quick_prompts = [
        "Explain the concept of cosmic education",
        "How do I introduce a new material?",
        "What is the prepared environment?",
        "Help me understand the sensitive periods"
    ]
    
    cols = st.columns(2)
    for idx, quick_prompt in enumerate(quick_prompts):
        with cols[idx % 2]:
            if st.button(quick_prompt, key=f"quick_{idx}"):
                st.session_state.companion_prompt = quick_prompt
                st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask me about Montessori philosophy, cosmic education, or educational approaches..."):
        # Add user message to chat history
        st.session_state.companion_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        system_prompt = """You are a warm, humble Montessori educational companion with deep knowledge of:
        - Maria Montessori's original writings and philosophy
        - Cosmic education and the Great Stories
        - Montessori National Curriculum (2011)
        - Child development across all planes of development
        - The prepared environment and observation
        
        Provide thoughtful, philosophical guidance rooted in Montessori principles. Speak warmly and avoid jargon.
        Connect big ideas to practical classroom applications. Emphasize the child's place in the universe."""
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.companion_messages[-1:],
                    system_prompt,
                    is_student=False
                )
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.companion_messages.append({"role": "assistant", "content": response})

def show_student_interface():
    """Student learning interface with Montessori-guided tutoring"""
    # Get student info from session
    student_id = st.session_state.get('user_id')
    student_name = st.session_state.get('user_name', 'Student')
    age_group = st.session_state.get('age_group', 'unknown')
    
    # Initialize student-specific session ID if not exists
    if 'student_session_id' not in st.session_state:
        st.session_state.student_session_id = str(uuid.uuid4())
    
    # Ensure student messages are initialized separately
    if 'student_messages' not in st.session_state:
        st.session_state.student_messages = []
        # Log session start
        db = get_db()
        if db and student_id:
            try:
                log_student_activity(
                    db, 
                    student_id, 
                    'session_start', 
                    session_id=st.session_state.student_session_id
                )
            except Exception as e:
                print(f"Error logging session start: {str(e)}")
            finally:
                db.close()
    
    st.markdown(f"### 🌟 Welcome, {student_name}!")
    st.markdown("*Your Montessori Learning Companion - Ask questions, explore ideas, discover connections*")
    
    # Display chat history
    for message in st.session_state.student_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to learn about today?"):
        # Add user message to chat history
        st.session_state.student_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Log the student's prompt
        db = get_db()
        if db and student_id:
            try:
                log_student_activity(
                    db, 
                    student_id, 
                    'learning_question', 
                    prompt_text=prompt,
                    session_id=st.session_state.student_session_id
                )
            except Exception as e:
                print(f"Error logging prompt: {str(e)}")
            finally:
                db.close()
        
        # Get AI response
        system_prompt = f"""You are a warm, encouraging Montessori learning companion for a student in the {age_group} age group.
        
        Your role is to:
        - Guide discovery through questions rather than just providing answers
        - Connect learning to the cosmic story and the child's place in the universe
        - Use age-appropriate language and examples
        - Encourage wonder, curiosity, and independent thinking
        - Make connections across subject areas
        - Celebrate the student's questions and observations
        
        Keep responses conversational, engaging, and developmentally appropriate for {age_group}."""
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.student_messages[-1:],
                    system_prompt,
                    is_student=True,
                    age_group=age_group
                )
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.student_messages.append({"role": "assistant", "content": response})
        
        # Log the AI response
        db = get_db()
        if db and student_id:
            try:
                log_student_activity(
                    db, 
                    student_id, 
                    'learning_response', 
                    prompt_text=prompt,
                    response_text=response,
                    session_id=st.session_state.student_session_id
                )
            except Exception as e:
                print(f"Error logging response: {str(e)}")
            finally:
                db.close()

def show_student_dashboard_interface():
    """Student observation dashboard for educators"""
    st.markdown("### 📊 Student Dashboard")
    st.markdown("*View student learning activities, engagement patterns, and manage access*")
    
    if not database_available:
        st.warning("Student dashboard requires database connection. Please contact support.")
        return
    
    # Get educator info
    educator_id = st.session_state.get('user_id')
    
    db = get_db()
    if not db:
        st.error("Database connection not available")
        return
    
    try:
        # Get all students accessible to this educator
        from database import get_educator_accessible_students
        students = get_educator_accessible_students(db, educator_id)
        
        if not students:
            st.info("No students found. Create student accounts to get started.")
            return
        
        # Student selector
        selected_student = st.selectbox(
            "Select Student:",
            students,
            format_func=lambda s: f"{s.full_name} ({s.age_group})"
        )
        
        if selected_student:
            # Check if current educator is primary educator
            is_primary_educator = selected_student.educator_id == educator_id
            
            # Display student info
            st.markdown(f"## {selected_student.full_name}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Age Group", selected_student.age_group or "Not specified")
            with col2:
                st.metric("Primary Educator", "You" if is_primary_educator else selected_student.educator.full_name)
            with col3:
                st.metric("Status", "Active" if selected_student.is_active else "Inactive")
            
            # Tabs for different views
            tab1, tab2 = st.tabs(["📚 Learning Activity", "🔐 Access Management"])
            
            with tab1:
                # Get student activities
                from database import get_student_activities
                activities = get_student_activities(db, selected_student.id, limit=50)
                
                if activities:
                    # Show summary metrics
                    st.markdown("### 📈 Engagement Summary")
                    col1, col2, col3 = st.columns(3)
                    
                    questions = [a for a in activities if a.activity_type == 'learning_question']
                    responses = [a for a in activities if a.activity_type == 'learning_response']
                    sessions = set([a.session_id for a in activities if a.session_id])
                    
                    with col1:
                        st.metric("Questions Asked", len(questions))
                    with col2:
                        st.metric("Responses Received", len(responses))
                    with col3:
                        st.metric("Learning Sessions", len(sessions))
                    
                    # Activity timeline
                    st.markdown("### 📝 Activity Timeline")
                    
                    for activity in activities:
                        with st.expander(
                            f"{activity.activity_type.replace('_', ' ').title()} - {activity.created_at.strftime('%Y-%m-%d %H:%M')}",
                            expanded=False
                        ):
                            if activity.prompt_text:
                                st.markdown("**Question:**")
                                st.write(activity.prompt_text)
                            
                            if activity.response_text:
                                st.markdown("**Response:**")
                                st.write(activity.response_text)
                            
                            if activity.session_id:
                                st.caption(f"Session ID: {activity.session_id}")
                else:
                    st.info("No learning activities recorded yet.")
            
            with tab2:
                st.markdown(f"### Access Management for {selected_student.full_name}")
                
                if not is_primary_educator:
                    st.info("You have viewing access to this student. Only the primary educator can manage access permissions.")
                else:
                    # Show current access list
                    st.markdown("#### Educators with Access")
                    
                    # Get all accessible educators for this student using the new function
                    from database import get_student_access_educators
                    accessible_educators = get_student_access_educators(db, selected_student.id)
                    
                    if accessible_educators:
                        for educator in accessible_educators:
                            if educator.id != educator_id:  # Don't show primary educator
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"📧 {educator.full_name} ({educator.email})")
                                with col2:
                                    if st.button(f"Remove", key=f"remove_{educator.id}"):
                                        from database import revoke_educator_access
                                        if revoke_educator_access(db, educator.id, selected_student.id, educator_id):
                                            st.success(f"Access removed for {educator.full_name}")
                                            st.rerun()
                                        else:
                                            st.error("Failed to remove access")
                    else:
                        st.info("No additional educators have access to this student.")
                    
                    # Add new educator access
                    st.markdown("#### Grant Access to Another Educator")
                    
                    # Get all educators except current one
                    from database import User
                    all_educators = db.query(User).filter(
                        User.user_type == "educator",
                        User.id != educator_id,
                        User.is_active == True
                    ).all()
                    
                    if all_educators:
                        # Filter out educators who already have access
                        accessible_educator_ids = [edu.id for edu in accessible_educators]
                        available_educators = [
                            edu for edu in all_educators 
                            if edu.id not in accessible_educator_ids
                        ]
                        
                        if available_educators:
                            selected_educator = st.selectbox(
                                "Select educator to grant access:",
                                available_educators,
                                format_func=lambda e: f"{e.full_name} ({e.email})"
                            )
                            
                            if st.button("Grant Access", key="grant_access"):
                                from database import grant_educator_access
                                if grant_educator_access(db, selected_educator.id, selected_student.id, educator_id):
                                    st.success(f"Access granted to {selected_educator.full_name}")
                                    st.rerun()
                                else:
                                    st.error("Failed to grant access")
                        else:
                            st.info("All educators already have access to this student.")
                    else:
                        st.info("No other educators available to grant access to.")
            
    except Exception as e:
        st.error(f"Error loading student data: {str(e)}")
        print(f"Dashboard error: {str(e)}")
    
    finally:
        if db:
            db.close()

def show_great_story_interface():
    """Montessori Great Story creator interface for educators"""
    st.markdown("### 📖 Montessori Great Story Creator")
    st.markdown("*Develop inspiring cosmic education stories that spark imagination and curiosity*")
    
    if not database_available:
        st.info("Stories will not be saved without database connection. Your stories will be available during this session only.")
    
    educator_id = st.session_state.get('user_id')
    
    # Tabs for creating new stories and viewing saved stories
    tab1, tab2 = st.tabs(["✨ Create New Story", "📚 My Saved Stories"])
    
    with tab1:
        st.markdown("#### Theme or Topic")
        st.markdown("*Enter a theme or topic to develop a Montessori Great Story*")
        
        # Theme/topic input
        theme = st.text_input("Story Theme or Topic:", placeholder="e.g., The Story of Water, The Coming of Life, Ancient Civilizations")
        
        # Age group selector
        age_group = st.selectbox(
            "Target Age Group:",
            ["3-6", "6-9", "9-12", "12-15", "All Ages"],
            format_func=lambda x: {
                "3-6": "Early Years (3-6)",
                "6-9": "Lower Primary (6-9)", 
                "9-12": "Upper Primary (9-12)",
                "12-15": "Adolescent (12-15)",
                "All Ages": "All Ages"
            }[x]
        )
        
        # Story development prompts
        st.markdown("#### Story Development Assistance")
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("Generate Story Outline", use_container_width=True):
                if theme:
                    system_prompt = f"""You are a Montessori Great Story specialist with deep knowledge of cosmic education principles.
                    
                    Create an inspiring story outline for the theme: "{theme}"
                    Target age group: {age_group}
                    
                    The outline should:
                    - Begin with wonder and capture imagination
                    - Connect to the cosmic story and the child's place in the universe
                    - Include sensory details and vivid imagery
                    - Build toward questions for further exploration
                    - Follow Montessori Great Story principles
                    - Be developmentally appropriate for {age_group}
                    
                    Provide a detailed outline with key story beats and suggested narrative elements."""
                    
                    with st.spinner("Generating story outline..."):
                        response = call_openai_api(
                            [{"role": "user", "content": f"Create a Great Story outline for: {theme}"}],
                            system_prompt,
                            is_student=False
                        )
                        st.session_state.story_outline = response
                        st.markdown(response)
                else:
                    st.warning("Please enter a theme or topic first.")
        
        with cols[1]:
            if st.button("Get Story Ideas", use_container_width=True):
                if theme:
                    system_prompt = f"""You are a Montessori Great Story specialist.
                    
                    Generate creative ideas and angles for developing a Great Story about: "{theme}"
                    Target age group: {age_group}
                    
                    Provide:
                    - 3-4 different narrative approaches
                    - Key cosmic connections to emphasize
                    - Suggested sensory elements and imagery
                    - Questions to spark further exploration
                    - Materials or experiences that could accompany the story"""
                    
                    with st.spinner("Generating ideas..."):
                        response = call_openai_api(
                            [{"role": "user", "content": f"Generate Great Story ideas for: {theme}"}],
                            system_prompt,
                            is_student=False
                        )
                        st.markdown(response)
                else:
                    st.warning("Please enter a theme or topic first.")
        
        # Story content area
        st.markdown("#### Your Story")
        story_title = st.text_input("Story Title:", value=theme if theme else "")
        story_content = st.text_area(
            "Story Content:",
            height=400,
            placeholder="Write or paste your Great Story here...\n\nYou can develop it based on the AI suggestions above, or write your own narrative.",
            value=st.session_state.get('story_outline', '')
        )
        
        # Keywords/tags
        keywords = st.text_input("Keywords (comma-separated):", placeholder="e.g., water cycle, cosmic, interconnection")
        
        # Save button
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("💾 Save Story", type="primary", use_container_width=True):
                if story_title and story_content:
                    db = get_db()
                    if db and educator_id:
                        try:
                            from database import create_great_story
                            story = create_great_story(
                                db,
                                educator_id=educator_id,
                                title=story_title,
                                theme=theme,
                                content=story_content,
                                age_group=age_group,
                                keywords=keywords
                            )
                            st.success(f"✅ Story '{story_title}' saved successfully!")
                            st.session_state.story_outline = ''
                        except Exception as e:
                            st.error(f"Error saving story: {str(e)}")
                        finally:
                            db.close()
                    else:
                        st.warning("Cannot save story - database connection required.")
                else:
                    st.warning("Please provide both a title and content for your story.")
        
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.story_outline = ''
                st.rerun()
    
    with tab2:
        st.markdown("#### Your Saved Great Stories")
        
        db = get_db()
        if db and educator_id:
            try:
                from database import get_educator_great_stories, delete_great_story
                stories = get_educator_great_stories(db, educator_id)
                
                if stories:
                    for story in stories:
                        with st.expander(f"📖 {story.title} ({story.age_group}) - {story.updated_at.strftime('%Y-%m-%d')}"):
                            st.markdown(f"**Theme:** {story.theme}")
                            if story.keywords:
                                st.markdown(f"**Keywords:** {story.keywords}")
                            st.markdown("**Story Content:**")
                            st.write(story.content)
                            
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                if st.button(f"📋 Copy to Clipboard", key=f"copy_{story.id}"):
                                    st.code(story.content, language=None)
                            with col2:
                                if st.button(f"✏️ Edit", key=f"edit_{story.id}"):
                                    st.info("Switch to 'Create New Story' tab to edit. Copy the content and modify as needed.")
                            with col3:
                                if st.button(f"🗑️ Delete", key=f"delete_{story.id}"):
                                    if delete_great_story(db, story.id):
                                        st.success("Story deleted!")
                                        st.rerun()
                else:
                    st.info("No saved stories yet. Create your first Great Story in the 'Create New Story' tab!")
            except Exception as e:
                st.error(f"Error loading stories: {str(e)}")
            finally:
                db.close()
        else:
            st.info("Database connection required to view saved stories.")

def show_planning_notes_interface():
    """Notes and planning workspace for educators"""
    st.markdown("### 📝 Planning Notes & Workspace")
    st.markdown("*Your personal workspace for planning, notes, resources, and materials organization*")
    
    if not database_available:
        st.info("Notes will not be saved without database connection. Your notes will be available during this session only.")
    
    educator_id = st.session_state.get('user_id')
    
    # Tabs for creating new notes and viewing saved notes
    tab1, tab2 = st.tabs(["📝 Active Workspace", "📂 My Saved Notes"])
    
    with tab1:
        # Note selection or creation
        st.markdown("#### Select or Create Note")
        
        db = get_db()
        existing_notes = []
        if db and educator_id:
            try:
                from database import get_educator_planning_notes
                existing_notes = get_educator_planning_notes(db, educator_id)
            except Exception as e:
                print(f"Error loading notes: {str(e)}")
            finally:
                db.close()
        
        # Create new or select existing
        col1, col2 = st.columns([3, 1])
        with col1:
            if existing_notes:
                note_options = ["-- Create New Note --"] + [f"{note.title}" for note in existing_notes]
                selected_note_name = st.selectbox("Select Note:", note_options)
                
                if selected_note_name != "-- Create New Note --":
                    # Load selected note
                    selected_note = next((n for n in existing_notes if n.title == selected_note_name), None)
                    if selected_note:
                        st.session_state.active_note_id = selected_note.id
                        st.session_state.note_title = selected_note.title
                        st.session_state.note_content = selected_note.content
                        st.session_state.note_materials = selected_note.materials or ""
                        try:
                            st.session_state.note_chapters = json.loads(selected_note.chapters) if selected_note.chapters else []
                        except:
                            st.session_state.note_chapters = []
                else:
                    # New note
                    st.session_state.active_note_id = None
                    if 'note_title' not in st.session_state:
                        st.session_state.note_title = ""
                    if 'note_content' not in st.session_state:
                        st.session_state.note_content = ""
                    if 'note_materials' not in st.session_state:
                        st.session_state.note_materials = ""
                    if 'note_chapters' not in st.session_state:
                        st.session_state.note_chapters = []
            else:
                # No existing notes, create new
                st.session_state.active_note_id = None
                if 'note_title' not in st.session_state:
                    st.session_state.note_title = ""
                if 'note_content' not in st.session_state:
                    st.session_state.note_content = ""
                if 'note_materials' not in st.session_state:
                    st.session_state.note_materials = ""
                if 'note_chapters' not in st.session_state:
                    st.session_state.note_chapters = []
        
        with col2:
            if st.button("🆕 New Note", use_container_width=True):
                st.session_state.active_note_id = None
                st.session_state.note_title = ""
                st.session_state.note_content = ""
                st.session_state.note_materials = ""
                st.session_state.note_chapters = []
                st.rerun()
        
        # Note title
        note_title = st.text_input("Note Title:", value=st.session_state.get('note_title', ''), placeholder="e.g., Week 3 Planning, Science Materials List, Great Lessons Preparation")
        st.session_state.note_title = note_title
        
        # Chapter/Section organization
        st.markdown("#### Chapters/Sections")
        chapters = st.session_state.get('note_chapters', [])
        
        col1, col2 = st.columns([4, 1])
        with col1:
            new_chapter = st.text_input("Add Chapter/Section:", placeholder="e.g., Introduction, Week 1, Materials Needed")
        with col2:
            if st.button("➕ Add", use_container_width=True):
                if new_chapter:
                    chapters.append(new_chapter)
                    st.session_state.note_chapters = chapters
                    st.rerun()
        
        # Display chapters
        if chapters:
            st.markdown("**Current Chapters:**")
            for idx, chapter in enumerate(chapters):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{idx + 1}. {chapter}")
                with col2:
                    if st.button("🗑️", key=f"del_chapter_{idx}"):
                        chapters.pop(idx)
                        st.session_state.note_chapters = chapters
                        st.rerun()
        
        # Main content area
        st.markdown("#### Content")
        note_content = st.text_area(
            "Type, paste, or organize your planning content here:",
            value=st.session_state.get('note_content', ''),
            height=300,
            placeholder="Write your notes, paste resources, organize ideas...\n\nYou can structure your content using the chapters above."
        )
        st.session_state.note_content = note_content
        
        # Materials list
        st.markdown("#### Materials & Resources")
        note_materials = st.text_area(
            "List materials, resources, links, or equipment needed:",
            value=st.session_state.get('note_materials', ''),
            height=150,
            placeholder="• Montessori pink tower\n• Number rods\n• https://example.com/resource\n• Colored pencils"
        )
        st.session_state.note_materials = note_materials
        
        # Image upload section
        st.markdown("#### 📷 Images & Visual Resources")
        uploaded_images = st.file_uploader(
            "Upload images, diagrams, or visual resources",
            accept_multiple_files=True,
            type=['jpg', 'jpeg', 'png', 'gif']
        )
        
        if uploaded_images:
            st.markdown("**Uploaded Images:**")
            cols = st.columns(3)
            for idx, img in enumerate(uploaded_images):
                with cols[idx % 3]:
                    st.image(img, caption=img.name, use_container_width=True)
        
        # Save button
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("💾 Save Note", type="primary", use_container_width=True):
                if note_title:
                    db = get_db()
                    if db and educator_id:
                        try:
                            from database import create_planning_note, update_planning_note
                            
                            chapters_json = json.dumps(chapters) if chapters else None
                            
                            if st.session_state.get('active_note_id'):
                                # Update existing note
                                update_planning_note(
                                    db,
                                    note_id=st.session_state.active_note_id,
                                    title=note_title,
                                    content=note_content,
                                    chapters=chapters_json,
                                    materials=note_materials
                                )
                                st.success(f"✅ Note '{note_title}' updated successfully!")
                            else:
                                # Create new note
                                note = create_planning_note(
                                    db,
                                    educator_id=educator_id,
                                    title=note_title,
                                    content=note_content,
                                    chapters=chapters_json,
                                    materials=note_materials
                                )
                                st.session_state.active_note_id = note.id
                                st.success(f"✅ Note '{note_title}' saved successfully!")
                        except Exception as e:
                            st.error(f"Error saving note: {str(e)}")
                        finally:
                            db.close()
                    else:
                        st.warning("Cannot save note - database connection required.")
                else:
                    st.warning("Please provide a title for your note.")
        
        with col2:
            if st.button("📋 Copy All Content", use_container_width=True):
                full_content = f"# {note_title}\n\n"
                if chapters:
                    full_content += "## Chapters\n" + "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(chapters)]) + "\n\n"
                full_content += "## Content\n" + note_content + "\n\n"
                if note_materials:
                    full_content += "## Materials\n" + note_materials
                st.code(full_content, language=None)
        
        with col3:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.active_note_id = None
                st.session_state.note_title = ""
                st.session_state.note_content = ""
                st.session_state.note_materials = ""
                st.session_state.note_chapters = []
                st.rerun()
    
    with tab2:
        st.markdown("#### Your Saved Planning Notes")
        
        db = get_db()
        if db and educator_id:
            try:
                from database import get_educator_planning_notes, delete_planning_note
                notes = get_educator_planning_notes(db, educator_id)
                
                if notes:
                    for note in notes:
                        with st.expander(f"📝 {note.title} - {note.updated_at.strftime('%Y-%m-%d %H:%M')}"):
                            # Display chapters if available
                            try:
                                chapters = json.loads(note.chapters) if note.chapters else []
                                if chapters:
                                    st.markdown("**Chapters:**")
                                    for idx, chapter in enumerate(chapters):
                                        st.write(f"{idx + 1}. {chapter}")
                                    st.markdown("---")
                            except:
                                pass
                            
                            # Display content
                            if note.content:
                                st.markdown("**Content:**")
                                st.write(note.content)
                            
                            # Display materials
                            if note.materials:
                                st.markdown("**Materials:**")
                                st.write(note.materials)
                            
                            # Actions
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                if st.button(f"✏️ Open in Workspace", key=f"open_{note.id}"):
                                    st.session_state.active_note_id = note.id
                                    st.session_state.note_title = note.title
                                    st.session_state.note_content = note.content
                                    st.session_state.note_materials = note.materials or ""
                                    try:
                                        st.session_state.note_chapters = json.loads(note.chapters) if note.chapters else []
                                    except:
                                        st.session_state.note_chapters = []
                                    st.rerun()
                            with col2:
                                if st.button(f"📋 Copy Content", key=f"copy_{note.id}"):
                                    st.code(note.content, language=None)
                            with col3:
                                if st.button(f"🗑️ Delete", key=f"delete_{note.id}"):
                                    if delete_planning_note(db, note.id):
                                        st.success("Note deleted!")
                                        st.rerun()
                else:
                    st.info("No saved notes yet. Create your first planning note in the 'Active Workspace' tab!")
            except Exception as e:
                st.error(f"Error loading notes: {str(e)}")
            finally:
                db.close()
        else:
            st.info("Database connection required to view saved notes.")
