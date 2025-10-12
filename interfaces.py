import streamlit as st
from utils import call_openai_api, get_max_tokens_for_user_type, scroll_to_top, add_scroll_to_top_button, scroll_to_latest_response
import PyPDF2
from docx import Document
from PIL import Image
import pytesseract
import io
import uuid
import json
import os
from datetime import datetime
from database import get_db, log_student_activity, database_available

def show_lesson_planning_interface():
    """Educational planning interface for educators with Australian Curriculum alignment"""
    scroll_to_top()
    
    # Ensure planning messages are initialized separately
    if 'planning_messages' not in st.session_state:
        st.session_state.planning_messages = []
        
    st.markdown("### 📚 Montessori Educational Planning Tool")
    st.markdown("*Create comprehensive lesson plans and scope & sequence with Australian Curriculum V.9 alignment*")
    
    # Age group selector with year level display
    from utils import map_age_to_year_levels
    
    age_group = st.selectbox(
        "Select Age Group:",
        ["12-15", "9-12", "6-9", "3-6"],
        format_func=lambda x: {
            "3-6": "Early Years (3-6) → Foundation",
            "6-9": "Lower Primary (6-9) → Years 1-3", 
            "9-12": "Upper Primary (9-12) → Years 4-6",
            "12-15": "Adolescent (12-15) → Years 7-9"
        }[x]
    )
    
    # Display year level mapping
    year_levels = map_age_to_year_levels(age_group)
    if year_levels:
        year_levels_str = ", ".join(year_levels)
        st.caption(f"🎯 Australian Curriculum Year Levels: **{year_levels_str}**")
    
    # Subject multiselect for curriculum alignment (age-appropriate)
    # HASS for Foundation-Year 6, separate subjects for Years 7-9
    if age_group in ["3-6", "6-9", "9-12"]:
        # Foundation to Year 6: Use HASS
        subject_options = ["English", "Mathematics", "Science", "HASS (Humanities and Social Sciences)", 
                          "Design and Technologies", "Digital Technologies", "The Arts", 
                          "Health and Physical Education", "Languages"]
    else:  # 12-15 (Years 7-9)
        # Years 7-9: Use separate humanities subjects
        subject_options = ["English", "Mathematics", "Science", "History", "Geography", 
                          "Business and Economics", "Civics and Citizenship",
                          "Design and Technologies", "Digital Technologies", "The Arts", 
                          "Health and Physical Education", "Languages"]
    
    subjects = st.multiselect(
        "Subject Area(s) for AC V9 alignment:",
        subject_options,
        help="Select one or more subjects to get specific Australian Curriculum V9 content descriptors"
    )
    
    # Planning type selector
    planning_type = st.selectbox(
        "Planning Type:",
        ["lesson_plan", "scope_sequence", "assessment_rubric"],
        format_func=lambda x: {
            "lesson_plan": "Lesson Planning",
            "scope_sequence": "Scope & Sequence Creation",
            "assessment_rubric": "Assessment Rubric"
        }[x]
    )
    
    # Display chat history
    ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
    for message in st.session_state.planning_messages:
        avatar = ai_avatar if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
    
    # Chat input for planning questions
    if prompt := st.chat_input("Ask your planning question..."):
        st.session_state.planning_messages.append({
            "role": "user",
            "content": prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
        with st.chat_message("assistant", avatar=ai_avatar):
            with st.spinner("Planning your lesson..."):
                # Construct system prompt based on planning type
                if planning_type == "lesson_plan":
                    system_context = "You are creating a lesson plan with Montessori principles and Australian Curriculum V9 alignment."
                elif planning_type == "scope_sequence":
                    system_context = "You are developing a scope and sequence document that maps learning across time, integrating Montessori principles with Australian Curriculum V9."
                else:  # assessment_rubric
                    system_context = """You are creating an assessment rubric that balances Montessori observational assessment with Australian Curriculum V9 achievement standards.

IMPORTANT RUBRIC FORMAT REQUIREMENTS:
- Do NOT use letter grades (A, B, C, D) or numerical scores
- Use ONLY these four performance levels as column headers (left to right):
  1. Sophisticated
  2. High Expectation Met
  3. Expectation Met
  4. Developing
- For each criterion, describe what each performance level looks like
- Focus on descriptive, asset-based language that honors the child's development
- Align descriptions with AC V9 achievement standards where appropriate
- Include Montessori observational assessment approaches"""
                
                response = call_openai_api(
                    st.session_state.planning_messages,
                    system_prompt=system_context,
                    age_group=age_group,
                    subject=subjects[0] if subjects else None,
                    subjects=subjects,
                    year_level=year_levels[0] if year_levels else None,
                    curriculum_type="AC_V9",
                    interface_type="lesson_planning"
                )
                
                st.markdown(response)
                st.session_state.planning_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Scroll to beginning of new response
                scroll_to_latest_response()
    
    # Export options
    if st.session_state.planning_messages:
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Export as PDF", use_container_width=True):
                from utils import export_lesson_plan_to_pdf
                # Format conversation into content string
                content = ""
                for msg in st.session_state.planning_messages:
                    if msg['role'] == 'user':
                        content += f"**Educator Question:**\n{msg['content']}\n\n"
                    else:
                        content += f"{msg['content']}\n\n"
                
                # Create title from context
                subject_str = ", ".join(subjects) if subjects else "General"
                title = f"{planning_type} - {subject_str} ({age_group})"
                filename = f"lesson_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                
                pdf_data, filename = export_lesson_plan_to_pdf(content, title, filename)
                st.download_button(
                    label="Download PDF",
                    data=pdf_data,
                    file_name=filename,
                    mime="application/pdf"
                )
        
        with col2:
            if st.button("📝 Export as DOCX", use_container_width=True):
                from utils import export_lesson_plan_to_docx
                # Format conversation into content string
                content = ""
                for msg in st.session_state.planning_messages:
                    if msg['role'] == 'user':
                        content += f"**Educator Question:**\n{msg['content']}\n\n"
                    else:
                        content += f"{msg['content']}\n\n"
                
                # Create title from context
                subject_str = ", ".join(subjects) if subjects else "General"
                title = f"{planning_type} - {subject_str} ({age_group})"
                filename = f"lesson_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                
                docx_data, filename = export_lesson_plan_to_docx(content, title, filename)
                st.download_button(
                    label="Download DOCX",
                    data=docx_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    
    # Add scroll to top button
    add_scroll_to_top_button()


def show_companion_interface():
    """Enhanced Montessori companion interface with conversation history management and persistence"""
    scroll_to_top()
    
    from utils import manage_conversation_history, estimate_tokens
    from database import save_conversation_message, log_educator_prompt, load_conversation_to_session
    
    # Get educator info
    user_id = st.session_state.get('user_id')
    
    # Initialize session-specific conversation ID
    if 'companion_session_id' not in st.session_state:
        st.session_state.companion_session_id = str(uuid.uuid4())
    
    # Ensure companion messages are initialized
    if 'companion_messages' not in st.session_state:
        st.session_state.companion_messages = []
        # Try to load conversation history from database
        if database_available and user_id:
            db = get_db()
            if db:
                try:
                    loaded_messages = load_conversation_to_session(
                        db, st.session_state.companion_session_id, 'companion'
                    )
                    if loaded_messages:
                        st.session_state.companion_messages = loaded_messages
                except Exception as e:
                    print(f"Error loading conversation history: {str(e)}")
                finally:
                    db.close()
    
    st.markdown("### 🗨️ Montessori Companion")
    st.markdown("*Your philosophical guide to Montessori principles, cosmic education, and educational wisdom*")
    
    # Age group selector for companion (optional - defaults to all ages)
    st.markdown("#### 🌱 Select Age Group (Optional)")
    st.markdown("*Choose a specific age range for targeted guidance, or select 'All Ages' for comprehensive support*")
    
    companion_age_options = {
        "All Ages (3-18)": "all",
        "Ages 12-15 (Adolescent)": "12-15",
        "Ages 9-12 (Upper Primary)": "9-12",
        "Ages 6-9 (Lower Primary)": "6-9",
        "Ages 3-6 (Early Years)": "3-6"
    }
    
    selected_age_display = st.selectbox(
        "Age Focus",
        options=list(companion_age_options.keys()),
        key="companion_age_selector",
        label_visibility="collapsed"
    )
    
    companion_age_group = companion_age_options[selected_age_display]
    
    # Manage conversation history (keep last 10 exchanges)
    st.session_state.companion_messages = manage_conversation_history(
        st.session_state.companion_messages, max_history=20
    )
    
    # Check if last message needs a response (from Quick Guide click)
    need_response = (
        len(st.session_state.companion_messages) > 0 and 
        st.session_state.companion_messages[-1]["role"] == "user" and
        (len(st.session_state.companion_messages) == 1 or 
         st.session_state.companion_messages[-2]["role"] == "assistant")
    )
    
    # Display chat history
    ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
    for message in st.session_state.companion_messages:
        avatar = ai_avatar if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
    
    # If last message was from user (Quick Guide), generate response
    if need_response:
        ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
        with st.chat_message("assistant", avatar=ai_avatar):
            with st.spinner("Consulting Montessori wisdom..."):
                response = call_openai_api(
                    st.session_state.companion_messages,
                    age_group=companion_age_group if companion_age_group != "all" else None,
                    interface_type="companion"
                )
                st.markdown(response)
                st.session_state.companion_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Scroll to beginning of new response
                scroll_to_latest_response()
                
                # Save assistant response to database
                if database_available and user_id:
                    db = get_db()
                    if db:
                        try:
                            save_conversation_message(
                                db,
                                session_id=st.session_state.companion_session_id,
                                interface_type='companion',
                                role='assistant',
                                content=response,
                                user_id=user_id,
                                student_id=None
                            )
                        except Exception as e:
                            print(f"Error saving conversation: {str(e)}")
                        finally:
                            db.close()
    
    # Quick conversation starters - Comprehensive Montessori Guide Topics
    st.markdown("#### 📚 Montessori Quick Guides")
    st.markdown("*Click any topic to explore authentic Montessori wisdom from Dr. Montessori's foundational texts*")
    
    quick_prompts = [
        "🌌 What is cosmic education and how do I implement it?",
        "🎯 Explain the sensitive periods in child development",
        "🏛️ What is the prepared environment?",
        "👁️ How do I observe children effectively?",
        "🌱 What is the absorbent mind?",
        "✋ How do I introduce a new material?",
        "🔄 What are the three-period lessons?",
        "🌍 How does Montessori connect to the universe story?",
        "🔬 How do I implement cosmic education in science?",
        "📖 What are the great stories and how do I tell them?",
        "🤝 How do I handle social conflicts using Montessori principles?",
        "🌟 What is normalization and how do I recognize it?",
        "🧘 How do I create a culture of peace in the classroom?",
        "🎨 How does art connect to cosmic education?",
        "📊 How do I assess learning in a Montessori way?"
    ]
    
    cols = st.columns(3)
    for idx, prompt_text in enumerate(quick_prompts):
        with cols[idx % 3]:
            if st.button(prompt_text, key=f"quick_{idx}", use_container_width=True):
                # Add prompt to conversation
                st.session_state.companion_messages.append({
                    "role": "user",
                    "content": prompt_text
                })
                
                # Save to database if available
                if database_available and user_id:
                    db = get_db()
                    if db:
                        try:
                            save_conversation_message(
                                db,
                                session_id=st.session_state.companion_session_id,
                                interface_type='companion',
                                role='user',
                                content=prompt_text,
                                user_id=user_id,
                                student_id=None
                            )
                        except Exception as e:
                            print(f"Error saving conversation: {str(e)}")
                        finally:
                            db.close()
                
                st.rerun()
    
    st.markdown("---")
    
    # Chat input
    if prompt := st.chat_input("Ask your Montessori question..."):
        st.session_state.companion_messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Save user message to database
        if database_available and user_id:
            db = get_db()
            if db:
                try:
                    save_conversation_message(
                        db,
                        session_id=st.session_state.companion_session_id,
                        interface_type='companion',
                        role='user',
                        content=prompt,
                        user_id=user_id,
                        student_id=None
                    )
                    
                    # Log for analytics
                    log_educator_prompt(
                        db, user_id, 'companion', prompt,
                        tokens_used=estimate_tokens(prompt)
                    )
                except Exception as e:
                    print(f"Error saving conversation: {str(e)}")
                finally:
                    db.close()
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
        with st.chat_message("assistant", avatar=ai_avatar):
            with st.spinner("Consulting Montessori wisdom..."):
                response = call_openai_api(
                    st.session_state.companion_messages,
                    age_group=companion_age_group if companion_age_group != "all" else None,
                    interface_type="companion"
                )
                st.markdown(response)
                st.session_state.companion_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Scroll to beginning of new response
                scroll_to_latest_response()
                
                # Save assistant response to database
                if database_available and user_id:
                    db = get_db()
                    if db:
                        try:
                            save_conversation_message(
                                db,
                                session_id=st.session_state.companion_session_id,
                                interface_type='companion',
                                role='assistant',
                                content=response,
                                user_id=user_id,
                                student_id=None
                            )
                        except Exception as e:
                            print(f"Error saving conversation: {str(e)}")
                        finally:
                            db.close()
    
    # Add scroll to top button
    add_scroll_to_top_button()


def show_student_interface():
    """Enhanced student learning interface with curriculum context, conversation history, and persistence"""
    scroll_to_top()
    
    from utils import manage_conversation_history
    from database import save_conversation_message, load_conversation_to_session
    
    # Get student info from session
    student_id = st.session_state.get('user_id')
    student_name = st.session_state.get('user_name', 'Student')
    age_group = st.session_state.get('age_group', 'unknown')
    
    # Initialize student-specific session ID if not exists
    if 'student_session_id' not in st.session_state:
        st.session_state.student_session_id = str(uuid.uuid4())
    
    # Ensure student messages are initialized
    if 'student_messages' not in st.session_state:
        st.session_state.student_messages = []
        # Try to load conversation history from database
        if database_available and student_id:
            db = get_db()
            if db:
                try:
                    loaded_messages = load_conversation_to_session(
                        db, st.session_state.student_session_id, 'student'
                    )
                    if loaded_messages:
                        st.session_state.student_messages = loaded_messages
                    # Log session start
                    log_student_activity(
                        db, 
                        student_id, 
                        'session_start', 
                        session_id=st.session_state.student_session_id
                    )
                except Exception as e:
                    print(f"Error loading conversation/logging session: {str(e)}")
                finally:
                    db.close()
    
    # Custom CSS for enhanced chat styling
    st.markdown("""
    <style>
    /* Subject-based color themes for chat messages */
    .subject-geography { background-color: #A7C796 !important; color: white !important; }
    .subject-history { background-color: #C9A7E3 !important; color: white !important; }
    .subject-science { background-color: #74B3A1 !important; color: white !important; }
    .subject-english { background-color: #E4C29B !important; color: #5B3E2E !important; }
    .subject-civics { background-color: #B8A7C7 !important; color: white !important; }
    
    /* Smooth scroll for chat */
    [data-testid="stChatMessageContainer"] {
        scroll-behavior: smooth;
    }
    
    /* Enhanced chat bubbles */
    [data-testid="stChatMessage"] {
        animation: fadeIn 0.4s ease-in-out;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 🌟 Welcome, {student_name}!")
    st.markdown("*Your personal learning companion for curious minds*")
    
    # Privacy Notice Banner
    st.warning("⚠️ **Privacy Notice:** Do NOT enter personal information (name, birthdate, home/school address, or details of real people). Keep all inputs anonymous.", icon="⚠️")
    
    # Subject selector with visual indicators
    st.markdown("#### 📚 What would you like to explore today?")
    
    # Initialize student-specific subject selector
    if 'student_subjects' not in st.session_state:
        st.session_state.student_subjects = []
    
    # Get age-appropriate subjects
    from utils import map_age_to_year_levels
    year_levels = map_age_to_year_levels(age_group)
    
    # Determine subject options based on age group
    if age_group in ["3-6", "6-9", "9-12"]:
        subject_options = ["English", "Mathematics", "Science", "History", "Geography", 
                          "Art", "Music", "Technology"]
    else:  # adolescent
        subject_options = ["English", "Mathematics", "Science", "History", "Geography", 
                          "Civics", "Economics", "Technology", "Art", "Music"]
    
    selected_subjects = st.multiselect(
        "Choose your subjects:",
        subject_options,
        default=st.session_state.student_subjects,
        help="Select subjects you're interested in learning about"
    )
    st.session_state.student_subjects = selected_subjects
    
    # Year level selector for students
    if 'student_year_selector' not in st.session_state:
        st.session_state.student_year_selector = year_levels[0] if year_levels else "Year 6"
    
    if year_levels and len(year_levels) > 1:
        selected_year_level = st.selectbox(
            "What year level are you studying?",
            year_levels,
            index=year_levels.index(st.session_state.student_year_selector) if st.session_state.student_year_selector in year_levels else 0
        )
        st.session_state.student_year_selector = selected_year_level
    
    # Manage conversation history (keep last 10 messages)
    st.session_state.student_messages = manage_conversation_history(
        st.session_state.student_messages, max_history=10
    )
    
    # Display chat history
    ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🌟"
    for message in st.session_state.student_messages:
        avatar = ai_avatar if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
    
    st.markdown("---")
    
    # File upload for students with rubric support
    st.markdown("#### 📁 Upload your work for feedback (optional)")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_work = st.file_uploader(
            "Share your writing, drawing, or project",
            type=['txt', 'pdf', 'jpg', 'png', 'docx'],
            help="Upload your work for feedback",
            key="work_upload"
        )
    
    with col2:
        uploaded_rubric = st.file_uploader(
            "Upload assessment rubric (optional)",
            type=['txt', 'pdf', 'docx'],
            help="Upload a rubric to guide the feedback",
            key="rubric_upload"
        )
    
    # Feedback button when work is uploaded
    if uploaded_work:
        if st.button("🌟 How about some feedback?", use_container_width=True, type="primary"):
            # Process work file
            work_content = ""
            with st.spinner("Reading your work..."):
                if uploaded_work.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_work.read()))
                    work_content = "\n".join([page.extract_text() for page in pdf_reader.pages])
                elif uploaded_work.type in ["image/jpeg", "image/png"]:
                    try:
                        image = Image.open(uploaded_work)
                        work_content = f"[Student uploaded an image: {uploaded_work.name}]"
                    except:
                        work_content = "[Image could not be processed]"
                elif uploaded_work.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(io.BytesIO(uploaded_work.read()))
                    work_content = "\n".join([para.text for para in doc.paragraphs])
                else:
                    work_content = uploaded_work.read().decode("utf-8")
            
            # Process rubric file if uploaded
            rubric_content = ""
            if uploaded_rubric:
                with st.spinner("Reading rubric..."):
                    if uploaded_rubric.type == "application/pdf":
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_rubric.read()))
                        rubric_content = "\n".join([page.extract_text() for page in pdf_reader.pages])
                    elif uploaded_rubric.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        doc = Document(io.BytesIO(uploaded_rubric.read()))
                        rubric_content = "\n".join([para.text for para in doc.paragraphs])
                    else:
                        rubric_content = uploaded_rubric.read().decode("utf-8")
            
            # Build comprehensive feedback prompt
            feedback_prompt = f"""Please provide detailed, constructive feedback on the following student work.

STUDENT WORK:
{work_content[:2000]}

"""
            if rubric_content:
                feedback_prompt += f"""ASSESSMENT RUBRIC:
{rubric_content[:1500]}

Please assess the work against the rubric criteria, providing specific feedback for each criterion.
"""
            
            feedback_prompt += f"""
FEEDBACK REQUIREMENTS:
1. Assess the work based on the rubric (if provided) and learning standards
2. Provide specific, actionable suggestions for improvement
3. Highlight strengths and areas of growth
4. Connect feedback to broader learning and real-world applications (Montessori approach)
5. Use encouraging, asset-based language that honors student development
6. Reference Australian Curriculum V9 standards for Year {st.session_state.get('student_year_selector', '6')}
7. Suggest next steps to deepen understanding

Keep feedback age-appropriate for {age_group} year olds."""

            # Add to conversation
            st.session_state.student_messages.append({
                "role": "user",
                "content": f"Please review my work: {uploaded_work.name}"
            })
            
            # Get AI feedback
            ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🤖"
            with st.chat_message("assistant", avatar=ai_avatar):
                with st.spinner("Analyzing your work..."):
                    response = call_openai_api(
                        st.session_state.student_messages + [{"role": "system", "content": feedback_prompt}],
                        is_student=True,
                        year_level=st.session_state.get('student_year_selector', 'Year 6'),
                        subjects=selected_subjects if selected_subjects else None,
                        curriculum_type="Blended"
                    )
                    st.markdown(response)
                    st.session_state.student_messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    # Save to database
                    if database_available and student_id:
                        db = get_db()
                        if db:
                            try:
                                save_conversation_message(
                                    db,
                                    session_id=st.session_state.student_session_id,
                                    interface_type='student',
                                    role='assistant',
                                    content=response,
                                    user_id=None,
                                    student_id=student_id
                                )
                            except Exception as e:
                                print(f"Error saving feedback: {str(e)}")
                            finally:
                                db.close()
    
    st.markdown("---")
    
    # Chat input
    uploaded_file = uploaded_work  # Keep backward compatibility
    if prompt := st.chat_input("Ask me anything about your learning..."):
        st.session_state.student_messages.append({
            "role": "user",
            "content": prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process uploaded file if present
        file_context = ""
        if uploaded_file:
            with st.spinner("Reading your file..."):
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                    file_context = "\n".join([page.extract_text() for page in pdf_reader.pages])
                elif uploaded_file.type in ["image/jpeg", "image/png"]:
                    try:
                        image = Image.open(uploaded_file)
                        file_context = f"[Student uploaded an image: {uploaded_file.name}]"
                    except:
                        file_context = "[Image could not be processed]"
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(io.BytesIO(uploaded_file.read()))
                    file_context = "\n".join([para.text for para in doc.paragraphs])
                else:
                    file_context = uploaded_file.read().decode("utf-8")
                
                if file_context:
                    prompt = f"{prompt}\n\n[Student's uploaded content: {file_context[:1000]}]"
        
        # Save conversation and detect curriculum keywords
        if database_available and student_id:
            db = get_db()
            if db:
                try:
                    # Save user message
                    save_conversation_message(
                        db,
                        session_id=st.session_state.student_session_id,
                        interface_type='student',
                        role='user',
                        content=prompt,
                        user_id=None,
                        student_id=student_id
                    )
                    
                    # Detect and track curriculum keywords
                    from utils import detect_trending_keywords, update_trending_keywords
                    detected_keywords = detect_trending_keywords(prompt)
                    
                    # Create extra_data with detected keywords for anonymized tracking
                    extra_data = {
                        'detected_keywords': [
                            {'subject': kw['subject'], 'keyword': kw['keyword']} 
                            for kw in detected_keywords
                        ],
                        'query_id': st.session_state.student_session_id[:8]  # Anonymous query ID
                    }
                    
                    # Log student activity with keyword data
                    log_student_activity(
                        db, 
                        student_id, 
                        'learning_question', 
                        prompt_text=prompt,
                        session_id=st.session_state.student_session_id,
                        extra_data=json.dumps(extra_data)
                    )
                    
                    # Update trending keywords
                    update_trending_keywords(
                        db, 
                        detected_keywords, 
                        st.session_state.student_session_id
                    )
                except Exception as e:
                    print(f"Error saving conversation/logging prompt: {str(e)}")
                finally:
                    db.close()
        
        # Get selected subjects and year level
        selected_subjects = st.session_state.get('student_subjects', [])
        selected_year_level = st.session_state.get('student_year_selector', 'Year 6')
        
        # Get AI response with enhanced features and curriculum alignment
        ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🤖"
        with st.chat_message("assistant", avatar=ai_avatar):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.student_messages,
                    is_student=True,
                    year_level=selected_year_level,
                    subjects=selected_subjects if selected_subjects else None,
                    curriculum_type="Blended",
                    use_conversation_history=True
                )
                
                # Highlight detected keywords in response
                highlighted_response = response
                if detected_keywords:
                    for kw in detected_keywords:
                        keyword = kw['keyword']
                        # Use markdown bold to highlight keywords
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        highlighted_response = re.sub(
                            pattern, 
                            f"**{keyword}**", 
                            highlighted_response, 
                            flags=re.IGNORECASE
                        )
                
                st.markdown(highlighted_response)
                st.session_state.student_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Scroll to beginning of new response
                scroll_to_latest_response()
                
                # Save assistant response
                if database_available and student_id:
                    db = get_db()
                    if db:
                        try:
                            save_conversation_message(
                                db,
                                session_id=st.session_state.student_session_id,
                                interface_type='student',
                                role='assistant',
                                content=response,
                                user_id=None,
                                student_id=student_id
                            )
                            
                            # Log response activity
                            log_student_activity(
                                db, 
                                student_id, 
                                'ai_response', 
                                prompt_text=prompt,
                                response_text=response,
                                session_id=st.session_state.student_session_id
                            )
                        except Exception as e:
                            print(f"Error saving conversation/logging response: {str(e)}")
                        finally:
                            db.close()
    
    # Add scroll to top button
    add_scroll_to_top_button()


def show_student_dashboard_interface():
    """Student observation dashboard for educators"""
    scroll_to_top()
    
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
                    
                    with col1:
                        st.metric("Total Activities", len(activities))
                    with col2:
                        question_count = len([a for a in activities if a.activity_type == 'learning_question'])
                        st.metric("Questions Asked", question_count)
                    with col3:
                        # Get latest activity timestamp
                        if activities:
                            latest = activities[0].created_at.strftime("%Y-%m-%d %H:%M")
                            st.metric("Last Activity", latest)
                    
                    # Activity timeline
                    st.markdown("### 📅 Recent Activity")
                    for activity in activities[:10]:  # Show last 10
                        with st.expander(f"{activity.activity_type} - {activity.created_at.strftime('%Y-%m-%d %H:%M')}"):
                            if activity.prompt_text:
                                st.markdown(f"**Prompt:** {activity.prompt_text}")
                            if activity.response_text:
                                st.markdown(f"**Response:** {activity.response_text[:500]}...")
                            if activity.extra_data:
                                try:
                                    extra = json.loads(activity.extra_data)
                                    if 'detected_keywords' in extra:
                                        keywords = [f"{kw['subject']}: {kw['keyword']}" for kw in extra['detected_keywords']]
                                        st.markdown(f"**Keywords:** {', '.join(keywords)}")
                                except:
                                    pass
                else:
                    st.info("No activities recorded yet for this student.")
            
            with tab2:
                st.markdown("### 🔐 Access Management")
                
                if is_primary_educator:
                    st.info("As the primary educator, you have full access to this student's data.")
                    
                    # Grant access to other educators
                    st.markdown("#### Share Access")
                    from database import get_all_educators, grant_educator_access, get_student_access_educators, is_institution_enforcement_on, User
                    
                    all_educators = get_all_educators(db)
                    
                    # Filter educators by institution if enforcement is ON
                    enforcement_on = is_institution_enforcement_on(db)
                    if enforcement_on:
                        current_educator = db.query(User).filter(User.id == educator_id).first()
                        if current_educator and current_educator.institution_name:
                            # Only show educators from same institution
                            other_educators = [e for e in all_educators 
                                             if e.id != educator_id 
                                             and e.institution_name == current_educator.institution_name]
                        else:
                            other_educators = [e for e in all_educators if e.id != educator_id]
                    else:
                        other_educators = [e for e in all_educators if e.id != educator_id]
                    
                    if other_educators:
                        selected_educator = st.selectbox(
                            "Grant access to educator:",
                            other_educators,
                            format_func=lambda e: f"{e.full_name} ({e.email})"
                        )
                        
                        if st.button("Grant Access"):
                            success, error_msg = grant_educator_access(db, selected_educator.id, selected_student.id, educator_id)
                            if success:
                                st.success(f"✅ Access granted to {selected_educator.full_name}")
                                st.rerun()
                            else:
                                st.error(f"❌ {error_msg or 'Failed to grant access'}")
                    
                    # Show current access list
                    access_list = get_student_access_educators(db, selected_student.id)
                    if access_list:
                        st.markdown("#### Current Access")
                        for educator in access_list:
                            st.markdown(f"- {educator.full_name} ({educator.email})")
                    
                    # Danger zone - remove student
                    st.markdown("---")
                    st.markdown("### ⚠️ Danger Zone")
                    with st.expander("Remove Student Account"):
                        st.warning("This will permanently delete the student account and all associated data. This action cannot be undone.")
                        confirm_text = st.text_input("Type the student's username to confirm:", key="confirm_delete")
                        if st.button("Permanently Delete Student Account", type="primary"):
                            if confirm_text == selected_student.username:
                                from database import delete_student
                                if delete_student(db, selected_student.id):
                                    st.success(f"✅ Successfully removed {selected_student.full_name}'s account")
                                    st.info("Refreshing dashboard...")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to remove student account. Please try again.")
                else:
                    st.info("You have shared access to this student. Contact the primary educator for access management.")
    
    except Exception as e:
        st.error(f"Error loading student data: {str(e)}")
        print(f"Dashboard error: {str(e)}")
    
    finally:
        if db:
            db.close()
    
    # Add scroll to top button
    add_scroll_to_top_button()


def show_great_story_interface():
    """Montessori Great Story creator interface for educators"""
    scroll_to_top()
    
    st.markdown("### 📖 Montessori Great Story Creator")
    st.markdown("*Develop inspiring cosmic education stories that spark imagination and curiosity*")
    
    if not database_available:
        st.info("Stories will not be saved without database connection. Your stories will be available during this session only.")
    
    educator_id = st.session_state.get('user_id')
    
    # Tabs for creating new stories and viewing saved stories
    tab1, tab2, tab3 = st.tabs(["✨ Create New Story", "📚 My Saved Stories", "🌟 Interactive Story Experience"])
    
    with tab1:
        st.markdown("#### Theme or Topic")
        st.markdown("*Enter a theme or topic to develop a Montessori Great Story*")
        
        # Theme/topic input
        theme = st.text_input("Story Theme or Topic:", placeholder="e.g., The Story of Water, The Coming of Life, Ancient Civilizations")
        
        # Age group selector
        age_group = st.selectbox(
            "Target Age Group:",
            ["All Ages", "12-15", "9-12", "6-9", "3-6"],
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
                    
                    with st.spinner("Creating story outline..."):
                        outline = call_openai_api(
                            [{"role": "user", "content": system_prompt}],
                            curriculum_type="Montessori"
                        )
                        st.session_state.story_outline = outline
                        st.markdown(outline)
                else:
                    st.warning("Please enter a theme or topic first")
        
        with cols[1]:
            if st.button("Generate Full Story", use_container_width=True):
                if theme:
                    outline_context = st.session_state.get('story_outline', '')
                    system_prompt = f"""You are a Montessori Great Story specialist with deep knowledge of cosmic education principles.
                    
                    Create a complete Montessori Great Story for the theme: "{theme}"
                    Target age group: {age_group}
                    
                    {f'Based on this outline: {outline_context}' if outline_context else ''}
                    
                    The story should:
                    - Begin with a captivating opening that creates wonder
                    - Weave in cosmic education principles
                    - Use rich, sensory language appropriate for {age_group}
                    - Connect the child to the greater universe story
                    - End with questions or invitations for further exploration
                    - Be approximately 800-1200 words
                    - Follow the Montessori tradition of great stories
                    
                    Write the complete story now."""
                    
                    with st.spinner("Crafting your Great Story..."):
                        story = call_openai_api(
                            [{"role": "user", "content": system_prompt}],
                            curriculum_type="Montessori",
                            max_tokens=3000
                        )
                        st.session_state.generated_story = story
                        st.markdown("### 📖 Your Great Story")
                        st.markdown(story)
                        
                        # Save story option
                        if database_available and educator_id:
                            story_title = st.text_input("Story Title:", value=theme)
                            if st.button("💾 Save Story"):
                                db = get_db()
                                if db:
                                    try:
                                        from database import save_great_story
                                        save_great_story(db, educator_id, story_title, story, age_group, theme)
                                        st.success("✅ Story saved successfully!")
                                    except Exception as e:
                                        st.error(f"Error saving story: {str(e)}")
                                    finally:
                                        db.close()
                else:
                    st.warning("Please enter a theme or topic first")
    
    with tab2:
        if database_available and educator_id:
            db = get_db()
            if db:
                try:
                    from database import get_educator_stories
                    stories = get_educator_stories(db, educator_id)
                    
                    if stories:
                        st.markdown("### 📚 Your Saved Stories")
                        for story in stories:
                            with st.expander(f"{story.title} ({story.age_group}) - {story.created_at.strftime('%Y-%m-%d')}"):
                                st.markdown(f"**Theme:** {story.theme or 'Not specified'}")
                                st.markdown(story.content)
                                
                                # Delete option
                                if st.button(f"🗑️ Delete", key=f"delete_story_{story.id}"):
                                    from database import delete_story
                                    if delete_story(db, story.id):
                                        st.success("Story deleted")
                                        st.rerun()
                    else:
                        st.info("No saved stories yet. Create your first Great Story!")
                except Exception as e:
                    st.error(f"Error loading stories: {str(e)}")
                finally:
                    db.close()
        else:
            st.info("Database connection required to view saved stories.")
    
    with tab3:
        st.markdown("### 🌟 Interactive Story Experience")
        st.markdown("*Create a branching, choose-your-own-adventure style story*")
        
        # Initialize branching story state
        if 'branching_story' not in st.session_state:
            st.session_state.branching_story = {
                'segments': [],
                'current_segment': 0,
                'choices_made': []
            }
        
        # Story setup
        if not st.session_state.branching_story['segments']:
            st.markdown("#### Start Your Interactive Story")
            story_theme = st.text_input("Story Theme:", placeholder="e.g., Journey to the Ancient Forest")
            story_age = st.selectbox("Age Group:", ["6-9", "9-12", "12-15"])
            
            if st.button("Begin Story", use_container_width=True):
                if story_theme:
                    # Generate first segment
                    prompt = f"""Create the opening segment of an interactive Montessori Great Story on the theme: "{story_theme}"
                    Age group: {story_age}
                    
                    Requirements:
                    - Write 150-200 words of engaging narrative
                    - End with a decision point
                    - Provide exactly 2 choices for the reader
                    - Each choice should be 1 sentence
                    - Connect to cosmic education principles
                    
                    Format your response as:
                    NARRATIVE: [story text]
                    CHOICE_A: [first choice]
                    CHOICE_B: [second choice]"""
                    
                    with st.spinner("Creating story opening..."):
                        response = call_openai_api(
                            [{"role": "user", "content": prompt}],
                            curriculum_type="Montessori"
                        )
                        
                        # Parse response
                        if "NARRATIVE:" in response and "CHOICE_A:" in response:
                            st.session_state.branching_story['segments'].append(response)
                            st.rerun()
        else:
            # Display current story segment
            current = st.session_state.branching_story['current_segment']
            segments = st.session_state.branching_story['segments']
            
            if current < len(segments):
                segment_text = segments[current]
                
                # Parse and display narrative
                if "NARRATIVE:" in segment_text:
                    narrative = segment_text.split("CHOICE_A:")[0].replace("NARRATIVE:", "").strip()
                    st.markdown(f"### 📖 Story Continues...")
                    st.markdown(narrative)
                    
                    # Parse and display choices
                    if "CHOICE_A:" in segment_text and "CHOICE_B:" in segment_text:
                        choice_a = segment_text.split("CHOICE_A:")[1].split("CHOICE_B:")[0].strip()
                        choice_b = segment_text.split("CHOICE_B:")[1].strip()
                        
                        st.markdown("#### What happens next?")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button(f"🔵 {choice_a}", use_container_width=True):
                                st.session_state.branching_story['choices_made'].append('A')
                                # Generate next segment based on choice A
                                # ... continuation logic
                        
                        with col2:
                            if st.button(f"🟢 {choice_b}", use_container_width=True):
                                st.session_state.branching_story['choices_made'].append('B')
                                # Generate next segment based on choice B
                                # ... continuation logic


def show_planning_notes_interface():
    """Notes and planning workspace for educators"""
    scroll_to_top()
    
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
                
                # Determine default index based on active_note_id
                default_index = 0
                active_note_id = st.session_state.get('active_note_id')
                if active_note_id:
                    for idx, note in enumerate(existing_notes):
                        if note.id == active_note_id:
                            default_index = idx + 1  # +1 because "Create New Note" is at index 0
                            break
                
                selected_note_name = st.selectbox("Select Note:", note_options, index=default_index)
                
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
                        
                        # Optionally display images
                        if hasattr(selected_note, 'image_data') and selected_note.image_data:
                            try:
                                image = Image.open(io.BytesIO(selected_note.image_data))
                                st.image(image, caption="Attached Image", use_column_width=True)
                            except:
                                pass
                else:
                    # Reset for new note
                    st.session_state.active_note_id = None
                    st.session_state.note_title = ""
                    st.session_state.note_content = ""
                    st.session_state.note_materials = ""
                    st.session_state.note_chapters = []
            else:
                st.info("No existing notes. Create your first note below!")
        
        with col2:
            if st.button("🆕 New Note", use_container_width=True):
                st.session_state.active_note_id = None
                st.session_state.note_title = ""
                st.session_state.note_content = ""
                st.session_state.note_materials = ""
                st.session_state.note_chapters = []
                st.rerun()
        
        st.markdown("---")
        
        # Note editor
        title = st.text_input("Note Title:", value=st.session_state.get('note_title', ''), placeholder="Enter note title...")
        
        # Chapter organization
        st.markdown("#### 📑 Organize by Chapters")
        chapters = st.session_state.get('note_chapters', [])
        
        col1, col2 = st.columns([4, 1])
        with col1:
            new_chapter = st.text_input("Add Chapter:", placeholder="e.g., Week 1, Introduction, Materials List")
        with col2:
            if st.button("➕ Add", use_container_width=True):
                if new_chapter:
                    chapters.append(new_chapter)
                    st.session_state.note_chapters = chapters
                    st.rerun()
        
        if chapters:
            selected_chapter = st.selectbox("Current Chapter:", chapters)
            if st.button("🗑️ Remove Chapter"):
                chapters.remove(selected_chapter)
                st.session_state.note_chapters = chapters
                st.rerun()
        
        # Note content
        content = st.text_area(
            "Notes Content:", 
            value=st.session_state.get('note_content', ''),
            height=300,
            placeholder="Write your planning notes, ideas, observations..."
        )
        
        # Materials list
        st.markdown("#### 🧰 Materials & Resources")
        materials = st.text_area(
            "Materials List:",
            value=st.session_state.get('note_materials', ''),
            height=150,
            placeholder="List materials, resources, or links needed..."
        )
        
        # Image attachment
        uploaded_image = st.file_uploader("Attach Image:", type=['jpg', 'jpeg', 'png'])
        
        # Save button
        if st.button("💾 Save Note", use_container_width=True, type="primary"):
            if title and content:
                db = get_db()
                if db and educator_id:
                    try:
                        from database import create_planning_note, update_planning_note
                        
                        # Process image if uploaded
                        image_data = None
                        if uploaded_image:
                            image_data = uploaded_image.read()
                        
                        chapters_json = json.dumps(chapters) if chapters else None
                        
                        if st.session_state.get('active_note_id'):
                            # Update existing note
                            update_planning_note(
                                db, 
                                st.session_state.active_note_id,
                                title=title, 
                                content=content,
                                chapters=chapters_json,
                                images=image_data,
                                materials=materials
                            )
                            st.success("✅ Note updated successfully!")
                        else:
                            # Save new note
                            note = create_planning_note(
                                db, 
                                educator_id, 
                                title, 
                                content,
                                chapters=chapters_json,
                                images=image_data,
                                materials=materials
                            )
                            st.session_state.active_note_id = note.id
                            st.success("✅ Note saved successfully!")
                        
                        st.session_state.note_title = title
                        st.session_state.note_content = content
                        st.session_state.note_materials = materials
                    except Exception as e:
                        st.error(f"Error saving note: {str(e)}")
                    finally:
                        db.close()
            else:
                st.warning("Please enter both title and content")
    
    with tab2:
        if database_available and educator_id:
            db = get_db()
            if db:
                try:
                    from database import get_educator_planning_notes, delete_planning_note
                    notes = get_educator_planning_notes(db, educator_id)
                    
                    if notes:
                        st.markdown("### 📂 Your Saved Notes")
                        for note in notes:
                            with st.expander(f"{note.title} - {note.created_at.strftime('%Y-%m-%d')}"):
                                st.markdown(note.content)
                                
                                if note.materials:
                                    st.markdown("**Materials:**")
                                    st.markdown(note.materials)
                                
                                if note.chapters:
                                    try:
                                        chapters_list = json.loads(note.chapters)
                                        st.markdown("**Chapters:**")
                                        for ch in chapters_list:
                                            st.markdown(f"- {ch}")
                                    except:
                                        pass
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button(f"✏️ Edit", key=f"edit_{note.id}"):
                                        st.session_state.active_note_id = note.id
                                        st.session_state.auth_mode = "planning_notes"
                                        st.rerun()
                                with col2:
                                    if st.button(f"🗑️ Delete", key=f"delete_{note.id}"):
                                        if delete_planning_note(db, note.id):
                                            st.success("Note deleted")
                                            st.rerun()
                    else:
                        st.info("No saved notes yet.")
                except Exception as e:
                    st.error(f"Error loading notes: {str(e)}")
                finally:
                    db.close()


def show_privacy_policy():
    """Privacy Policy page compliant with Australian Privacy Act 1988"""
    st.markdown("### 🔒 Privacy Policy")
    st.markdown("*Last Updated: October 2025*")
    
    st.markdown("""
    ---
    
    ## Introduction
    
    Welcome to **Guide - Your Montessori Companion** ("Guide," "we," "us," or "our"). This Privacy Policy explains how we collect, use, store, and protect your personal information in accordance with the **Australian Privacy Act 1988** and the **Australian Privacy Principles (APPs)**.
    
    Guide is provided by **Auxpery** and is designed to support educators and students in Montessori and Australian Curriculum-aligned educational settings.
    
    ---
    
    ## 1. Information We Collect (APP 3)
    
    ### Personal Information from Educators:
    - Full name
    - Email address
    - Password (securely hashed - we never store plain text passwords)
    - Usage data (prompts submitted, subjects taught, year levels)
    - Conversation history with our AI assistant
    - Uploaded documents and files for curriculum analysis
    
    ### Personal Information from Students:
    - Full name
    - Username
    - Password (securely hashed)
    - Age group (3-6, 6-9, 9-12, 12-15 years)
    - Learning activities and questions
    - Conversation history with our AI tutor
    - Uploaded files for learning support
    
    ### Automatically Collected Information:
    - Session identifiers (anonymized for students)
    - Curriculum keywords detected in queries
    - Usage timestamps
    - Trending topics for educational insights
    
    ### Information We Do NOT Collect:
    We explicitly instruct students NOT to provide:
    - Home addresses
    - Birthdates
    - Phone numbers
    - Details about real people
    - Any other sensitive personal information
    
    ---
    
    ## 2. How We Use Your Information (APP 6)
    
    We use your personal information for the following purposes:
    
    ### For Educators:
    - Provide AI-assisted lesson planning and curriculum alignment
    - Generate educational content and resources
    - Track usage analytics for service improvement
    - Save conversation history for continuity
    - Enable collaboration features
    
    ### For Students:
    - Provide personalized learning support
    - Track learning progress and engagement
    - Adapt AI responses to age and curriculum level
    - Enable educators to monitor student activities
    
    ### For All Users:
    - Authenticate and secure accounts
    - Improve our AI models and services
    - Comply with legal obligations
    - Communicate important updates
    
    ---
    
    ## 3. Overseas Disclosure (APP 8)
    
    **IMPORTANT: Your data is sent to overseas entities.**
    
    ### OpenAI (United States):
    We use OpenAI's GPT-4o-mini AI model to power our educational assistant. When you submit questions or upload documents, this information is sent to OpenAI's servers in the **United States** for processing.
    
    **What data goes to OpenAI:**
    - Your prompts and questions
    - Conversation history (last 10 messages)
    - Curriculum context and system prompts
    - Content from uploaded documents
    
    **Privacy implications:**
    - OpenAI is subject to US privacy laws, not Australian Privacy Act protections
    - OpenAI's data practices are governed by their privacy policy
    - OpenAI may use data to improve their AI models (subject to their terms)
    
    **Your options:**
    - By using Guide, you consent to this overseas data transfer
    - You can choose not to submit sensitive information
    - Contact us if you have concerns about overseas disclosure
    
    ### Replit (United States):
    Our database and infrastructure are hosted on Replit's platform in the **United States**.
    
    ---
    
    ## 4. Data Security (APP 11)
    
    We implement the following security measures:
    
    ### Technical Safeguards:
    - **Password Security**: All passwords are hashed using bcrypt encryption
    - **SSL/TLS Encryption**: Database connections use SSL encryption
    - **Access Controls**: Role-based access (educators vs. students)
    - **Session Management**: Secure session handling with Streamlit
    
    ### Organizational Safeguards:
    - Limited access to personal data
    - Regular security reviews
    - Incident response procedures
    
    ### Limitations:
    While we implement strong security, no system is 100% secure. We cannot guarantee absolute security of data transmitted over the internet.
    
    ---
    
    ## 5. Data Retention (APP 11.2)
    
    ### Retention Periods:
    - **Educator accounts**: Retained while account is active
    - **Student accounts**: Retained while account is active
    - **Conversation history**: Retained for **2 years** from last activity
    - **Learning analytics**: Retained for **2 years**
    - **Inactive accounts**: Deleted after **3 years** of inactivity
    
    ### Deletion:
    - You can request immediate deletion of your account and data
    - Upon deletion, all personal information is permanently removed
    - Some anonymized analytics may be retained for service improvement
    
    ---
    
    ## 6. Your Privacy Rights (APP 12 & 13)
    
    Under Australian Privacy Act, you have the right to:
    
    ### Access Your Data (APP 12):
    - Request a copy of all personal information we hold about you
    - Receive data in a commonly used electronic format
    - Access is provided free of charge (unless request is excessive)
    
    ### Correct Your Data (APP 13):
    - Request correction of inaccurate or incomplete information
    - We will correct data within 30 days of verified request
    - If we refuse correction, we will provide written reasons
    
    ### Delete Your Data:
    - Request permanent deletion of your account and all associated data
    - Deletion is irreversible and takes effect within 7 days
    - Some data may be retained where legally required
    
    ### Object to Processing:
    - Object to specific uses of your data
    - Withdraw consent for overseas disclosure (may limit functionality)
    
    ---
    
    ## 7. Parental Rights and Student Privacy
    
    ### For Students Under 18:
    - Educators must obtain **parental/guardian consent** before creating student accounts
    - Parents have the right to access their child's data
    - Parents can request deletion of their child's account at any time
    - We provide privacy notices to students warning against sharing personal information
    
    ### School Responsibilities:
    - Schools using Guide must ensure they have appropriate consent mechanisms
    - Schools remain data controllers for student information
    - Guide acts as a data processor on behalf of schools
    
    ---
    
    ## 8. Cookies and Tracking
    
    Guide uses:
    - **Session cookies**: For authentication and session management (essential)
    - **Streamlit cookies**: For application functionality (essential)
    - We do NOT use advertising or third-party tracking cookies
    
    ---
    
    ## 9. Changes to This Policy (APP 1)
    
    We may update this Privacy Policy to reflect:
    - Changes in privacy laws
    - New features or services
    - Feedback from users or regulators
    
    **Notification:**
    - We will notify users of material changes via email or in-app notice
    - Continued use after changes constitutes acceptance
    - Previous versions available upon request
    
    ---
    
    ## 10. Complaints and Contact (APP 1)
    
    ### Privacy Officer Contact:
    **Email:** privacy@auxpery.com  
    **Response Time:** Within 30 days
    
    ### How to Make a Complaint:
    1. Email our Privacy Officer with details of your concern
    2. We will acknowledge receipt within 5 business days
    3. We will investigate and respond within 30 days
    4. If unsatisfied, you may escalate to OAIC (below)
    
    ### Australian Privacy Regulator:
    **Office of the Australian Information Commissioner (OAIC)**  
    Website: www.oaic.gov.au  
    Phone: 1300 363 992  
    Email: enquiries@oaic.gov.au
    
    You have the right to lodge a complaint with OAIC if you believe we have breached your privacy rights.
    
    ---
    
    ## 11. Data Protection Agreement
    
    For schools and organizations using Guide:
    - We can provide a Data Processing Agreement (DPA) upon request
    - DPA outlines our responsibilities as a data processor
    - Contact privacy@auxpery.com for DPA template
    
    ---
    
    ## 12. Questions?
    
    If you have questions about this Privacy Policy or how we handle your data:
    
    📧 **Email:** privacy@auxpery.com  
    🌐 **Website:** [Contact form available in app]  
    📞 **Support:** Available to registered users
    
    ---
    
    *This Privacy Policy is designed to be transparent, accessible, and compliant with Australian Privacy Act 1988. We are committed to protecting your privacy and handling your data responsibly.*
    
    **© 2025 Auxpery - Gentle Technology for Thoughtful Teaching**
    """)
    
    # Add quick actions
    st.markdown("---")
    st.markdown("### 🔐 Privacy Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Request My Data", use_container_width=True):
            st.session_state.auth_mode = "data_access"
            st.rerun()
    
    with col2:
        if st.button("✏️ Update My Information", use_container_width=True):
            st.session_state.auth_mode = "account_settings"
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete My Account", use_container_width=True):
            st.session_state.auth_mode = "account_deletion"
            st.rerun()


def show_data_access_interface():
    """User data access interface (APP 12)"""
    st.markdown("### 📥 Access Your Data")
    st.markdown("*Request a copy of all personal information we hold about you*")
    
    user_id = st.session_state.get('user_id')
    is_student = st.session_state.get('is_student', False)
    
    st.info("Under the Australian Privacy Act 1988, you have the right to access your personal information. We will provide your data in a commonly used electronic format within 30 days.")
    
    if st.button("📥 Generate My Data Export", type="primary", use_container_width=True):
        with st.spinner("Gathering your data..."):
            db = get_db()
            if db and user_id:
                try:
                    import json
                    from datetime import datetime
                    
                    export_data = {
                        "export_date": datetime.now().isoformat(),
                        "user_type": "student" if is_student else "educator",
                        "account_info": {},
                        "conversation_history": [],
                        "activities": [],
                        "saved_content": []
                    }
                    
                    if is_student:
                        # Export student data
                        from database import Student, StudentActivity, ConversationHistory
                        student = db.query(Student).filter(Student.id == user_id).first()
                        
                        if student:
                            export_data["account_info"] = {
                                "username": student.username,
                                "full_name": student.full_name,
                                "age_group": student.age_group,
                                "created_at": student.created_at.isoformat(),
                                "is_active": student.is_active
                            }
                            
                            # Get activities
                            activities = db.query(StudentActivity).filter(
                                StudentActivity.student_id == user_id
                            ).all()
                            
                            export_data["activities"] = [
                                {
                                    "type": a.activity_type,
                                    "prompt": a.prompt_text,
                                    "response": a.response_text,
                                    "date": a.created_at.isoformat()
                                } for a in activities
                            ]
                            
                            # Get conversations
                            conversations = db.query(ConversationHistory).filter(
                                ConversationHistory.student_id == user_id
                            ).all()
                            
                            export_data["conversation_history"] = [
                                {
                                    "role": c.role,
                                    "content": c.content,
                                    "date": c.created_at.isoformat()
                                } for c in conversations
                            ]
                    
                    else:
                        # Export educator data
                        from database import User, EducatorAnalytics, ConversationHistory, LessonPlan
                        user = db.query(User).filter(User.id == user_id).first()
                        
                        if user:
                            export_data["account_info"] = {
                                "email": user.email,
                                "full_name": user.full_name,
                                "user_type": user.user_type,
                                "created_at": user.created_at.isoformat(),
                                "is_active": user.is_active
                            }
                            
                            # Get analytics
                            analytics = db.query(EducatorAnalytics).filter(
                                EducatorAnalytics.user_id == user_id
                            ).all()
                            
                            export_data["analytics"] = [
                                {
                                    "interface": a.interface_type,
                                    "subject": a.subject,
                                    "year_level": a.year_level,
                                    "prompt": a.prompt_text,
                                    "tokens": a.tokens_used,
                                    "date": a.created_at.isoformat()
                                } for a in analytics
                            ]
                            
                            # Get lesson plans
                            plans = db.query(LessonPlan).filter(
                                LessonPlan.creator_id == user_id
                            ).all()
                            
                            export_data["saved_content"] = [
                                {
                                    "type": "lesson_plan",
                                    "title": p.title,
                                    "content": p.content,
                                    "created": p.created_at.isoformat()
                                } for p in plans
                            ]
                    
                    # Create downloadable JSON
                    json_data = json.dumps(export_data, indent=2)
                    
                    st.success("✅ Data export ready!")
                    st.download_button(
                        label="📥 Download My Data (JSON)",
                        data=json_data,
                        file_name=f"guide_data_export_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                    
                except Exception as e:
                    st.error(f"Error generating export: {str(e)}")
                finally:
                    db.close()
            else:
                st.error("Unable to access database")


def show_account_deletion_interface():
    """Account deletion interface (APP 12/13)"""
    st.markdown("### 🗑️ Delete My Account")
    st.markdown("*Permanently remove your account and all associated data*")
    
    user_id = st.session_state.get('user_id')
    is_student = st.session_state.get('is_student', False)
    user_name = st.session_state.get('user_name', '')
    
    st.error("⚠️ **Warning: This action cannot be undone!**")
    
    st.markdown("""
    ### What will be deleted:
    - Your account credentials
    - All conversation history
    - All saved lesson plans, stories, and notes (educators)
    - All learning activities and progress (students)
    - All uploaded files and documents
    - All analytics and usage data
    
    ### What happens next:
    - Deletion takes effect within 7 days
    - You will receive confirmation via email (educators)
    - All data is permanently removed from our systems
    - This action cannot be reversed
    """)
    
    st.markdown("---")
    
    st.markdown("### Confirm Deletion")
    
    confirm_text = st.text_input(
        f"Type your {'username' if is_student else 'full name'} to confirm:",
        help=f"Enter exactly: {user_name}"
    )
    
    reason = st.text_area(
        "Reason for deletion (optional):",
        placeholder="Help us improve by sharing why you're leaving...",
        help="This is optional but helps us understand user needs"
    )
    
    if st.button("🗑️ Permanently Delete My Account", type="primary", use_container_width=True):
        if confirm_text == user_name:
            db = get_db()
            if db and user_id:
                try:
                    if is_student:
                        from database import delete_student
                        if delete_student(db, user_id):
                            # Log reason if provided
                            if reason:
                                # Could save to a deletion_log table for analytics
                                pass
                            
                            st.success("✅ Your account has been permanently deleted.")
                            st.info("You will be logged out in 3 seconds...")
                            
                            # Clear session
                            import time
                            time.sleep(3)
                            for key in list(st.session_state.keys()):
                                del st.session_state[key]
                            st.rerun()
                        else:
                            st.error("Failed to delete account. Please contact support.")
                    else:
                        from database import delete_educator
                        # Comprehensive deletion for educators with all related data
                        success, error_msg = delete_educator(db, user_id)
                        
                        if success:
                            st.success("✅ Your account has been permanently deleted.")
                            st.info("You will be logged out in 3 seconds...")
                            
                            import time
                            time.sleep(3)
                            for key in list(st.session_state.keys()):
                                del st.session_state[key]
                            st.rerun()
                        else:
                            st.error(f"❌ {error_msg}")
                            if "active student" in error_msg.lower():
                                st.info("💡 **Tip:** Go to 'Create Student Account' to view and delete your students first.")
                
                except Exception as e:
                    st.error(f"Error deleting account: {str(e)}")
                finally:
                    db.close()
        else:
            st.error(f"Confirmation text does not match. Please type exactly: {user_name}")


def show_pd_expert_interface():
    """Professional Development Expert Mode - Restricted to authorized educators"""
    scroll_to_top()
    
    user_email = st.session_state.get('user_email', '')
    
    # Access control - restrict to authorized email
    if user_email != "guideaichat@gmail.com":
        st.error("🔒 Access Denied")
        st.info("This Professional Development Expert Mode is restricted to authorized accounts only.")
        return
    
    # Header with special badge
    st.markdown("### 🧭 Professional Development Expert Mode")
    st.markdown("*Evidence-based PD coaching with self-learning memory and Montessori expertise*")
    
    st.markdown("---")
    
    # Info box
    with st.expander("ℹ️ About PD Expert Mode", expanded=False):
        st.markdown("""
        **This specialized mode provides:**
        
        - 📚 **Evidence-based guidance** from frameworks like Harvard Instructional Moves, Edutopia, and adult learning theory
        - 🧠 **Self-learning memory** that adapts to your professional development focus areas
        - 🎯 **Montessori-aligned** coaching with deep understanding of Prepared Adult principles
        - 🔄 **Contextual responses** based on keywords like "adult learning", "instructional coaching", "workshop design"
        
        **Structured responses include:**
        1️⃣ Summary of your question  
        2️⃣ Evidence-based insight or framework  
        3️⃣ Suggested approach or structure  
        4️⃣ Montessori connection  
        5️⃣ Next steps or reflective prompt
        """)
    
    # Initialize PD messages in session state
    if 'pd_messages' not in st.session_state:
        st.session_state.pd_messages = []
    
    # Display conversation history with avatar
    for msg in st.session_state.pd_messages:
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.markdown(msg['content'])
        else:
            with st.chat_message("assistant", avatar="assets/montessori-avatar.png"):
                st.markdown(f"**🧭 PD Expert**")
                st.markdown(msg['content'])
    
    # Chat input
    if user_prompt := st.chat_input("Ask your professional development question...", key="pd_expert_input"):
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_prompt)
        
        st.session_state.pd_messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Call PD Expert API (Python implementation)
        with st.chat_message("assistant", avatar="assets/montessori-avatar.png"):
            st.markdown("**🧭 PD Expert**")
            
            with st.spinner("Consulting expertise and memory... (this may take 30-60 seconds for comprehensive responses)"):
                from utils import call_pd_expert
                from openai import OpenAI
                import os
                
                try:
                    # Initialize OpenAI client
                    openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                    
                    # Call PD Expert function
                    result = call_pd_expert(user_email, user_prompt, openai_client)
                    
                    if result.get('success'):
                        expert_response = result.get('output', '')
                        st.markdown(expert_response)
                        
                        st.session_state.pd_messages.append({
                            "role": "assistant",
                            "content": expert_response
                        })
                        
                        # Scroll to beginning of new response
                        scroll_to_latest_response()
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        if 'Access denied' in error_msg:
                            st.error("🔒 Access denied. This feature is restricted.")
                        else:
                            st.error(f"Error: {error_msg}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Clear conversation button
    if st.session_state.pd_messages:
        st.markdown("---")
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.pd_messages = []
            st.rerun()
    
    # Add scroll to top button
    add_scroll_to_top_button()
