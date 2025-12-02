import streamlit as st
from database import get_db, create_user, authenticate_user, authenticate_student, get_user_by_email, get_student_by_username, create_student, check_subscription_active
from datetime import datetime
import re

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Password is valid"

def login_page():
    """Display login page for educators and students"""
    st.markdown('<h2 style="text-align: center; color: #2E8B57;">🔐 Login to Your Account</h2>', unsafe_allow_html=True)
    
    # Choose login type
    login_type = st.selectbox("I am a:", ["Educator", "Student"])
    
    if login_type == "Educator":
        with st.form("educator_login"):
            st.markdown("### Educator Login")
            email = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                else:
                    db = get_db()
                    if not db:
                        st.error("Authentication is not available. Database connection required.")
                        return
                    try:
                        user = authenticate_user(db, email, password)
                        if user:
                            st.session_state.user_id = user.id
                            st.session_state.user_type = user.user_type
                            st.session_state.user_name = user.full_name
                            st.session_state.user_email = user.email
                            st.session_state.authenticated = True
                            st.session_state.is_student = False
                            
                            # Store subscription information
                            st.session_state.subscription_status = user.subscription_status or 'inactive'
                            st.session_state.subscription_plan = user.subscription_plan
                            st.session_state.subscription_end_date = user.subscription_end_date
                            st.session_state.has_active_subscription = check_subscription_active(db, user.id)
                            
                            # Clear any existing auth_mode to ensure clean state
                            if 'auth_mode' in st.session_state:
                                del st.session_state['auth_mode']
                            st.success(f"Welcome back, {user.full_name}!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
                    finally:
                        if db:
                            db.close()
    
    else:  # Student login
        with st.form("student_login"):
            st.markdown("### Student Login")
            username = st.text_input("Username", placeholder="your_username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    db = get_db()
                    if not db:
                        st.error("Authentication is not available. Database connection required.")
                        return
                    try:
                        student = authenticate_student(db, username, password)
                        if student:
                            st.session_state.user_id = student.id
                            st.session_state.user_type = "student"
                            st.session_state.user_name = student.full_name
                            st.session_state.username = student.username
                            st.session_state.educator_id = student.educator_id
                            st.session_state.age_group = student.age_group
                            st.session_state.authenticated = True
                            st.session_state.is_student = True
                            # Clear any existing auth_mode to prevent educator features from showing
                            if 'auth_mode' in st.session_state:
                                del st.session_state['auth_mode']
                            st.success(f"Welcome back, {student.full_name}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    finally:
                        if db:
                            db.close()

def signup_page():
    """Display signup page for new educators"""
    st.markdown('<h2 style="text-align: center; color: #2E8B57;">📝 Create Your Educator Account</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center;">Join our Montessori educational planning community</p>', unsafe_allow_html=True)
    
    # Privacy notice before signup
    st.info("📋 **Privacy Notice:** By creating an account, you agree to our data collection practices. Please read our Terms and Conditions for details on how we handle your information.")
    
    # Link to terms and conditions
    if st.button("📋 View Terms & Conditions", key="signup_privacy_link"):
        st.session_state.auth_mode = "privacy_policy"
        st.rerun()
    
    with st.form("educator_signup"):
        st.markdown("### Create New Account")
        full_name = st.text_input("Full Name", placeholder="Your full name")
        email = st.text_input("Email", placeholder="your.email@example.com")
        user_type = st.selectbox("I am a:", ["Educator"])
        user_type = "educator"  # Normalize to single type
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        # Consent checkboxes
        st.markdown("---")
        st.markdown("### Privacy & Consent")
        
        consent_data_collection = st.checkbox(
            "I understand that Guide collects and stores my personal information (name, email, usage data) to provide educational services.",
            value=False
        )
        
        consent_overseas_transfer = st.checkbox(
            "I consent to my data being sent to OpenAI (United States) for AI processing. I understand Australian privacy laws may not apply to this overseas data transfer.",
            value=False
        )
        
        consent_privacy_policy = st.checkbox(
            "I have read and agree to the Terms of Use and Privacy Policy.",
            value=False
        )
        
        submit = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit:
            # Validation
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif not consent_data_collection:
                st.error("Please acknowledge our data collection practices to continue")
            elif not consent_overseas_transfer:
                st.error("Please consent to overseas data transfer (required for AI functionality)")
            elif not consent_privacy_policy:
                st.error("Please read and agree to the Terms of Use and Privacy Policy")
            else:
                valid_password, password_message = validate_password(password)
                if not valid_password:
                    st.error(password_message)
                else:
                    db = get_db()
                    if not db:
                        st.error("Account creation is not available. Database connection required.")
                        return
                    try:
                        # Check if user already exists
                        existing_user = get_user_by_email(db, email)
                        if existing_user:
                            st.error("An account with this email already exists")
                        else:
                            # Create new user
                            user = create_user(db, email, password, full_name, user_type)
                            
                            # Record consent for auditing (APP 5/8 compliance)
                            from database import record_consent
                            record_consent(db, user_id=user.id, consent_type='data_collection', policy_version="1.0")
                            record_consent(db, user_id=user.id, consent_type='overseas_transfer', policy_version="1.0")
                            record_consent(db, user_id=user.id, consent_type='privacy_policy', policy_version="1.0")
                            
                            st.success(f"Account created successfully! Welcome, {full_name}!")
                            st.session_state.user_id = user.id
                            st.session_state.user_type = user.user_type
                            st.session_state.user_name = user.full_name
                            st.session_state.user_email = user.email
                            st.session_state.authenticated = True
                            st.session_state.is_student = False
                            st.rerun()
                    finally:
                        if db:
                            db.close()

def create_student_page():
    """Allow educators to create student accounts"""
    if not st.session_state.get('authenticated') or st.session_state.get('is_student'):
        st.error("Access denied. Only educators can create student accounts.")
        return
    
    st.markdown('<h2 style="text-align: center; color: #2E8B57;">👨‍🎓 Create Student Account</h2>', unsafe_allow_html=True)
    
    with st.form("create_student"):
        st.markdown("### Add New Student")
        full_name = st.text_input("Student's Full Name", placeholder="Student's full name")
        username = st.text_input("Username", placeholder="student_username", help="This will be used for student login")
        age_group = st.selectbox("Age Group", ["12-15", "9-12", "6-9", "3-6"], 
                                 format_func=lambda x: {
                                     "12-15": "Adolescent (12-15)",
                                     "9-12": "Upper Primary (9-12)",
                                     "6-9": "Lower Primary (6-9)",
                                     "3-6": "Early Years (3-6)"
                                 }[x])
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        submit = st.form_submit_button("Create Student Account", use_container_width=True)
        
        if submit:
            if not all([full_name, username, password, confirm_password]):
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                valid_password, password_message = validate_password(password)
                if not valid_password:
                    st.error(password_message)
                else:
                    db = get_db()
                    if not db:
                        st.error("Student account creation is not available. Database connection required.")
                        return
                    try:
                        # Check if username already exists
                        existing_student = get_student_by_username(db, username)
                        if existing_student:
                            st.error("A student with this username already exists")
                        else:
                            # Create new student
                            student = create_student(
                                db, 
                                username, 
                                password, 
                                full_name, 
                                st.session_state.user_id, 
                                age_group
                            )
                            
                            # Record parental consent for auditing (APP 3/5 compliance)
                            from database import record_parental_consent, record_consent
                            record_parental_consent(
                                db, 
                                student_id=student.id,
                                educator_id=st.session_state.user_id,
                                consent_method='educator_confirmed'
                            )
                            
                            # Record privacy consents for student
                            record_consent(db, student_id=student.id, consent_type='data_collection', 
                                         granted_by_id=st.session_state.user_id, policy_version="1.0")
                            record_consent(db, student_id=student.id, consent_type='overseas_transfer',
                                         granted_by_id=st.session_state.user_id, policy_version="1.0")
                            
                            st.success(f"Student account created successfully for {full_name}!")
                            st.info(f"Username: {username}")
                            st.info("The student can now log in using their username and password.")
                    finally:
                        if db:
                            db.close()

def logout():
    """
    Log out current user - MANUAL LOGOUT ONLY
    
    This function is ONLY called when the user explicitly clicks the logout button.
    There are no automatic logout triggers, timeouts, or force logouts in this application.
    Session state persists indefinitely like ChatGPT until this function is called.
    """
    # Clear all authentication-related session state
    for key in ['user_id', 'user_type', 'user_name', 'user_email', 'username', 
                'educator_id', 'age_group', 'authenticated', 'is_student',
                'subscription_status', 'subscription_plan', 'subscription_end_date', 
                'has_active_subscription']:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear messages as well
    if 'messages' in st.session_state:
        st.session_state.messages = []
    
    st.success("You have been logged out successfully!")
    st.rerun()

def check_subscription_required():
    """
    Check if user has active subscription and show appropriate message.
    Returns True if user has access, False otherwise.
    Handles grace periods for past_due and cancelled-but-not-expired states.
    """
    if st.session_state.get('is_student'):
        return True  # Students don't need subscriptions
    
    if not st.session_state.get('authenticated'):
        return False
    
    has_subscription = st.session_state.get('has_active_subscription', False)
    subscription_status = st.session_state.get('subscription_status', 'inactive')
    end_date = st.session_state.get('subscription_end_date')
    
    # Show warning for past_due but still allow access
    if subscription_status == 'past_due':
        st.warning("⚠️ Your subscription payment is past due. Please update your payment method at auxpery.com.au to avoid interruption.")
        return True  # Still allow access during grace period
    
    # Check if cancelled but still within paid period
    if subscription_status == 'cancelled' and end_date:
        if end_date > datetime.now():
            remaining_days = (end_date - datetime.now()).days
            st.info(f"📋 Your subscription has been cancelled. You have access until {end_date.strftime('%d/%m/%Y')} ({remaining_days} days remaining).")
            return True  # Allow access until end date
    
    if not has_subscription:
        st.info("📋 Subscribe to Guide to unlock all features. Visit auxpery.com.au to get started.")
        return False
    
    return True

def get_subscription_display():
    """
    Get subscription status display info for the dashboard.
    Returns a dictionary with status info.
    """
    if st.session_state.get('is_student'):
        return None
    
    status = st.session_state.get('subscription_status', 'inactive')
    plan = st.session_state.get('subscription_plan')
    end_date = st.session_state.get('subscription_end_date')
    
    status_icons = {
        'active': '✅',
        'past_due': '⚠️',
        'cancelled': '❌',
        'inactive': '📋'
    }
    
    status_labels = {
        'active': 'Active',
        'past_due': 'Payment Past Due',
        'cancelled': 'Cancelled',
        'inactive': 'No Subscription'
    }
    
    plan_labels = {
        'monthly': 'Monthly ($12/month)',
        'yearly': 'Yearly ($144/year)'
    }
    
    info = {
        'icon': status_icons.get(status, '📋'),
        'status': status_labels.get(status, 'Unknown'),
        'plan': plan_labels.get(plan, 'N/A') if plan else 'N/A',
        'end_date': end_date.strftime('%d/%m/%Y') if end_date else 'N/A',
        'is_active': status == 'active'
    }
    
    return info

def show_user_info():
    """Display current user information"""
    if st.session_state.get('authenticated'):
        if st.session_state.get('is_student'):
            st.sidebar.markdown(f"**Student:** {st.session_state.user_name}")
            st.sidebar.markdown(f"**Username:** {st.session_state.username}")
            if st.session_state.get('age_group'):
                st.sidebar.markdown(f"**Age Group:** {st.session_state.age_group}")
        else:
            st.sidebar.markdown(f"**{st.session_state.user_type.title()}:** {st.session_state.user_name}")
            st.sidebar.markdown(f"**Email:** {st.session_state.user_email}")
            
            # Show subscription status for educators
            sub_info = get_subscription_display()
            if sub_info:
                st.sidebar.markdown("---")
                st.sidebar.markdown(f"**Subscription:** {sub_info['icon']} {sub_info['status']}")
                if sub_info['is_active']:
                    st.sidebar.markdown(f"**Plan:** {sub_info['plan']}")
                    st.sidebar.markdown(f"**Renews:** {sub_info['end_date']}")
        
        if st.sidebar.button("🚪 Logout"):
            logout()