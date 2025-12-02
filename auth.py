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
    # Ensure login defaults to Educator on fresh entry
    if 'login_user_type' not in st.session_state:
        st.session_state.login_user_type = "Educator"
    
    # Back link - also reset login type when going back
    if st.button("Back", key="login_back"):
        st.session_state.auth_mode = "landing"
        st.session_state.login_user_type = "Educator"
        st.rerun()
    
    # Minimal title
    st.markdown('<h2 style="text-align: center; margin: 0 0 4px 0; color: #333333; font-size: 24px; font-weight: 500;">Login</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; margin: 0 0 24px 0; color: #666666; font-size: 14px;">Access your account</p>', unsafe_allow_html=True)
    
    # Toggle pills for Educator/Student
    st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
    _, pill_col, _ = st.columns([1, 2, 1])
    with pill_col:
        col_edu, col_stu = st.columns(2)
        with col_edu:
            if st.button("Educator", 
                        key="toggle_educator",
                        use_container_width=True,
                        type="primary" if st.session_state.login_user_type == "Educator" else "secondary"):
                st.session_state.login_user_type = "Educator"
                st.rerun()
        with col_stu:
            if st.button("Student",
                        key="toggle_student", 
                        use_container_width=True,
                        type="primary" if st.session_state.login_user_type == "Student" else "secondary"):
                st.session_state.login_user_type = "Student"
                st.rerun()
    
    st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
    
    # Form container - render based on session state
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        if st.session_state.login_user_type == "Educator":
            with st.form("educator_login"):
                email = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password")
                
                st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")
                
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
                                
                                st.session_state.subscription_status = user.subscription_status or 'inactive'
                                st.session_state.subscription_plan = user.subscription_plan
                                st.session_state.subscription_end_date = user.subscription_end_date
                                st.session_state.has_active_subscription = check_subscription_active(db, user.id)
                                
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
                username = st.text_input("Username", placeholder="your_username")
                password = st.text_input("Password", type="password")
                
                st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")
                
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
                                if 'auth_mode' in st.session_state:
                                    del st.session_state['auth_mode']
                                st.success(f"Welcome back, {student.full_name}!")
                                st.rerun()
                            else:
                                st.error("Invalid username or password")
                        finally:
                            if db:
                                db.close()
        
        # Secondary links below form
        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 12px; color: #888888; margin: 0;">Don\'t have an account?</p>', unsafe_allow_html=True)
        st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
        
        if st.button("Create an account", key="login_to_signup", use_container_width=True):
            st.session_state.auth_mode = "signup"
            st.rerun()
        
        # Footer
        st.markdown('<div style="height: 48px;"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; font-size: 12px; color: #888888; line-height: 1.8; max-width: 480px; margin: 0 auto;">
            <p style="font-style: italic; margin: 0 0 12px 0; color: #888888;">"The child is both a hope and a promise for mankind." — Maria Montessori</p>
            <p style="margin: 0 0 4px 0;">Guide – Your prepared digital environment</p>
            <p style="color: #999999; font-size: 11px; margin: 0;">Brought to you by Auxpery – Gentle Technology for Thoughtful Education</p>
        </div>
        """, unsafe_allow_html=True)

def signup_page():
    """Display signup page for new educators"""
    # Back link
    if st.button("Back", key="signup_back"):
        st.session_state.auth_mode = "landing"
        st.rerun()
    
    # Minimal title
    st.markdown('<h2 style="text-align: center; margin: 0 0 4px 0; color: #333333; font-size: 24px; font-weight: 500;">Create Account</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; margin: 0 0 24px 0; color: #666666; font-size: 14px;">Join our Montessori educational community</p>', unsafe_allow_html=True)
    
    # Form container
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("educator_signup"):
            full_name = st.text_input("Full Name", placeholder="Your full name")
            email = st.text_input("Email", placeholder="your.email@example.com")
            user_type = "educator"  # Normalize to single type
            password = st.text_input("Password", type="password", help="Minimum 6 characters")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            # Consent checkboxes
            st.markdown('<div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #E0E0E0;"></div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size: 14px; font-weight: 500; color: #333333; margin-bottom: 16px;">Privacy & Consent</p>', unsafe_allow_html=True)
            
            consent_data_collection = st.checkbox(
                "I understand that Guide collects and stores my personal information to provide educational services.",
                value=False
            )
            
            consent_overseas_transfer = st.checkbox(
                "I consent to my data being processed by OpenAI (United States) for AI features.",
                value=False
            )
            
            consent_privacy_policy = st.checkbox(
                "I have read and agree to the Terms of Use and Privacy Policy.",
                value=False
            )
            
            st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
        
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
                            
                            # Send welcome email
                            try:
                                from email_service import get_email_service
                                email_service = get_email_service()
                                email_service.send_welcome_email(email, full_name)
                            except Exception as e:
                                print(f"Welcome email error: {str(e)}")
                            
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
        
        # Footer
        st.markdown('<div style="height: 48px;"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; font-size: 12px; color: #888888; line-height: 1.8; max-width: 480px; margin: 0 auto;">
            <p style="font-style: italic; margin: 0 0 12px 0; color: #888888;">"The child is both a hope and a promise for mankind." — Maria Montessori</p>
            <p style="margin: 0 0 4px 0;">Guide – Your prepared digital environment</p>
            <p style="color: #999999; font-size: 11px; margin: 0;">Brought to you by Auxpery – Gentle Technology for Thoughtful Education</p>
        </div>
        """, unsafe_allow_html=True)

def create_student_page():
    """Allow educators to create student accounts"""
    if not st.session_state.get('authenticated') or st.session_state.get('is_student'):
        st.error("Access denied. Only educators can create student accounts.")
        return
    
    st.markdown('<h2 style="text-align: center; color: #333333; font-size: 28px; font-weight: 500; margin: 30px 0;">Create Student Account</h2>', unsafe_allow_html=True)
    
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
            st.info(f"Your subscription has been cancelled. You have access until {end_date.strftime('%d/%m/%Y')} ({remaining_days} days remaining).")
            return True  # Allow access until end date
    
    if not has_subscription:
        st.info("Subscribe to Guide to unlock all features. Visit auxpery.com.au to get started.")
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
        'active': 'Active',
        'past_due': 'Past Due',
        'cancelled': 'Cancelled',
        'inactive': 'Inactive'
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
        'icon': '',
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