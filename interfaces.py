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
    
    # Age group selector with year level display
    from utils import map_age_to_year_levels
    
    age_group = st.selectbox(
        "Select Age Group:",
        ["3-6", "6-9", "9-12", "12-15"],
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
    
    # Curriculum Alignment Review Button (appears when documents uploaded and planning type selected)
    if uploaded_files and planning_type == "curriculum_alignment":
        st.markdown("---")
        st.markdown("### 🔍 AI-Powered Curriculum Alignment Review")
        st.markdown("*Sophisticated AC V9 and Montessori National Curriculum alignment analysis with keyword recognition*")
        
        if st.button("🚀 Start Curriculum Alignment Review", type="primary", use_container_width=True):
            # Process uploaded documents
            with st.spinner("📚 Analyzing uploaded documents for curriculum alignment..."):
                review_results = perform_curriculum_alignment_review(
                    uploaded_files=uploaded_files,
                    age_group=age_group,
                    subjects=subjects
                )
                
                # Display review results
                if review_results:
                    st.session_state.planning_messages.append({
                        "role": "assistant",
                        "content": review_results
                    })
                    st.rerun()
        
        st.markdown("---")
    
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
        
        # Process uploaded documents with enhanced structure
        document_context = ""
        if uploaded_files:
            st.info(f"📎 Processing {len(uploaded_files)} uploaded document(s)...")
            for file in uploaded_files:
                file_content = extract_file_content(file)
                if file_content:
                    # Add structured metadata and chunking for better AI reference
                    lines = file_content.split('\n')
                    total_lines = len(lines)
                    document_context += f"""
═══════════════════════════════════════════════════════════════════
📄 UPLOADED CURRICULUM DOCUMENT: {file.name}
Total content: {total_lines} lines
═══════════════════════════════════════════════════════════════════

{file_content}

═══════════════════════════════════════════════════════════════════
END OF DOCUMENT: {file.name}
YOU MUST REFERENCE this document in your response with specific quotes, AC V9 codes, and page/section citations
═══════════════════════════════════════════════════════════════════
"""
        
        # Load Montessori literature references
        from utils import load_montessori_own_handbook, load_the_absorbent_mind, load_the_montessori_method, map_age_to_year_levels
        montessori_refs = ""
        
        handbook = load_montessori_own_handbook()
        if handbook and len(handbook) > 100:
            montessori_refs += f"\n\nMONTESSORI REFERENCE - Dr. Montessori's Own Handbook:\n{handbook[:1000]}...\n"
        
        absorbent = load_the_absorbent_mind()
        if absorbent and len(absorbent) > 100:
            montessori_refs += f"\n\nMONTESSORI REFERENCE - The Absorbent Mind:\n{absorbent[:1000]}...\n"
        
        method = load_the_montessori_method()
        if method and len(method) > 100:
            montessori_refs += f"\n\nMONTESSORI REFERENCE - The Montessori Method:\n{method[:1000]}...\n"
        
        # Get year levels for age group
        year_levels = map_age_to_year_levels(age_group)
        year_levels_str = ", ".join(year_levels) if year_levels else "General"
        
        # Enhanced system prompt with document emphasis
        system_prompt = f"""You are GuideChat, an advanced AI planning assistant for educators.
Your goal is to help teachers design open-ended, inquiry-driven, and student-centered learning experiences.

CRITICAL: You MUST draw from ALL provided reference materials in your response:
1. **UPLOADED CURRICULUM DOCUMENTS** - Reference specific content descriptors, codes, and guidelines from uploaded Australian Curriculum V9 documents
2. **MONTESSORI LITERATURE** - Apply principles from the provided Montessori references
3. **AGE-APPROPRIATE ALIGNMENT** - Tailor ALL suggestions specifically for {age_group} year olds using developmentally appropriate language, materials, and concepts

Current Planning Context:
- Age Group: {age_group} → Year Levels: {year_levels_str} (THIS IS MANDATORY - all responses must align with these specific Australian Curriculum year levels)
- Planning Type: {planning_type}
- Subject Area(s): {', '.join(subjects) if subjects else 'General/Cross-curriculum'}

Base all guidance on:
- The Montessori National Curriculum of Australia
- Maria Montessori's philosophy (see references below)
- The Australian Curriculum Version 9 (use uploaded documents as primary reference)

When designing learning experiences:
1. Focus on **big questions**, provocations, and lines of inquiry
2. Encourage **student exploration**, **choice**, and **reflection**
3. Present **conceptual frameworks** and **open challenges**
4. Offer **teacher prompts** for observation and scaffolding
5. Use age-appropriate, curiosity-oriented language for {age_group} year olds
6. **CITE SPECIFIC AC V9 CODES** from uploaded curriculum documents

Response Structure (MANDATORY):
1. **Big Question** — Central driving inquiry for {age_group} learners
2. **Possible Lines of Inquiry** — Multiple pathways appropriate for {age_group}
3. **Provocations & Environment Setup** — Materials and prompts suitable for {age_group}
4. **Student-Led Exploration Ideas** — Open activities for {age_group} developmental stage
5. **Observation Prompts for Educators** — What to notice with {age_group} learners
6. **Curriculum Connections** — Specific AC V9 codes from uploaded documents + Montessori principles

Tone: Reflective, curious, facilitative. Always reference uploaded documents and Montessori literature.{montessori_refs}"""
        
        # Prepare comprehensive prompt with document context
        full_prompt = prompt
        if document_context:
            full_prompt = f"""EDUCATOR REQUEST: {prompt}

UPLOADED CURRICULUM DOCUMENTS TO REFERENCE:
{document_context}

YOU MUST cite specific content from these uploaded documents in your response, including AC V9 codes and descriptors."""
        
        # Update the last message with enhanced context
        st.session_state.planning_messages[-1] = {"role": "user", "content": full_prompt}
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.planning_messages[-1:],
                    system_prompt=system_prompt,
                    is_student=False,
                    age_group=age_group,
                    subjects=subjects if subjects else None  # Pass all selected subjects
                )
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.planning_messages.append({"role": "assistant", "content": response})

