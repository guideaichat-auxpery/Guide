import streamlit as st
from utils import call_openai_api, get_max_tokens_for_user_type

def show_lesson_planning_interface():
    """Educational planning interface for teachers and parents with Australian Curriculum alignment"""
    st.markdown("### 📚 Montessori Educational Planning Tool")
    st.markdown("*Create comprehensive lesson plans and scope & sequence with Australian Curriculum V.9 alignment*")
    
    # Age group selector
    age_group = st.selectbox(
        "Select Age Group:",
        ["early_years", "primary", "adolescent"],
        format_func=lambda x: {
            "early_years": "Early Years (3-6)",
            "primary": "Primary (6-12)", 
            "adolescent": "Adolescent (12-18)"
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
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Quick planning templates based on age group
    st.markdown(f"#### Quick {age_group.replace('_', ' ').title()} Planning Templates:")
    
    if age_group == "early_years":
        templates = [
            f"Create a practical life lesson for 3-year-olds with AC V.9 alignment for {planning_type}",
            f"Design a sensorial exploration activity with Montessori materials for {planning_type}",
            f"Plan a grace and courtesy lesson with cultural connections for {planning_type}",
            f"Develop a language enrichment activity for early literacy for {planning_type}"
        ]
    elif age_group == "primary":
        templates = [
            f"Create a cosmic education lesson connecting math and science for {planning_type}",
            f"Design a cultural studies project on Australian geography for {planning_type}",
            f"Plan a collaborative research activity for mixed-age groups for {planning_type}",
            f"Develop a practical application of mathematical concepts for {planning_type}"
        ]
    else:  # adolescent
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
            7. Include parent/family engagement suggestions for home-school families
            
            Format the response with clear sections and practical implementation guidance.
            """
            
            st.session_state.messages.append({"role": "user", "content": enhanced_prompt})
            
            with st.spinner("Creating comprehensive educational plan..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.messages, max_tokens)
                if response:
                    st.markdown("### 📚 Educational Planning Guidance")
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble generating the educational plan. Please try again.")
    
    # Custom planning input
    if prompt := st.chat_input("Describe your specific educational planning needs..."):
        enhanced_prompt = f"""
        Educational Planning Request for {age_group} students:
        {prompt}
        
        Please ensure your response includes:
        1. Relevant Australian Curriculum V.9 codes and achievement standards
        2. Montessori pedagogical rationale
        3. Practical implementation steps
        4. Assessment and observation strategies
        5. Materials and resources needed
        6. Extension and differentiation options
        """
        
        st.session_state.messages.append({"role": "user", "content": enhanced_prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Creating educational guidance..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def show_companion_interface():
    """Companion interface for general Montessori guidance (secondary feature)"""
    st.markdown("### 🗨️ Montessori Companion")
    st.markdown("*Explore Montessori philosophy and get guidance on educational approaches*")
    
    # Display chat history
    for message in st.session_state.messages:
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
            st.session_state.messages.append({"role": "user", "content": topic})
            
            with st.spinner("Exploring Montessori philosophy..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.messages, max_tokens)
                if response:
                    st.markdown("### 🗨️ Montessori Insight")
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble generating guidance. Please try again.")
    
    # Chat input for custom questions
    if prompt := st.chat_input("Ask about Montessori philosophy, approaches, or implementation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Providing Montessori guidance..."):
                max_tokens = get_max_tokens_for_user_type('educator')
                response = call_openai_api(st.session_state.messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def show_student_interface():
    """Student interface for all age groups with age-appropriate guidance"""
    age_group = st.session_state.get('age_group', 'primary')
    
    st.markdown(f"### 👨‍🎓 Student Learning Support ({age_group.replace('_', ' ').title()})")
    st.markdown("*Discover the joy of self-directed learning with Montessori principles*")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Age-appropriate learning topics
    st.markdown("#### Explore Learning:")
    
    if age_group == "early_years":
        topics = [
            "How can I help with practical life activities at home?",
            "Why do we use special learning materials?",
            "How can I be more independent?",
            "What makes learning fun and interesting?",
            "How can I help my friends learn too?"
        ]
    elif age_group == "primary":
        topics = [
            "How are all subjects connected to the cosmic story?",
            "Why is hands-on learning so important?",
            "How can I research topics that interest me?",
            "What makes a good learning environment?",
            "How can I help younger and older students?"
        ]
    else:  # adolescent
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
            
            st.session_state.messages.append({"role": "user", "content": age_appropriate_prompt})
            
            with st.spinner("Exploring your question..."):
                max_tokens = get_max_tokens_for_user_type('student')
                response = call_openai_api(st.session_state.messages, max_tokens)
                if response:
                    st.markdown("### 🌟 Learning Discovery")
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble answering. Please try again.")
    
    # Chat input for custom questions
    if prompt := st.chat_input("Ask me about learning, interests, or how things work..."):
        age_appropriate_prompt = f"""
        Question from a {age_group} student: {prompt}
        
        Please provide an age-appropriate response that encourages exploration, 
        independence, and follows Montessori principles for {age_group} learners.
        """
        
        st.session_state.messages.append({"role": "user", "content": age_appropriate_prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking about your question..."):
                max_tokens = get_max_tokens_for_user_type('student')
                response = call_openai_api(st.session_state.messages, max_tokens)
                
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")
    
    show_clear_conversation_button()

def show_clear_conversation_button():
    """Reusable clear conversation button"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()