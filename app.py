import streamlit as st
from auth import login_page, signup_page, create_student_page, show_user_info
from database import create_tables, database_status_message, database_available
from interfaces import show_lesson_planning_interface, show_companion_interface, show_student_interface, show_student_dashboard_interface, show_great_story_interface, show_planning_notes_interface, show_privacy_policy, show_data_access_interface, show_account_deletion_interface, show_pd_expert_interface
from replit_auth import check_replit_auth, authenticate_with_replit, show_replit_auth_status

# Configure page
st.set_page_config(
    page_title="Guide - Your Montessori Companion",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database and show status
if not database_available:
    st.warning("Running in limited mode - authentication and data storage are not available.")
    st.info("You can still explore the Montessori companion features.")
elif not create_tables():
    st.warning("Database initialization failed - some features may not work properly.")
    st.info("You can still explore the companion features while we resolve this.")
else:
    # Run data retention cleanup periodically (APP 11.2 compliance)
    from database import get_db, cleanup_old_data, get_data_retention_status
    from datetime import datetime, timedelta
    
    # Check if we should run cleanup (once per day)
    if 'last_cleanup_check' not in st.session_state:
        st.session_state.last_cleanup_check = datetime.now() - timedelta(days=2)  # Force first check
    
    time_since_last_check = datetime.now() - st.session_state.last_cleanup_check
    
    # Run cleanup if it's been more than 24 hours
    if time_since_last_check > timedelta(hours=24):
        db = get_db()
        if db:
            try:
                # Get status before cleanup (for logging)
                status = get_data_retention_status(db)
                if status and (status['old_conversations'] > 0 or status['old_student_activities'] > 0):
                    # Run cleanup
                    deleted = cleanup_old_data(db)
                    if deleted:
                        print(f"Data retention cleanup: {deleted}")  # Log for admin
                
                # Update last check time
                st.session_state.last_cleanup_check = datetime.now()
            except Exception as e:
                print(f"Error during data retention cleanup: {str(e)}")
            finally:
                db.close()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login', 'signup', 'create_student'

# Auto-authenticate with Replit Auth if available and not already authenticated
if not st.session_state.authenticated and not st.session_state.get('replit_auth_checked'):
    is_replit_auth, replit_info = check_replit_auth()
    if is_replit_auth and replit_info and database_available:
        # Attempt auto-authentication
        authenticate_with_replit()
    st.session_state.replit_auth_checked = True

# Load Montessori Design System
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css('static/css/montessori-theme.css')

# Additional custom CSS for specific components
st.markdown("""
<style>
.main-header {
    text-align: center;
    font-family: var(--font-serif);
    color: var(--color-ink);
    margin-bottom: 0.5rem;
    font-size: 4rem;
    font-weight: 500;
}
.main-byline {
    text-align: center;
    color: var(--color-ink);
    font-family: var(--font-serif);
    font-size: 1.3rem;
    font-weight: 300;
    margin-bottom: 1rem;
}
.subtitle {
    text-align: center;
    color: var(--color-ink);
    font-style: italic;
    margin-bottom: 2rem;
    opacity: 0.8;
}
.welcome-box {
    background: linear-gradient(135deg, var(--color-sand), var(--color-sky));
    padding: 2rem;
    border-radius: var(--radius-large);
    margin: 2rem 0;
    border-left: 5px solid var(--color-leaf);
    box-shadow: var(--shadow-soft);
}
.user-type {
    background: var(--color-sand);
    padding: 1rem;
    border-radius: var(--radius-medium);
    margin: 1rem 0;
    border-left: 3px solid var(--color-leaf);
}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<h1 class="main-header">🌟 Guide</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-byline">Your Montessori Companion</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">From lesson planning to philosophy and methodology, get clear guidance that supports your teaching and learning</p>', unsafe_allow_html=True)

# Authentication and main application logic
if not st.session_state.authenticated:
    # Welcome section
    st.markdown("""
    <div class="welcome-box">
        <h3>✨ Welcome to Guide - Your Montessori Educational Planning Tool</h3>
        <p><em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em></p>
        
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
        if st.button("🔒 Privacy Policy", use_container_width=True):
            st.session_state.auth_mode = "privacy_policy"
            st.rerun()
    
    # Display appropriate authentication form
    if st.session_state.auth_mode == "login":
        login_page()
    elif st.session_state.auth_mode == "signup":
        signup_page()
    elif st.session_state.auth_mode == "privacy_policy":
        show_privacy_policy()
    

else:
    # Authenticated user interface
    show_user_info()
    
    # Navigation menu for authenticated users
    if not st.session_state.get('is_student'):
        # Educator interface
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 Lesson Planning", use_container_width=True):
                st.session_state.auth_mode = "lesson_planning"
                st.rerun()
            
            if st.button("🗨️ Montessori Companion", use_container_width=True):
                st.session_state.auth_mode = "companion"
                st.rerun()
        
        with col2:
            if st.button("📖 Great Stories", use_container_width=True):
                st.session_state.auth_mode = "great_stories"
                st.rerun()
            
            if st.button("📝 Planning Notes", use_container_width=True):
                st.session_state.auth_mode = "planning_notes"
                st.rerun()
        
        with col3:
            if st.button("👨‍🎓 Create Student", use_container_width=True):
                st.session_state.auth_mode = "create_student"
                st.rerun()
            
            if st.button("📊 Student Dashboard", use_container_width=True):
                st.session_state.auth_mode = "student_dashboard"
                st.rerun()
        
        # PD Expert Mode (restricted access)
        if st.session_state.get('user_email') == "guideaichat@gmail.com":
            st.markdown("---")
            if st.button("🧭 PD Expert Mode", use_container_width=True, type="primary"):
                st.session_state.auth_mode = "pd_expert"
                st.rerun()
        
        # Privacy & Settings row
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 My Data", use_container_width=True):
                st.session_state.auth_mode = "data_access"
                st.rerun()
        with col2:
            if st.button("⚙️ Account", use_container_width=True):
                st.session_state.auth_mode = "account_deletion"
                st.rerun()
        
        # Default to lesson planning for educators
        if 'auth_mode' not in st.session_state or st.session_state.auth_mode not in ['lesson_planning', 'create_student', 'companion', 'student_dashboard', 'great_stories', 'planning_notes', 'privacy_policy', 'data_access', 'account_deletion', 'pd_expert']:
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
    elif st.session_state.auth_mode == "student_dashboard":
        show_student_dashboard_interface()
    elif st.session_state.auth_mode == "great_stories":
        show_great_story_interface()
    elif st.session_state.auth_mode == "planning_notes":
        show_planning_notes_interface()
    elif st.session_state.auth_mode == "pd_expert":
        show_pd_expert_interface()
    elif st.session_state.auth_mode == "student_companion":
        show_student_interface()
    elif st.session_state.auth_mode == "privacy_policy":
        show_privacy_policy()
    elif st.session_state.auth_mode == "data_access":
        show_data_access_interface()
    elif st.session_state.auth_mode == "account_deletion":
        show_account_deletion_interface()
    
# Main app logic continues here

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem;'>
        <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em><br><br>
        Guide - Your Montessori Companion | Powered by OpenAI GPT-4o Mini<br>
        Grounded in authentic Montessori principles and foundational texts<br>
        Brought to you by Auxpery - <em>Gentle Technology for Thoughtful Teaching</em>
    </div>
    """,
    unsafe_allow_html=True
)
