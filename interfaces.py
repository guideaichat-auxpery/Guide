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
            f"Create an independent research project with community connections for {planning_type}",
            f"Design a practical application of mathematical concepts for {planning_type}",
            f"Plan a collaborative inquiry into Australian history for {planning_type}",
            f"Develop critical thinking through scientific investigation for {planning_type}"
        ]
    else:  # 12-15
        templates = [
            f"Create a social enterprise project connecting community service for {planning_type}",
            f"Design a real-world problem-solving investigation for {planning_type}",
            f"Plan a peer mentoring program with leadership development for {planning_type}",
            f"Develop a sustainable living project with environmental focus for {planning_type}"
        ]
    
    for template in templates:
        if st.button(f"📋 {template}", key=f"template_{template[:20]}", use_container_width=True):
            enhanced_prompt = f"""
            Please create a comprehensive {planning_type} for {age_group} students with the following requirements:
            
            {template}
            
            ESSENTIAL REQUIREMENTS:
            1. Include specific Australian Curriculum V.9 content descriptor codes and achievement standards
            2. Ensure strong Montessori pedagogical foundation with rationale
            3. Provide materials list (both traditional Montessori and accessible alternatives)
            4. Include assessment strategies and observation points
            5. Add extension activities and differentiation options
            6. Consider mixed-age learning opportunities where appropriate
            7. Include family engagement suggestions for home-school families
            
            Format the response with clear sections and practical implementation guidance.
            """
            
            st.session_state.planning_messages.append({"role": "user", "content": enhanced_prompt})
            
            with st.spinner("Creating comprehensive educational plan..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.planning_messages, max_tokens)
                if response:
                    st.markdown("### 📚 Educational Planning Guidance")
                    st.markdown(response)
                    st.session_state.planning_messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble generating the educational plan. Please try again.")
    
    # Handle uploaded documents
    if uploaded_files:
        st.markdown("#### 📋 Document Analysis")
        for uploaded_file in uploaded_files:
            st.info(f"📄 Analyzing: {uploaded_file.name}")
            
            # Read file content based on type
            file_content = ""
            try:
                if uploaded_file.type == "text/plain":
                    file_content = str(uploaded_file.read(), "utf-8")
                elif uploaded_file.type in ["image/jpeg", "image/jpg", "image/png"]:
                    # Read image data once
                    image_data = uploaded_file.read()
                    st.image(image_data, caption=f"Uploaded: {uploaded_file.name}", width=300)
                    # Extract text from image using OCR
                    try:
                        # Check if tesseract is available
                        import shutil
                        if not shutil.which('tesseract'):
                            file_content = f"[Image uploaded: {uploaded_file.name} - OCR not available in this environment]"
                        else:
                            image_buffer = io.BytesIO(image_data)
                            image = Image.open(image_buffer)
                            extracted_text = pytesseract.image_to_string(image)
                            file_content = f"Image content extracted via OCR:\n{extracted_text[:2000]}"
                            if len(extracted_text) > 2000:
                                file_content += "...[truncated]"
                    except Exception as e:
                        file_content = f"[Image uploaded: {uploaded_file.name} - OCR extraction failed: {str(e)}]"
                elif uploaded_file.type == "application/pdf":
                    # Extract text from PDF
                    try:
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        pdf_text = ""
                        for page in pdf_reader.pages:
                            pdf_text += page.extract_text() + "\n"
                        file_content = f"PDF content:\n{pdf_text[:2000]}"
                        if len(pdf_text) > 2000:
                            file_content += "...[truncated]"
                    except Exception as e:
                        file_content = f"[PDF uploaded: {uploaded_file.name} - text extraction failed: {str(e)}]"
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    # Extract text from DOCX
                    try:
                        doc = Document(uploaded_file)
                        doc_text = ""
                        for paragraph in doc.paragraphs:
                            doc_text += paragraph.text + "\n"
                        file_content = f"DOCX content:\n{doc_text[:2000]}"
                        if len(doc_text) > 2000:
                            file_content += "...[truncated]"
                    except Exception as e:
                        file_content = f"[DOCX uploaded: {uploaded_file.name} - text extraction failed: {str(e)}]"
                else:
                    file_content = f"[Document uploaded: {uploaded_file.name} - {uploaded_file.type}]"
            except Exception as e:
                file_content = f"[Error reading {uploaded_file.name}: {str(e)}]"
            
            # Create analysis prompt
            analysis_prompt = f"""
            Please analyze this uploaded document for a {age_group} age group and provide feedback:
            
            Document: {uploaded_file.name}
            Content: {file_content[:1000]}...
            
            Please provide:
            1. **Montessori Alignment**: How well this aligns with Montessori principles for {age_group}
            2. **Australian Curriculum V.9**: Relevant AC codes and standards addressed
            3. **Developmental Appropriateness**: Suitability for {age_group} learners
            4. **Suggestions for Improvement**: Specific recommendations
            5. **Extension Activities**: Follow-up learning opportunities
            """
            
            if st.button(f"🔍 Analyze {uploaded_file.name}", key=f"analyze_{uploaded_file.name}"):
                st.session_state.planning_messages.append({"role": "user", "content": analysis_prompt})
                
                with st.spinner(f"Analyzing {uploaded_file.name}..."):
                    max_tokens = get_max_tokens_for_user_type('educator')
                    response = call_openai_api(st.session_state.planning_messages, max_tokens)
                    if response:
                        st.markdown("### 📋 Document Analysis Results")
                        st.markdown(response)
                        st.session_state.planning_messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble analyzing the document. Please try again.")

    # Custom planning input chatbox
    st.markdown("#### 💬 Custom Educational Planning Request")
    st.markdown("*Describe your specific planning needs, ask questions, or request customized lesson plans*")
    
    if prompt := st.chat_input("Describe your educational planning needs, upload documents for feedback, or ask specific questions..."):
        # Create enhanced prompt based on uploaded files
        file_context = ""
        if uploaded_files:
            file_names = [f.name for f in uploaded_files]
            file_context = f"\n\nNote: I have uploaded the following documents for context: {', '.join(file_names)}"
        
        enhanced_prompt = f"""
        Educational Planning Request for {age_group} students ({planning_type}):
        {prompt}{file_context}
        
        Please ensure your response includes:
        1. Relevant Australian Curriculum V.9 codes and achievement standards
        2. Montessori pedagogical rationale
        3. Practical implementation steps
        4. Assessment and observation strategies
        5. Materials and resources needed
        6. Extension and differentiation options
        7. If documents were uploaded, reference them in your response
        """
        
        st.session_state.planning_messages.append({"role": "user", "content": enhanced_prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Creating personalized educational guidance..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.planning_messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.planning_messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def show_companion_interface():
    """Companion interface for general Montessori guidance (secondary feature)"""
    # Ensure companion messages are initialized
    if 'companion_messages' not in st.session_state:
        st.session_state.companion_messages = []
        
    st.markdown("### 🗨️ Montessori Companion")
    st.markdown("*Explore Montessori philosophy and get guidance on educational approaches*")
    
    # Display chat history
    for message in st.session_state.companion_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Quick companion topics
    st.markdown("#### Explore Montessori Concepts:")
    companion_topics = [
        "How does cosmic education connect all learning areas?",
        "What role does the prepared environment play in different age groups?",
        "How do I observe and follow the child effectively?",
        "What are the key differences between early years, primary, and adolescent approaches?",
        "How can I create independence-building activities?",
        "What is the importance of mixed-age communities?"
    ]
    
    for topic in companion_topics:
        if st.button(f"💭 {topic}", key=f"companion_{topic[:20]}", use_container_width=True):
            st.session_state.companion_messages.append({"role": "user", "content": topic})
            
            with st.spinner("Exploring Montessori philosophy..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.companion_messages, max_tokens)
                if response:
                    st.markdown("### 🗨️ Montessori Insight")
                    st.markdown(response)
                    st.session_state.companion_messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble generating guidance. Please try again.")
    
    # Chat input for custom questions
    if prompt := st.chat_input("Ask about Montessori philosophy, approaches, or implementation..."):
        st.session_state.companion_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Providing Montessori guidance..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.companion_messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.companion_messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def log_student_interaction(activity_type, prompt_text, response_text=None, session_id=None):
    """Log student activity to database if available"""
    if not database_available or not st.session_state.get('is_student'):
        return
    
    try:
        db = get_db()
        if db and st.session_state.get('user_id'):
            log_student_activity(
                db=db,
                student_id=st.session_state.user_id,
                activity_type=activity_type,
                prompt_text=prompt_text,
                response_text=response_text,
                session_id=session_id
            )
            db.close()
    except Exception as e:
        # Silent logging failure - don't disrupt student experience
        print(f"Failed to log student activity: {str(e)}")

def show_student_interface():
    """Student interface for all age groups with age-appropriate guidance"""
    # Ensure messages are initialized
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Initialize session ID for tracking related interactions
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = str(uuid.uuid4())
        
    age_group = st.session_state.get('age_group', '6-9')
    
    # Handle legacy age group values
    legacy_mapping = {
        "early_years": "3-6",
        "primary": "6-9", 
        "adolescent": "12-15"
    }
    if age_group in legacy_mapping:
        age_group = legacy_mapping[age_group]
    
    age_display = {
        "3-6": "Early Years (3-6)",
        "6-9": "Lower Primary (6-9)", 
        "9-12": "Upper Primary (9-12)",
        "12-15": "Adolescent (12-15)"
    }.get(age_group, f"Age Group {age_group}")
    
    st.markdown(f"### 👨‍🎓 Student Learning Support ({age_display})")
    st.markdown("*Discover the joy of self-directed learning with Montessori principles*")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Age-appropriate learning topics
    st.markdown("#### Explore Learning:")
    
    if age_group == "3-6":
        topics = [
            "How can I help with practical life activities at home?",
            "Why do we use special learning materials?",
            "How can I be more independent?",
            "What makes learning fun and interesting?",
            "How can I help my friends learn too?"
        ]
    elif age_group == "6-9":
        topics = [
            "How are all subjects connected to the cosmic story?",
            "Why is hands-on learning so important?",
            "How can I research topics that interest me?",
            "What makes a good learning environment?",
            "How can I help younger students?"
        ]
    elif age_group == "9-12":
        topics = [
            "How can I do independent research on topics I'm interested in?",
            "Why is collaboration important in learning?",
            "How do I connect my learning to the real world?",
            "What are effective ways to help younger students?",
            "How can I take responsibility for my own learning?"
        ]
    else:  # 12-15
        topics = [
            "How can my learning connect to real-world problems?",
            "What role can I play in my community?",
            "How do I develop leadership and collaboration skills?",
            "How can I prepare for my future while learning?",
            "What are meaningful ways to contribute to society?"
        ]
    
    for topic in topics:
        if st.button(f"🌟 {topic}", key=f"student_{topic[:15]}", use_container_width=True):
            age_appropriate_prompt = f"""
            Question from a {age_group} student: {topic}
            
            Please provide an age-appropriate response that:
            1. Respects the student's natural curiosity and development
            2. Encourages self-direction and independence
            3. Connects to Montessori principles appropriate for their age
            4. Suggests practical ways they can explore this further
            5. Uses language and examples suitable for {age_group} learners
            """
            
            # Log the prompt
            log_student_interaction(
                activity_type="prompt",
                prompt_text=topic,
                session_id=st.session_state.current_session_id
            )
            
            st.session_state.messages.append({"role": "user", "content": age_appropriate_prompt})
            
            with st.spinner("Exploring your question..."):
                max_tokens = get_max_tokens_for_user_type('student')
                response = call_openai_api(st.session_state.planning_messages, max_tokens)
                if response:
                    st.markdown("### 🌟 Learning Discovery")
                    st.markdown(response)
                    st.session_state.planning_messages.append({"role": "assistant", "content": response})
                    
                    # Log the response
                    log_student_interaction(
                        activity_type="response",
                        prompt_text=topic,
                        response_text=response,
                        session_id=st.session_state.current_session_id
                    )
                else:
                    st.error("I'm having trouble answering. Please try again.")
    
    # Chat input for custom questions
    if prompt := st.chat_input("Ask me about learning, interests, or how things work..."):
        age_appropriate_prompt = f"""
        Question from a {age_group} student: {prompt}
        
        Please provide an age-appropriate response that encourages exploration, 
        independence, and follows Montessori principles for {age_group} learners.
        """
        
        # Log the prompt
        log_student_interaction(
            activity_type="prompt",
            prompt_text=prompt,
            session_id=st.session_state.current_session_id
        )
        
        st.session_state.messages.append({"role": "user", "content": age_appropriate_prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking about your question..."):
                max_tokens = get_max_tokens_for_user_type('student')
                response = call_openai_api(st.session_state.planning_messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.planning_messages.append({"role": "assistant", "content": response})
                    
                    # Log the response
                    log_student_interaction(
                        activity_type="response",
                        prompt_text=prompt,
                        response_text=response,
                        session_id=st.session_state.current_session_id
                    )
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def show_clear_conversation_button():
    """Reusable clear conversation button"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            # Log the clear action for students
            if st.session_state.get('is_student'):
                log_student_interaction(
                    activity_type="clear_conversation",
                    prompt_text="Student cleared conversation",
                    session_id=st.session_state.get('current_session_id')
                )
                # Start new session
                st.session_state.current_session_id = str(uuid.uuid4())
            
            st.session_state.messages = []
            st.rerun()

def show_student_dashboard_interface():
    """Educator interface to view student activities and engagement"""
    st.markdown("### 📊 Student Activity Dashboard")
    st.markdown("*Monitor student engagement and learning patterns*")
    
    if not database_available:
        st.warning("Student dashboard is not available without database connection.")
        st.info("This feature requires database access to view student activities.")
        return
    
    # Get educator's accessible students
    db = get_db()
    if not db:
        st.error("Database connection error. Cannot load student data.")
        return
    
    try:
        from database import get_educator_accessible_students, get_student_activities
        
        educator_id = st.session_state.get('user_id')
        if not educator_id:
            st.error("User session error. Please log in again.")
            return
        
        students = get_educator_accessible_students(db, educator_id)
        
        if not students:
            st.info("No students found. Create student accounts to begin monitoring their activities.")
            return
        
        # Student selector
        st.markdown("#### Select Student")
        selected_student = st.selectbox(
            "Choose a student to view their activities:",
            students,
            format_func=lambda s: f"{s.full_name} (@{s.username}) - {s.age_group or 'No age group'}"
        )
        
        if selected_student:
            # Check if current educator is primary educator for access management
            is_primary_educator = (selected_student.educator_id == educator_id)
            
            # Tabs for activities and access management
            tab1, tab2 = st.tabs(["📊 Student Activities", "🔑 Access Management"])
            
            with tab1:
                st.markdown(f"### Activities for {selected_student.full_name}")
                
                # Get student activities
                activities = get_student_activities(db, selected_student.id, limit=50)
                
                if not activities:
                    st.info(f"{selected_student.full_name} hasn't started any learning activities yet.")
                else:
                    # Activity summary
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        total_prompts = len([a for a in activities if a.activity_type == "prompt"])
                        st.metric("Total Questions Asked", total_prompts)
                    
                    with col2:
                        total_responses = len([a for a in activities if a.activity_type == "response"])
                        st.metric("AI Responses Received", total_responses)
                    
                    with col3:
                        sessions = len(set([a.session_id for a in activities if a.session_id]))
                        st.metric("Learning Sessions", sessions)
                    
                    # Activity timeline
                    st.markdown("#### Recent Activity Timeline")
                    
                    for activity in activities:
                        with st.expander(
                            f"📝 {activity.activity_type.replace('_', ' ').title()} - {activity.created_at.strftime('%Y-%m-%d %H:%M')}",
                            expanded=False
                        ):
                            if activity.activity_type == "prompt":
                                st.markdown("**Student Question:**")
                                st.info(activity.prompt_text)
                                
                            elif activity.activity_type == "response":
                                st.markdown("**Student Question:**")
                                st.info(activity.prompt_text)
                                st.markdown("**AI Response:**")
                                st.success(activity.response_text)
                                
                            elif activity.activity_type == "clear_conversation":
                                st.markdown("🗑️ Student cleared conversation and started a new session")
                            
                            # Show session info if available
                            if activity.session_id:
                                st.caption(f"Session ID: {activity.session_id}")
            
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