def perform_curriculum_alignment_review(uploaded_files, age_group, subjects):
    """
    Perform sophisticated curriculum alignment review of uploaded documents
    using AC V9 and MNC with intelligent keyword recognition and year level inference
    """
    from utils import extract_curriculum_keywords, get_primary_year_level, infer_year_level_from_keywords
    from utils import fetch_curriculum_context, call_openai_api
    
    # Extract content from all uploaded files
    document_content = ""
    for file in uploaded_files:
        file_content = extract_file_content(file)
        if file_content:
            document_content += f"""
═══════════════════════════════════════════════════════════════════
📄 DOCUMENT: {file.name}
═══════════════════════════════════════════════════════════════════
{file_content}

═══════════════════════════════════════════════════════════════════
"""
    
    if not document_content:
        return "⚠️ Unable to extract content from uploaded documents. Please ensure files are readable."
    
    # Detect curriculum keywords from document content
    all_keywords = []
    subject_keywords_map = {}
    
    if subjects:
        for subject in subjects:
            found_keywords = extract_curriculum_keywords(subject, document_content)
            if found_keywords:
                all_keywords.extend(found_keywords)
                subject_keywords_map[subject] = found_keywords
    
    # Infer year level from detected keywords
    inferred_year_level = None
    if all_keywords and age_group:
        inferred_year_level = infer_year_level_from_keywords(all_keywords, age_group)
    
    # Get primary year level (with keyword inference)
    target_year_level = get_primary_year_level(age_group, detected_keywords=all_keywords if all_keywords else None)
    
    # Build keyword context summary
    keyword_summary = ""
    if all_keywords:
        unique_keywords = list(set(all_keywords))
        keyword_summary = f"""
🎯 **DETECTED CURRICULUM KEYWORDS**: {', '.join(unique_keywords[:15])}
{'...' if len(unique_keywords) > 15 else ''}

📚 **SUBJECT-SPECIFIC ALIGNMENT**:
"""
        for subject, keywords in subject_keywords_map.items():
            keyword_summary += f"- **{subject}**: {', '.join(keywords[:5])}\n"
    
    # Add year level inference info
    year_level_info = ""
    if inferred_year_level:
        year_level_info = f"\n🎓 **INFERRED YEAR LEVEL**: {target_year_level} (based on detected AC V9 curriculum topics)\n"
    elif target_year_level:
        year_level_info = f"\n🎓 **TARGET YEAR LEVEL**: {target_year_level} (from age group: {age_group})\n"
    
    # Fetch curriculum context for alignment
    curriculum_contexts = []
    if subjects and target_year_level:
        for subject in subjects:
            context = fetch_curriculum_context(subject, target_year_level, curriculum_type="Blended")
            if context:
                curriculum_contexts.append(f"--- {subject} ({target_year_level}) ---\n{context}")
    
    curriculum_reference = "\n\n".join(curriculum_contexts) if curriculum_contexts else ""
    
    # Build comprehensive review prompt
    review_prompt = f"""You are an expert curriculum alignment reviewer specializing in Australian Curriculum V9 and Montessori National Curriculum.

Conduct a COMPREHENSIVE CURRICULUM ALIGNMENT REVIEW of the uploaded document(s).

{keyword_summary}
{year_level_info}

UPLOADED DOCUMENT(S):
{document_content}

RELEVANT CURRICULUM CONTEXT:
{curriculum_reference}

⚠️ CRITICAL REQUIREMENTS:
1. **AC V9 VERSION ENFORCEMENT**: Use ONLY Australian Curriculum VERSION 9 codes (starting with "AC9", e.g., AC9HG9K03, AC9E7LA01)
2. **KEYWORD-BASED ALIGNMENT**: Reference the detected curriculum keywords above and explain how the document aligns (or doesn't align) with each
3. **YEAR LEVEL APPROPRIATENESS**: Assess whether content is pitched at the correct cognitive level for {target_year_level}
4. **MONTESSORI INTEGRATION**: Evaluate how well the document integrates Montessori principles (prepared environment, cosmic education, student agency)
5. **SPECIFIC CITATIONS**: Quote specific sections from the uploaded document to support your analysis

PROVIDE A STRUCTURED REVIEW WITH:

### 🎯 Curriculum Alignment Summary
- Overall AC V9 alignment strength (Strong/Moderate/Weak)
- Overall MNC alignment strength (Strong/Moderate/Weak)
- Key strengths identified
- Critical gaps or misalignments

### 📊 Detailed AC V9 Analysis
For each detected subject ({', '.join(subjects) if subjects else 'N/A'}):
- Specific AC V9 content descriptors addressed (with codes)
- Direct quotes from document showing alignment
- Year level appropriateness for {target_year_level}
- General Capabilities integration (Critical & Creative Thinking, Ethical Understanding, etc.)

### 🌱 Montessori National Curriculum Analysis
- Cosmic Education connections (if applicable)
- Developmental plane alignment ({age_group} years)
- Student agency and choice provisions
- Prepared environment considerations
- Practical life/grace and courtesy integration

### 💡 Specific Recommendations for Improvement
Provide 3-5 actionable suggestions with:
- What to add/modify/remove
- Specific AC V9 codes to incorporate
- Montessori principles to strengthen
- Example implementations

### ⭐ Highlighted Strengths
Quote 2-3 specific sections from the document that demonstrate excellent curriculum alignment

Be thorough, specific, and reference actual content from the uploaded documents."""
    
    # Call OpenAI API with the review prompt
    review_messages = [{"role": "user", "content": review_prompt}]
    
    review_response = call_openai_api(
        messages=review_messages,
        is_student=False,
        age_group=age_group,
        subjects=subjects,
        curriculum_type="Blended",
        use_conversation_history=False
    )
    
    return review_response

