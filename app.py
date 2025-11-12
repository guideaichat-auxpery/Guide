import streamlit as st
import logging
import sys
from auth import login_page, signup_page, create_student_page, show_user_info
from database import create_tables, database_status_message, database_available
from interfaces import show_lesson_planning_interface, show_companion_interface, show_student_interface, show_student_dashboard_interface, show_great_story_interface, show_planning_notes_interface, show_privacy_policy, show_data_access_interface, show_account_deletion_interface, show_pd_expert_interface

# ---- STRUCTURED LOGGING CONFIGURATION ----
# Centralized logging setup for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for app module
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Guide - Your prepared digital environment",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Backend optimization: Initialize database once at process startup
from database import initialize_database_once

if not database_available:
    st.warning("Running in limited mode - authentication and data storage are not available.")
    st.info("You can still explore the Montessori companion features.")
else:
    # Run one-time initialization (tables, migrations) - process-level, not per-session
    initialize_database_once()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login', 'signup', 'create_student'

# Load Design Systems - cached for performance
@st.cache_data
def load_css(file_path):
    """Load CSS file with caching to improve performance"""
    with open(file_path) as f:
        return f'<style>{f.read()}</style>'

# Load Montessori theme for general interface
st.markdown(load_css('static/css/montessori-theme.css'), unsafe_allow_html=True)

# Load Danish eco theme for educator dashboard cards
st.markdown(load_css('static/css/danish-eco-theme.css'), unsafe_allow_html=True)

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
st.markdown('<h1 class="main-header">Guide</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-byline">Your prepared digital environment</p>', unsafe_allow_html=True)

# Only show subtitle for unauthenticated users
if not st.session_state.authenticated:
    st.markdown('<p class="subtitle">From lesson planning to Montessori philosophy and methodology, get clear guidance that supports your teaching and learning</p>', unsafe_allow_html=True)

