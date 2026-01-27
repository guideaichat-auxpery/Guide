import streamlit as st
import logging
import sys
from auth import login_page, signup_page, create_student_page, show_user_info, check_subscription_status, show_pricing_page, invalidate_subscription_cache, show_account_settings, sync_subscription_from_stripe, check_and_restore_session, show_forgot_password_form, show_reset_password_form, school_join_page, show_school_admin_dashboard, school_setup_page
from database import create_tables, database_status_message, database_available
from interfaces import show_lesson_planning_interface, show_companion_interface, show_student_interface, show_student_dashboard_interface, show_great_story_interface, show_planning_notes_interface, show_privacy_policy, show_data_access_interface, show_account_deletion_interface, show_pd_expert_interface, show_imaginarium_interface, show_contact_form

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
    initial_sidebar_state="expanded"
)

# Google Analytics 4 tracking (deferred load for faster initial page render)
GA_MEASUREMENT_ID = "G-L1LH5117YK"
st.markdown(f"""
    <!-- Google tag (gtag.js) - deferred to not block page render -->
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        // Load GA script after page is interactive, then configure
        window.addEventListener('load', function() {{
            var s = document.createElement('script');
            s.src = 'https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}';
            s.async = true;
            s.onload = function() {{
                gtag('js', new Date());
                gtag('config', '{GA_MEASUREMENT_ID}');
            }};
            document.head.appendChild(s);
        }});
    </script>
""", unsafe_allow_html=True)

# Scroll behavior: Only scroll to top on navigation, not on chat updates
# Check if this is a navigation action (page/mode change) vs chat action
from utils import force_scroll_to_top, inject_sidebar_toggle_button

# Track previous mode to detect navigation
current_mode = st.session_state.get('auth_mode', 'login')
previous_mode = st.session_state.get('_previous_auth_mode', None)

# Only scroll to top if mode changed (navigation) or first load
if previous_mode != current_mode:
    force_scroll_to_top()
    st.session_state['_previous_auth_mode'] = current_mode

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

# Persistent session restoration: Check for saved session token on page load
if database_available and not st.session_state.get('authenticated'):
    check_and_restore_session()

# Handle return from Stripe checkout - sync subscription and invalidate cache
try:
    query_params = st.query_params
    if query_params.get('subscription') == 'success':
        educator_id = st.session_state.get('user_id')
        user_email = st.session_state.get('user_email')
        if educator_id and user_email:
            invalidate_subscription_cache(educator_id)
            sync_result = sync_subscription_from_stripe(educator_id, user_email)
            if sync_result and sync_result.get('isActive'):
                st.success("Payment successful! Your subscription is now active.")
            else:
                st.success("Payment received! Your subscription should be active shortly.")
        st.query_params.clear()
    
    # Handle password reset token from email link
    reset_token = query_params.get('reset_token')
    if reset_token:
        st.session_state.auth_mode = 'reset_password'
        st.session_state.reset_token = reset_token
    
    # Handle school invite link (/join/{invite_code})
    invite_code = query_params.get('join')
    if invite_code:
        st.session_state.auth_mode = 'school_join'
        st.session_state.school_invite_code = invite_code
    
    # Handle school setup token from marketing site checkout
    # URL format: /?school_setup=token_value
    school_setup_token = query_params.get('school_setup')
    if school_setup_token:
        st.session_state.auth_mode = 'school_setup'
        st.session_state.school_setup_token = school_setup_token
except Exception as e:
    logger.warning(f"Error processing query params: {e}")

# Session timeout configuration (security - child protection)
from datetime import datetime, timedelta

SESSION_TIMEOUT_STUDENT = timedelta(hours=2)  # 2 hours for students
SESSION_TIMEOUT_EDUCATOR = timedelta(minutes=30)  # 30 minutes for educators
SESSION_WARNING_THRESHOLD = timedelta(minutes=5)  # Warn 5 minutes before timeout