def generate_student_work_feedback(uploaded_files, rubric_file, year_level, subjects, student_name):
    """
    Generate constructive feedback on student uploaded work using AI.
    References rubric if provided.
    """
    from utils import call_openai_api
    
    # Extract student work content
    work_content = ""
    for file in uploaded_files:
        file_content = extract_file_content(file)
        if file_content:
            work_content += f"""
═══════════════════════════════════════════════════════════════════
📄 STUDENT WORK FILE: {file.name}
═══════════════════════════════════════════════════════════════════
{file_content}

"""
    
    if not work_content:
        return "⚠️ Unable to extract content from your uploaded files. Please try different files."
    
    # Extract rubric content if provided
    rubric_content = ""
    if rubric_file:
        rubric_text = extract_file_content(rubric_file)
        if rubric_text:
            rubric_content = f"""
═══════════════════════════════════════════════════════════════════
📋 ASSESSMENT RUBRIC/MARKING CRITERIA: {rubric_file.name}
═══════════════════════════════════════════════════════════════════
{rubric_text}

YOU MUST reference this rubric in your feedback, assessing the student's work against each criterion.
═══════════════════════════════════════════════════════════════════
"""
    
    # Build feedback prompt
    feedback_prompt = f"""You are a supportive Montessori educator providing constructive feedback on student work.

STUDENT: {student_name}
YEAR LEVEL: {year_level}
SUBJECTS: {', '.join(subjects) if subjects else 'General'}

{rubric_content}

STUDENT'S SUBMITTED WORK:
{work_content}

PROVIDE CONSTRUCTIVE FEEDBACK WITH:

### 🌟 Strengths
Identify 2-3 specific things the student did well. Quote directly from their work.

### 💡 Areas for Growth
Provide 2-3 specific, actionable suggestions for improvement:
- What to focus on next
- How to develop their thinking/skills further
- Questions to deepen understanding

{f'''### 📋 Rubric Assessment
For EACH criterion in the rubric:
- State the criterion
- Explain how the student's work meets/doesn't meet it (with specific examples)
- Provide guidance on how to better meet the criterion''' if rubric_content else ''}

### 🎯 Next Steps
Suggest 1-2 concrete actions the student can take to improve this work or build on these skills.

IMPORTANT GUIDELINES:
- Use age-appropriate language for {year_level}
- Be encouraging and growth-focused (Montessori approach)
- Provide specific examples from the student's work
- Ask guiding questions rather than giving all answers
- {f'MUST reference the uploaded rubric criteria' if rubric_content else 'Focus on learning process and skill development'}
- Avoid generic praise - be specific and meaningful
- Frame feedback as opportunities for growth, not deficiencies"""
    
    # Generate feedback using AI
    feedback_messages = [{"role": "user", "content": feedback_prompt}]
    
    feedback_response = call_openai_api(
        messages=feedback_messages,
        is_student=True,
        year_level=year_level,
        subjects=subjects,
        curriculum_type="Blended",
        use_conversation_history=False
    )
    
    return feedback_response

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
    """Enhanced Montessori companion interface with conversation history management and persistence"""
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
    
    # Manage conversation history (keep last 10 exchanges)
    st.session_state.companion_messages = manage_conversation_history(
        st.session_state.companion_messages, max_history=20
    )
    
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
        
        # Save user message to database
        if database_available and user_id:
            db = get_db()
            if db:
                try:
                    save_conversation_message(
                        db, st.session_state.companion_session_id, 'companion',
                        'user', prompt, user_id=user_id
                    )
                except Exception as e:
                    print(f"Error saving conversation: {str(e)}")
                finally:
                    db.close()
        
        # Get AI response with enhanced features
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = call_openai_api(
                    st.session_state.companion_messages,
                    is_student=False,
                    use_conversation_history=True
                )
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.companion_messages.append({"role": "assistant", "content": response})
        
        # Save assistant response and log analytics
        if database_available and user_id:
            db = get_db()
            if db:
                try:
                    # Save conversation
                    save_conversation_message(
                        db, st.session_state.companion_session_id, 'companion',
                        'assistant', response, user_id=user_id
                    )
                    # Log analytics
                    tokens_est = estimate_tokens(prompt + response)
                    log_educator_prompt(
                        db, user_id, 'companion', prompt, 
                        tokens_used=tokens_est
                    )
                except Exception as e:
                    print(f"Error saving conversation/analytics: {str(e)}")
                finally:
                    db.close()

