import streamlit as st
from auth import login_page, signup_page, create_student_page, show_user_info
from database import create_tables
from interfaces import show_lesson_planning_interface, show_companion_interface, show_student_interface, show_clear_conversation_button

# Configure page
st.set_page_config(
    page_title="Guide - Your Montessori Companion",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
create_tables()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login', 'signup', 'create_student'

# Custom CSS for Montessori aesthetics
st.markdown("""
<style>
.main-header {
    text-align: center;
    color: #2E8B57;
    margin-bottom: 2rem;
}
.subtitle {
    text-align: center;
    color: #666;
    font-style: italic;
    margin-bottom: 2rem;
}
.welcome-box {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 2rem;
    border-radius: 10px;
    margin: 2rem 0;
    border-left: 5px solid #2E8B57;
}
.user-type {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 3px solid #2E8B57;
}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<h1 class="main-header">🌟 Guide - Your Montessori Companion</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">From lesson planning to philosophy, get clear guidance that supports your teaching</p>', unsafe_allow_html=True)

# Authentication and main application logic
if not st.session_state.authenticated:
    # Welcome section
    st.markdown("""
    <div class="welcome-box">
        <h3>✨ Welcome to Your Montessori Educational Planning Tool</h3>
        <p><em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em></p>
        
        <p style="text-align: center; margin: 2rem 0;"><strong>Comprehensive Educational Planning with:</strong><br>
        <em>Montessori Principles</em> • <em>Australian Curriculum V.9 Alignment</em> • <em>Scope & Sequence Creation</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Authentication mode selector
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔑 Login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()
    
    with col2:
        if st.button("📝 Sign Up", use_container_width=True):
            st.session_state.auth_mode = "signup"
            st.rerun()
    
    with col3:
        st.write("")  # Empty space for layout
    
    # Display appropriate authentication form
    if st.session_state.auth_mode == "login":
        login_page()
    elif st.session_state.auth_mode == "signup":
        signup_page()
    
    # Info about the platform
    st.markdown("""
    <div style="margin-top: 3rem;">
        <div class="user-type">
            <strong>🏠 Home-School Parents:</strong> Create comprehensive educational plans, lesson sequences, and demonstrate curriculum alignment for auditing authorities.
        </div>
        
        <div class="user-type">
            <strong>👩‍🏫 Teachers:</strong> Develop Montessori-aligned lesson plans with Australian Curriculum codes, scope and sequence planning, and professional development resources.
        </div>
        
        <div class="user-type">
            <strong>👨‍🎓 Students:</strong> Access age-appropriate learning support from early years through adolescence with Montessori-guided tutoring experiences.
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # Authenticated user interface
    show_user_info()
    
    # Navigation menu for authenticated users
    if not st.session_state.get('is_student'):
        # Educator interface (teachers and parents)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 Lesson Planning", use_container_width=True):
                st.session_state.auth_mode = "lesson_planning"
                st.rerun()
        
        with col2:
            if st.button("👨‍🎓 Create Student Account", use_container_width=True):
                st.session_state.auth_mode = "create_student"
                st.rerun()
        
        with col3:
            if st.button("🗨️ Montessori Companion", use_container_width=True):
                st.session_state.auth_mode = "companion"
                st.rerun()
        
        # Default to lesson planning for educators
        if 'auth_mode' not in st.session_state or st.session_state.auth_mode not in ['lesson_planning', 'create_student', 'companion']:
            st.session_state.auth_mode = 'lesson_planning'
    else:
        # Student interface
        st.session_state.auth_mode = 'student_companion'
    
    # Display appropriate interface based on mode
    if st.session_state.auth_mode == "create_student":
        create_student_page()
    elif st.session_state.auth_mode == "lesson_planning":
        show_lesson_planning_interface()
    elif st.session_state.auth_mode == "companion":
        show_companion_interface()
    elif st.session_state.auth_mode == "student_companion":
        show_student_interface()
    
# Main app logic continues here

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem;'>
        Guide - Your Montessori Companion | Powered by OpenAI GPT-4o Mini<br>
        Grounded in authentic Montessori principles and foundational texts<br>
        <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)