# Authentication and main application logic
if not st.session_state.authenticated:
    # Welcome section
    st.markdown("""
    <div class="welcome-box">
        <h3>✨ Welcome to Guide</h3>
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
        if st.button("📋 Terms & Conditions", use_container_width=True):
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
    # Explicitly check user type to ensure proper role-based UI
    is_student = st.session_state.get('is_student', None)
    
    if is_student is False:
        # Educator interface
        
        # Default to dashboard home for educators
        if 'auth_mode' not in st.session_state or st.session_state.auth_mode not in ['dashboard_home', 'lesson_planning', 'create_student', 'companion', 'student_dashboard', 'great_stories', 'planning_notes', 'privacy_policy', 'data_access', 'account_deletion', 'pd_expert']:
            st.session_state.auth_mode = 'dashboard_home'
        
        # Show dashboard home or specific interface
        current_mode = st.session_state.get('auth_mode', 'dashboard_home')
        
        # Only show dashboard navigation cards on home view
        if current_mode == 'dashboard_home':
            # Open sticky card container - pins cards at top during interactions
            st.markdown('<div class="sticky-card-container">', unsafe_allow_html=True)
            
            # Institution setting check (inside sticky container)
            from database import get_db, update_educator_institution, is_institution_enforcement_on, User
            db = get_db()
            if db:
                try:
                    educator_id = st.session_state.get('user_id')
                    educator = db.query(User).filter(User.id == educator_id).first()
                    
                    # Check if institution needs to be set
                    if not educator.institution_name or educator.institution_name.strip() == '':
                        st.warning("⚠️ **Action Required:** Please set your institution name to enable student sharing.")
                        
                        with st.form("institution_form"):
                            institution_name = st.text_input(
                                "Institution Name:",
                                placeholder="Montessori School",
                                help="This enables secure student sharing with educators from your institution"
                            )
                            submitted = st.form_submit_button("Set Institution")
                            
                            if submitted and institution_name:
                                success, auto_enabled = update_educator_institution(db, educator_id, institution_name)
                                if success:
                                    if auto_enabled:
                                        st.success("✅ Institution set! 🚀 All educators now have institutions - enforcement automatically enabled!")
                                    else:
                                        st.success(f"✅ Institution set to: {institution_name}")
                                    st.rerun()
                                else:
                                    st.error("Failed to update institution")
                except Exception as e:
                    print(f"Institution check error: {str(e)}")
                finally:
                    db.close()
            
            # Educator Dashboard - Welcome and Cards
            educator_name = st.session_state.get('user_email', 'Educator').split('@')[0].title()
            st.markdown(f'<h2 style="margin-bottom: 1rem;">Welcome back, {educator_name}</h2>', unsafe_allow_html=True)
            
            # Institution badge
            try:
                from database import get_db, is_institution_enforcement_on, User
                db = get_db()
                if db:
                    educator_id = st.session_state.get('user_id')
                    educator = db.query(User).filter(User.id == educator_id).first()
                    if educator and educator.institution_name:
                        enforcement_on = is_institution_enforcement_on(db)
                        status_icon = "🔒" if enforcement_on else "⏳"
                        status_text = "Active" if enforcement_on else "Grace Period"
                        st.markdown(f"""
                        <div style="background-color: rgba(120, 154, 118, 0.08); border-left: 3px solid #789A76; 
                                    padding: 0.5rem 1rem; margin-bottom: 1.5rem; border-radius: 4px; display: inline-block;">
                            <span style="font-size: 14px; opacity: 0.75;">{status_icon} <strong>Institution:</strong> {educator.institution_name} | <strong>Sharing Enforcement:</strong> {status_text}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    db.close()
            except Exception as e:
                print(f"Error fetching institution info: {e}")
            
            # Navigation cards in 3x2 grid
            col1, col2, col3 = st.columns(3)
            
            cards = [
                {"title": "Lesson Planning", "body": "Design age-appropriate learning experiences", "icon": "📚", "mode": "lesson_planning", "key": "lp"},
                {"title": "Montessori Companion", "body": "Tap into Montessori wisdom and training", "icon": "🌱", "mode": "companion", "key": "comp"},
                {"title": "Student Dashboard", "body": "Stay connected to your students' learning", "icon": "👥", "mode": "student_dashboard", "key": "sd"},
                {"title": "Planning Notes", "body": "Record and save your lesson plans", "icon": "📝", "mode": "planning_notes", "key": "pn"},
                {"title": "Create Student", "body": "Add new students", "icon": "➕", "mode": "create_student", "key": "cs"},
                {"title": "Great Stories", "body": "Create narratives to introduce new learning", "icon": "📖", "mode": "great_stories", "key": "gs"}
            ]
            
            columns = [col1, col2, col3]
            for idx, card in enumerate(cards):
                col_idx = idx % 3
                with columns[col_idx]:
                    button_label = f"{card['icon']} **{card['title']}**\n\n{card['body']}"
                    if st.button(button_label, key=f"{card['key']}_card_btn", use_container_width=True, type="secondary"):
                        st.session_state.auth_mode = card['mode']
                        st.rerun()
            
            # Account buttons
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
            acc_col1, acc_col2 = st.columns(2)
            with acc_col1:
                if st.button("My Data", key="data_btn", use_container_width=True):
                    st.session_state.auth_mode = "data_access"
                    st.rerun()
            with acc_col2:
                if st.button("Account Settings", key="account_btn", use_container_width=True):
                    st.session_state.auth_mode = "account_deletion"
                    st.rerun()
            
            # PD Expert Mode
            if st.session_state.get('user_email') == "guideaichat@gmail.com":
                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("🔬 PD Expert Mode", use_container_width=True, type="primary"):
                    st.session_state.auth_mode = "pd_expert"
                    st.rerun()
            
            # Close sticky card container
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Chat content zone for any future content on dashboard home
            st.markdown('<div class="chat-content-zone">', unsafe_allow_html=True)
            # Any additional dashboard content would go here
            st.markdown('</div>', unsafe_allow_html=True)
    elif is_student is True:
        # Student interface - explicitly for students only
        st.session_state.auth_mode = 'student_companion'
    else:
        # Fallback for undefined state - treat as student for safety
        st.session_state.auth_mode = 'student_companion'
    
    # Display appropriate interface based on mode
    if st.session_state.auth_mode == "dashboard_home":
        # Dashboard is already rendered above for educators
        pass
    elif st.session_state.auth_mode == "create_student":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_cs"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        create_student_page()
    elif st.session_state.auth_mode == "lesson_planning":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_lp"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_lesson_planning_interface()
    elif st.session_state.auth_mode == "companion":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_comp"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_companion_interface()
    elif st.session_state.auth_mode == "student_dashboard":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_sd"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_student_dashboard_interface()
    elif st.session_state.auth_mode == "great_stories":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_gs"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_great_story_interface()
    elif st.session_state.auth_mode == "planning_notes":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_pn"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_planning_notes_interface()
    elif st.session_state.auth_mode == "pd_expert":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_pd"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_pd_expert_interface()
    elif st.session_state.auth_mode == "student_companion":
        show_student_interface()
    elif st.session_state.auth_mode == "privacy_policy":
        show_privacy_policy()
    elif st.session_state.auth_mode == "data_access":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_data"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_data_access_interface()
    elif st.session_state.auth_mode == "account_deletion":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_acct"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_account_deletion_interface()
    
# Main app logic continues here

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem;'>
        <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em><br><br>
        Guide - Your prepared digital environment<br>
        Brought to you by Auxpery - <em>Gentle Technology for Thoughtful Education</em><br><br>
        Contact us at guide@auxpery.com.au
    </div>
    """,
    unsafe_allow_html=True
)
