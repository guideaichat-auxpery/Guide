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
                        logger.info(f"Data retention cleanup: {deleted}")
                
                # Update last check time
                st.session_state.last_cleanup_check = datetime.now()
            except Exception as e:
                logger.error(f"Error during data retention cleanup: {str(e)}")
            finally:
                db.close()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login', 'signup', 'create_student'

# Load Design Systems
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load both Montessori theme and Danish eco design
load_css('static/css/montessori-theme.css')
load_css('static/css/danish-eco-theme.css')

# Danish Educator Dashboard Function
def render_danish_educator_dashboard():
    """Render the Danish eco-design educator dashboard with card-based navigation"""
    
    # Get educator name and institution info
    educator_name = st.session_state.get('user_email', 'Educator').split('@')[0].title()
    
    # Get institution info from database
    institution_info = ""
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
                institution_info = f"{status_icon} <strong>Institution:</strong> {educator.institution_name} | <strong>Sharing Enforcement:</strong> {status_text}"
            db.close()
    except Exception as e:
        print(f"Error fetching institution info: {e}")
    
    # Wrapper for entire dashboard
    st.markdown('<div class="danish-dashboard-wrapper">', unsafe_allow_html=True)
    
    # Danish Header
    st.markdown(f"""
    <div class="danish-header">
        <div class="danish-header-left">
            <span class="danish-wordmark">Guide</span>
            <span class="danish-byline">by AUXPERY</span>
        </div>
        <div class="danish-header-right">
            <svg class="danish-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
            </svg>
            <svg class="danish-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>
                <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>
            </svg>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Main Dashboard Content - open div
    st.markdown('<div class="danish-dashboard">', unsafe_allow_html=True)
    
    # Greeting
    st.markdown(f'<h1 class="danish-greeting">Welcome back, {educator_name}</h1>', unsafe_allow_html=True)
    
    # Institution badge if available
    if institution_info:
        st.markdown(f'<div class="danish-institution-badge">{institution_info}</div>', unsafe_allow_html=True)
    
    # Create 3x2 grid of cards using Streamlit columns
    col1, col2, col3 = st.columns(3)
    
    # Card data
    cards = [
        {"title": "Lesson Planning", "body": "Design age-appropriate learning experiences", "icon_paths": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>', "mode": "lesson_planning", "key": "lp"},
        {"title": "Montessori Companion", "body": "Tap into Montessori wisdom and training", "icon_paths": '<path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"></path><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"></path><path d="M12 2v2"></path><path d="M12 22v-2"></path><path d="m17 20.66-1-1.73"></path><path d="M11 10.27 7 3.34"></path><path d="m20.66 17-1.73-1"></path><path d="m3.34 7 1.73 1"></path><path d="M14 12h8"></path><path d="M2 12h2"></path><path d="m20.66 7-1.73 1"></path><path d="m3.34 17 1.73-1"></path><path d="m17 3.34-1 1.73"></path><path d="m11 13.73-4 6.93"></path>', "mode": "companion", "key": "comp"},
        {"title": "Student Dashboard", "body": "Stay connected to your students' learning", "icon_paths": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>', "mode": "student_dashboard", "key": "sd"},
        {"title": "Planning Notes", "body": "Record and save your lesson plans", "icon_paths": '<path d="M9 5H2v7l6.29 6.29c.94.94 2.48.94 3.42 0l3.58-3.58c.94-.94.94-2.48 0-3.42L9 5Z"></path><path d="M6 9.01V9"></path><path d="m15 5 6.3 6.3a2.4 2.4 0 0 1 0 3.4L17 19"></path>', "mode": "planning_notes", "key": "pn"},
        {"title": "Create Student", "body": "Add new students", "icon_paths": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><line x1="19" y1="8" x2="19" y2="14"></line><line x1="22" y1="11" x2="16" y2="11"></line>', "mode": "create_student", "key": "cs"},
        {"title": "Great Stories", "body": "Create narratives to introduce new learning", "icon_paths": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>', "mode": "great_stories", "key": "gs"}
    ]
    
    # Distribute cards across columns - use simple, functional approach
    columns = [col1, col2, col3]
    for idx, card in enumerate(cards):
        col_idx = idx % 3
        with columns[col_idx]:
            # Simple button with icon emoji as visual identifier
            icon_map = {
                "lp": "📚",
                "comp": "🌱", 
                "sd": "👥",
                "pn": "📝",
                "cs": "➕",
                "gs": "📖"
            }
            icon = icon_map.get(card['key'], "📌")
            
            button_label = f"{icon} **{card['title']}**\n\n{card['body']}"
            
            if st.button(
                button_label,
                key=f"{card['key']}_card_btn",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.auth_mode = card['mode']
                st.rerun()
    
    # Account Section
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
    
    # PD Expert Mode (restricted access)
    if st.session_state.get('user_email') == "guideaichat@gmail.com":
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🔬 PD Expert Mode", use_container_width=True, type="primary"):
            st.session_state.auth_mode = "pd_expert"
            st.rerun()
    
    # Close danish-dashboard div
    st.markdown('</div>', unsafe_allow_html=True)
    # Close danish-dashboard-wrapper div
    st.markdown('</div>', unsafe_allow_html=True)

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
    # Explicitly check user type to ensure proper role-based UI
    is_student = st.session_state.get('is_student', None)
    
    # Institution setting for educators (compact display)
    if is_student is False:
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
    
    if is_student is False:
        # Educator interface
        
        # Default to dashboard home for educators
        if 'auth_mode' not in st.session_state or st.session_state.auth_mode not in ['dashboard_home', 'lesson_planning', 'create_student', 'companion', 'student_dashboard', 'great_stories', 'planning_notes', 'privacy_policy', 'data_access', 'account_deletion', 'pd_expert']:
            st.session_state.auth_mode = 'dashboard_home'
        
        # Show Danish dashboard home or specific interface
        current_mode = st.session_state.get('auth_mode', 'dashboard_home')
        
        # Only show dashboard navigation cards on home view
        if current_mode == 'dashboard_home':
            render_danish_educator_dashboard()
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
        Guide - Your prepared digital environment | Powered by OpenAI GPT-4o Mini<br>
        Grounded in authentic Montessori principles and foundational texts<br>
        Brought to you by Auxpery - <em>Gentle Technology for Thoughtful Education</em>
    </div>
    """,
    unsafe_allow_html=True
)