def check_session_timeout():
    """Check if session has timed out due to inactivity and handle logout"""
    if not st.session_state.get('authenticated', False):
        return False
    
    last_activity = st.session_state.get('last_activity_time')
    if not last_activity:
        # First activity - set the timestamp
        st.session_state.last_activity_time = datetime.now()
        return False
    
    # Determine timeout based on user type
    is_student = st.session_state.get('is_student', False)
    timeout = SESSION_TIMEOUT_STUDENT if is_student else SESSION_TIMEOUT_EDUCATOR
    user_type = "student" if is_student else "educator"
    
    time_since_activity = datetime.now() - last_activity
    
    # Check if session has timed out
    if time_since_activity > timeout:
        # Log the timeout
        logger.info(f"Session timeout for {user_type} after {time_since_activity}")
        
        # Clear session
        for key in ['authenticated', 'user_id', 'user_type', 'user_name', 'user_email', 
                    'is_student', 'username', 'educator_id', 'age_group', 'last_activity_time']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.warning(f"Your session has expired due to inactivity. Please log in again.")
        return True
    
    # Check if approaching timeout (warning)
    time_remaining = timeout - time_since_activity
    if time_remaining < SESSION_WARNING_THRESHOLD and time_remaining > timedelta(0):
        minutes_left = int(time_remaining.total_seconds() / 60)
        st.toast(f"Session expires in {minutes_left} minute(s). Activity will extend your session.", icon="⏰")
    
    # Update last activity time
    st.session_state.last_activity_time = datetime.now()
    return False

# Check session timeout for authenticated users
if st.session_state.get('authenticated', False):
    if check_session_timeout():
        st.rerun()

# Load Design Systems - combined and cached for faster page load
@st.cache_data
def load_all_css():
    """Load all CSS files in a single cached operation for faster page load"""
    css_files = [
        'static/css/montessori-theme.css',
        'static/css/danish-eco-theme.css', 
        'static/css/mobile-responsive.css',
        'static/css/accessibility.css'
    ]
    combined_css = []
    for file_path in css_files:
        with open(file_path) as f:
            combined_css.append(f.read())
    return f'<style>{" ".join(combined_css)}</style>'

# Load all CSS in a single markdown call (reduces render overhead)
st.markdown(load_all_css(), unsafe_allow_html=True)

# Base CSS for components (safe for all pages)
st.markdown("""
<style>
.main-header {
    text-align: center;
    font-family: var(--font-serif);
    color: var(--color-ink);
    margin-top: 0;
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

# Landing page specific CSS - only hide header/reduce padding on unauthenticated pages
# This was causing the sidebar to not appear after login!
if not st.session_state.get('authenticated', False):
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stAppViewContainer"] > section > div,
    [data-testid="stVerticalBlock"],
    .stMainBlockContainer,
    div[data-testid="stVerticalBlock"] { padding-top: 0 !important; }
    .stApp [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"]:first-child {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    </style>
    <script>
    // Layout fix for landing page only
    document.addEventListener('DOMContentLoaded', function() {
        requestAnimationFrame(function() {
            var containers = document.querySelectorAll('[data-testid="stVerticalBlock"], [class*="stMainBlockContainer"]');
            containers.forEach(function(el) { el.style.paddingTop = '0'; el.style.marginTop = '0'; });
            var header = document.querySelector('header[data-testid="stHeader"]');
            if (header) header.style.display = 'none';
        });
    });
    </script>
    """, unsafe_allow_html=True)

# Main Header - wrapped with reduced negative margin to avoid title being cut off
st.markdown('<div style="margin-top: -4rem;"><h1 class="main-header">Guide</h1></div>', unsafe_allow_html=True)
st.markdown('<p class="main-byline">Your prepared digital environment</p>', unsafe_allow_html=True)