def show_student_interface():
    """Enhanced student learning interface with curriculum context, conversation history, and persistence"""
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
    st.markdown("*Your Montessori Learning Companion - Ask questions, explore ideas, discover connections*")
    
    # Privacy Notice Banner
    st.warning("⚠️ **Privacy Notice:** Do NOT enter personal information (name, birthdate, home/school address, or details of real people). Keep all inputs anonymous.", icon="⚠️")
    
    # Enhanced learning context selector with age-appropriate subjects
    
    with st.expander("📚 Set Learning Context (Optional)", expanded=False):
        # Year level selector (Year 6-9)
        student_year_level = st.selectbox(
            "Your Year Level:",
            ["Year 6", "Year 7", "Year 8", "Year 9"],
            index=0,
            key="student_year_selector"
        )
        
        # Determine subject options based on year level
        if student_year_level == "Year 6":
            # Year 6: Use HASS
            subject_options = ["English", "Mathematics", "Science", "HASS (Humanities and Social Sciences)", 
                              "Design and Technologies", "Digital Technologies", "The Arts", 
                              "Health and Physical Education", "Languages"]
        else:  # Years 7-9
            # Years 7-9: Use separate humanities subjects
            subject_options = ["English", "Mathematics", "Science", "History", "Geography", 
                              "Business and Economics", "Civics and Citizenship",
                              "Design and Technologies", "Digital Technologies", "The Arts", 
                              "Health and Physical Education", "Languages"]
        
        # Multi-subject selector
        student_subjects = st.multiselect(
            "Subject(s) you're learning about:",
            subject_options,
            key="student_subjects",
            help="Select one or more subjects to get curriculum-aligned guidance"
        )
    
    # File upload section for student work
    st.markdown("#### 📄 Upload Your Work for Help (Optional)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        student_uploaded_files = st.file_uploader(
            "Upload your work (homework, assignments, etc.)",
            accept_multiple_files=True,
            type=['txt', 'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'],
            key="student_file_uploader"
        )
    
    with col2:
        rubric_file = st.file_uploader(
            "Upload rubric/marking criteria (optional)",
            accept_multiple_files=False,
            type=['txt', 'pdf', 'docx', 'doc'],
            key="student_rubric_uploader"
        )
    
    # Show review button when work is uploaded
    if student_uploaded_files:
        st.markdown("---")
        if st.button("🎯 Review for Constructive Feedback", type="primary", use_container_width=True):
            with st.spinner("📚 Analyzing your work and preparing feedback..."):
                feedback = generate_student_work_feedback(
                    uploaded_files=student_uploaded_files,
                    rubric_file=rubric_file,
                    year_level=st.session_state.get('student_year_selector', 'Year 6'),
                    subjects=st.session_state.get('student_subjects', []),
                    student_name=student_name
                )
                
                # Display feedback
                if feedback:
                    st.session_state.student_messages.append({
                        "role": "assistant",
                        "content": feedback
                    })
                    st.rerun()
        st.markdown("---")
    
    # Manage conversation history (keep last 10 exchanges)
    st.session_state.student_messages = manage_conversation_history(
        st.session_state.student_messages, max_history=20
    )
    
    # Display chat history with avatars
    # Try to use custom Montessori avatar if available, otherwise use emoji
    import os
    ai_avatar = "assets/montessori-avatar.png" if os.path.exists("assets/montessori-avatar.png") else "🤖"
    
    for message in st.session_state.student_messages:
        avatar = ai_avatar if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to learn about today?"):
        # Process uploaded files if any
        document_context = ""
        if student_uploaded_files:
            st.info(f"📎 Reviewing {len(student_uploaded_files)} file(s) you uploaded...")
            for file in student_uploaded_files:
                file_content = extract_file_content(file)
                if file_content:
                    document_context += f"""

📄 YOUR UPLOADED FILE: {file.name}
═══════════════════════════════════════════════════════════════════
{file_content}
═══════════════════════════════════════════════════════════════════
"""
        
        # Build enhanced prompt with document context
        full_prompt = prompt
        if document_context:
            full_prompt = f"""STUDENT QUESTION: {prompt}

STUDENT'S UPLOADED WORK/DOCUMENTS:
{document_context}

HELP THE STUDENT understand their work using guided questions and scaffolded support."""
        
        # Add user message to chat history
        st.session_state.student_messages.append({"role": "user", "content": full_prompt})
        
        # Display user message (original prompt only) with avatar
        import os
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        # Extract curriculum keywords from student query
        from utils import detect_trending_keywords, update_trending_keywords
        detected_keywords = detect_trending_keywords(prompt)
        
        # Save and log the student's prompt with keyword tracking
        if database_available and student_id:
            db = get_db()
            if db:
                try:
                    # Save conversation message
                    save_conversation_message(
                        db, st.session_state.student_session_id, 'student',
                        'user', prompt, student_id=student_id
                    )
                    
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
                        pattern = r'\b(' + re.escape(keyword) + r')\b'
                        highlighted_response = re.sub(
                            pattern, 
                            r'**\1**', 
                            highlighted_response, 
                            flags=re.IGNORECASE
                        )
                
                st.markdown(highlighted_response)
        
        # Add assistant response to chat history
        st.session_state.student_messages.append({"role": "assistant", "content": response})
        
        # Save and log the AI response
        if database_available and student_id:
            db = get_db()
            if db:
                try:
                    # Save conversation message
                    save_conversation_message(
                        db, st.session_state.student_session_id, 'student',
                        'assistant', response, student_id=student_id
                    )
                    # Log student activity
                    log_student_activity(
                        db, 
                        student_id, 
                        'learning_response', 
                        prompt_text=prompt,
                        response_text=response,
                        session_id=st.session_state.student_session_id
                    )
                except Exception as e:
                    print(f"Error saving conversation/logging response: {str(e)}")
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
                    
                    # Remove Student Account section (only for primary educator)
                    st.markdown("---")
                    st.markdown("### ⚠️ Remove Student Account")
                    st.warning("**Warning**: Removing a student account will permanently delete all their data, including learning activities, conversations, and progress. This action cannot be undone.")
                    
                    # Confirmation checkbox
                    confirm_delete = st.checkbox(
                        f"I understand this will permanently delete {selected_student.full_name}'s account and all associated data",
                        key="confirm_delete_student"
                    )
                    
                    # Delete button (only enabled if confirmed)
                    if st.button(
                        f"🗑️ Permanently Remove {selected_student.full_name}",
                        type="secondary",
                        disabled=not confirm_delete,
                        key="delete_student_button"
                    ):
                        from database import delete_student
                        
                        with st.spinner(f"Removing {selected_student.full_name}..."):
                            if delete_student(db, selected_student.id):
                                st.success(f"✅ Successfully removed {selected_student.full_name}'s account")
                                st.info("Refreshing dashboard...")
                                st.rerun()
                            else:
                                st.error("❌ Failed to remove student account. Please try again.")
            
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