# Inject floating sidebar toggle button (appears when sidebar is collapsed) - for all users
inject_sidebar_toggle_button()

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
    
    # Display login page with tabs (includes Sign Up and Terms)
    if st.session_state.auth_mode in ["login", "signup", "privacy_policy", None]:
        login_page()
    elif st.session_state.auth_mode == "forgot_password":
        show_forgot_password_form()
    elif st.session_state.auth_mode == "reset_password":
        reset_token = st.session_state.get('reset_token')
        if reset_token:
            show_reset_password_form(reset_token)
        else:
            st.error("Invalid reset link. Please request a new password reset.")
            if st.button("Request New Reset Link"):
                st.session_state.auth_mode = 'forgot_password'
                st.rerun()
    elif st.session_state.auth_mode == "school_join":
        invite_code = st.session_state.get('school_invite_code')
        if invite_code:
            school_join_page(invite_code)
        else:
            st.error("Invalid invite link")
            if st.button("Return to Login"):
                st.session_state.auth_mode = 'login'
                st.rerun()
    elif st.session_state.auth_mode == "school_setup":
        setup_token = st.session_state.get('school_setup_token')
        if setup_token:
            school_setup_page(setup_token)
        else:
            st.error("Invalid setup link")
            if st.button("Return to Login"):
                st.session_state.auth_mode = 'login'
                st.rerun()
    elif st.session_state.auth_mode == "contact":
        if st.button("← Back to Login", key="back_contact_guest"):
            st.session_state.auth_mode = "login"
            st.rerun()
        show_contact_form()
    

else:
    # Authenticated user interface - Force sidebar to render first
    with st.sidebar:
        st.empty()  # Ensure sidebar container is created
    show_user_info()
    
    # Navigation menu for authenticated users
    # Explicitly check user type to ensure proper role-based UI
    is_student = st.session_state.get('is_student', None)
    
    if is_student is False:
        # Educator interface
        
        # FAILPROOF SUBSCRIPTION CHECK
        # Trust session state verified at login (Stripe was checked directly)
        # This eliminates webhook dependency and DB sync issues
        educator_id = st.session_state.get('user_id')
        
        # ADMIN BYPASS: Skip all subscription checks for admin users
        # Get admin status from session and display for debugging
        session_is_admin = st.session_state.get('is_admin')
        session_verified = st.session_state.get('subscription_verified')
        session_active = st.session_state.get('subscription_active')
        
        # TEMPORARY DEBUG: Show admin status in UI
        if st.session_state.get('user_email') in ['ben@hmswairoa.net', 'admin@auxpery.com.au']:
            st.info(f"Debug: is_admin={session_is_admin}, verified={session_verified}, active={session_active}")
        
        if session_is_admin:
            has_active_subscription = True
            subscription_status = 'admin'
            print(f"[SUBSCRIPTION CHECK] ADMIN BYPASS - granting access")
        elif st.session_state.get('subscription_verified'):
            # Session already verified with Stripe - trust it completely
            has_active_subscription = st.session_state.get('subscription_active', False)
            subscription_status = st.session_state.get('subscription_status', 'none')
        else:
            # Not verified yet or Stripe was unavailable - try Stripe again
            from auth import sync_subscription_from_stripe
            import stripe_client
            user_email = st.session_state.get('user_email')
            
            # Initialize defaults
            has_active_subscription = False
            subscription_status = 'none'
            
            # FIRST: Check if user is admin from database before anything else
            if educator_id:
                from database import get_db, User
                admin_db = get_db()
                if admin_db:
                    try:
                        admin_user = admin_db.query(User).filter(User.id == educator_id).first()
                        # CRITICAL: Explicit boolean conversion to handle any type issues
                        raw_admin = admin_user.is_admin if (admin_user and hasattr(admin_user, 'is_admin')) else False
                        db_is_admin = bool(raw_admin) if raw_admin else False
                        if admin_user and db_is_admin:
                            print(f"[SUBSCRIPTION CHECK] ADMIN user {educator_id} detected from DB - bypassing Stripe check")
                            st.session_state.is_admin = True
                            st.session_state.subscription_verified = True
                            st.session_state.subscription_active = True
                            st.session_state.subscription_status = 'admin'
                            st.session_state.subscription_plan = 'admin'
                            has_active_subscription = True
                            subscription_status = 'admin'
                    except Exception as e:
                        print(f"[SUBSCRIPTION CHECK] Error checking admin: {e}")
                    finally:
                        admin_db.close()
            
            # Only proceed with Stripe check if not already resolved as admin
            if not st.session_state.get('is_admin') and user_email and educator_id:
                stripe_result = sync_subscription_from_stripe(educator_id, user_email)
                stripe_status = stripe_result.get('status', 'none') if stripe_result else 'error'
                
                if stripe_status == 'error':
                    # Stripe failed - ALWAYS grant grace access (benefit of the doubt)
                    print(f"[PAYWALL] Stripe check failed, granting GRACE ACCESS for educator {educator_id}")
                    db_result = stripe_client.get_subscription_from_db(educator_id)
                    plan = db_result.get('plan')
                    
                    # CRITICAL: On Stripe error, ALWAYS grant access temporarily
                    # Better to let a non-subscriber in briefly than lock out a paying user
                    has_active_subscription = True  # GRACE ACCESS
                    subscription_status = 'grace'
                    st.session_state.subscription_active = True
                    st.session_state.subscription_status = 'grace'
                    st.session_state.subscription_plan = plan or 'grace'
                    # subscription_verified stays False - will retry on next navigation
                else:
                    # Successful Stripe response - authoritative
                    has_active_subscription = stripe_result.get('isActive', False)
                    subscription_status = stripe_status
                    plan = stripe_result.get('plan')
                    
                    # Mark as verified - won't retry unless logged out
                    st.session_state.subscription_verified = True
                    st.session_state.subscription_active = has_active_subscription
                    st.session_state.subscription_status = subscription_status
                    st.session_state.subscription_plan = plan
            elif not st.session_state.get('is_admin'):
                # No email in session and not admin - use database as last resort
                subscription_info = check_subscription_status(educator_id)
                has_active_subscription = subscription_info.get('isActive', False)
                subscription_status = subscription_info.get('status', 'none')
        
        # If no active subscription, show pricing page (unless accessing account settings, admin, or in grace access)
        if not has_active_subscription and subscription_status not in ['trialing', 'active', 'grace', 'admin']:
            # FAILSAFE: Double-check admin status from database before showing paywall
            if educator_id:
                from database import get_db, User
                db_check = get_db()
                if db_check:
                    try:
                        db_user = db_check.query(User).filter(User.id == educator_id).first()
                        # CRITICAL: Explicit boolean conversion to handle any type issues
                        raw_admin = db_user.is_admin if (db_user and hasattr(db_user, 'is_admin')) else False
                        db_is_admin = bool(raw_admin) if raw_admin else False
                        if db_user and db_is_admin:
                            # User IS admin in database - fix session state and continue
                            print(f"[FAILSAFE] Admin user {educator_id} detected via DB check - fixing session state")
                            st.session_state.is_admin = True
                            st.session_state.subscription_verified = True
                            st.session_state.subscription_active = True
                            st.session_state.subscription_status = 'admin'
                            st.session_state.subscription_plan = 'admin'
                            has_active_subscription = True
                            subscription_status = 'admin'
                    finally:
                        db_check.close()
            
            # Allow access to account settings and logout even without subscription
            if not has_active_subscription and st.session_state.get('auth_mode') not in ['account_deletion', 'privacy_policy']:
                show_pricing_page()
                st.stop()
        
        # Default to dashboard home for educators
        if 'auth_mode' not in st.session_state or st.session_state.auth_mode not in ['dashboard_home', 'lesson_planning', 'create_student', 'companion', 'student_dashboard', 'great_stories', 'planning_notes', 'privacy_policy', 'data_access', 'account_deletion', 'pd_expert', 'imaginarium', 'school_admin_dashboard']:
            st.session_state.auth_mode = 'dashboard_home'
        
        # Show dashboard home or specific interface
        current_mode = st.session_state.get('auth_mode', 'dashboard_home')
        
        # Only show dashboard navigation cards on home view
        if current_mode == 'dashboard_home':
            # Open sticky card container - pins cards at top during interactions
            st.markdown('<div class="sticky-card-container">', unsafe_allow_html=True)
            
            # Get cached educator profile (single DB query, 60s cache)
            from database import get_cached_educator_profile, update_educator_institution, get_db, invalidate_educator_profile_cache
            educator_id = st.session_state.get('user_id')
            educator_profile = get_cached_educator_profile(educator_id)
            
            # Institution setting check (inside sticky container)
            if educator_profile and educator_profile.get('institution_needs_setup'):
                st.warning("⚠️ **Action Required:** Please set your institution name to enable student sharing.")
                
                with st.form("institution_form"):
                    institution_name = st.text_input(
                        "Institution Name:",
                        placeholder="Montessori School",
                        help="This enables secure student sharing with educators from your institution"
                    )
                    submitted = st.form_submit_button("Set Institution")
                    
                    if submitted and institution_name:
                        db = get_db()
                        if db and educator_id:
                            try:
                                success, auto_enabled = update_educator_institution(db, educator_id, institution_name)
                                if success:
                                    invalidate_educator_profile_cache(educator_id)
                                    if auto_enabled:
                                        st.success("✅ Institution set! 🚀 All educators now have institutions - enforcement automatically enabled!")
                                    else:
                                        st.success(f"✅ Institution set to: {institution_name}")
                                    st.rerun()
                                else:
                                    st.error("Failed to update institution")
                            finally:
                                db.close()
            
            # Educator Dashboard - Welcome and Cards
            educator_name = st.session_state.get('user_email', 'Educator').split('@')[0].title()
            st.markdown(f'<h2 style="margin-bottom: 1rem;">Welcome back, {educator_name}</h2>', unsafe_allow_html=True)
            
            # Institution badge (uses cached profile - no extra DB call)
            if educator_profile and educator_profile.get('institution_name'):
                enforcement_on = educator_profile.get('enforcement_on', False)
                status_icon = "🔒" if enforcement_on else "⏳"
                status_text = "Active" if enforcement_on else "Grace Period"
                st.markdown(f"""
                <div style="background-color: rgba(120, 154, 118, 0.08); border-left: 3px solid #789A76; 
                            padding: 0.5rem 1rem; margin-bottom: 1.5rem; border-radius: 4px; display: inline-block;">
                    <span style="font-size: 14px; opacity: 0.75;">{status_icon} <strong>Institution:</strong> {educator_profile['institution_name']} | <strong>Sharing Enforcement:</strong> {status_text}</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Welcome message - tools are now in sidebar for easy access
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(245, 240, 232, 0.6), rgba(235, 228, 216, 0.6)); 
                        border-radius: 16px; padding: 2rem; margin: 1rem 0 2rem 0; text-align: center;">
                <p style="font-size: 1.1rem; color: #5a5a5a; margin: 0;">
                    Use the sidebar to navigate between tools. Select a tool to begin your work.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # PD Expert Mode - restricted to authorized emails
            authorized_pd_emails = ["guideaichat@gmail.com", "ben@hmswairoa.net"]
            if st.session_state.get('user_email') in authorized_pd_emails:
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
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
    elif st.session_state.auth_mode == "imaginarium":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_img"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_imaginarium_interface()
    elif st.session_state.auth_mode == "school_admin_dashboard":
        # Back to dashboard button
        if st.button("← Back to Dashboard", key="back_school"):
            st.session_state.auth_mode = "dashboard_home"
            st.rerun()
        show_school_admin_dashboard()
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
    elif st.session_state.auth_mode == "contact":
        # Back button - go to previous page or login
        if st.session_state.get('logged_in'):
            if st.button("← Back to Dashboard", key="back_contact"):
                st.session_state.auth_mode = "dashboard_home"
                st.rerun()
        else:
            if st.button("← Back to Login", key="back_contact_login"):
                st.session_state.auth_mode = "login"
                st.rerun()
        show_contact_form()
    
# Main app logic continues here

# Footer with contact link - only show on homepage (login page)
if st.session_state.auth_mode == "login":
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns([1, 2, 1])
    with footer_col2:
        st.markdown(
            """
            <div style='text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem; margin-bottom: 1.5rem;'>
                <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em><br><br>
                Guide - Your prepared digital environment<br>
                Brought to you by Auxpery - <em>Gentle Technology for Thoughtful Education</em>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("📬 Contact Us", key="footer_contact", use_container_width=True):
            st.session_state.auth_mode = "contact"
            st.rerun()
