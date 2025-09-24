import streamlit as st
from database import get_db, create_user, authenticate_user, authenticate_student, get_user_by_email, get_student_by_username, create_student
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
    
    with st.form("educator_signup"):
        st.markdown("### Create New Account")
        full_name = st.text_input("Full Name", placeholder="Your full name")
        email = st.text_input("Email", placeholder="your.email@example.com")
        user_type = st.selectbox("I am a:", ["Educator"])
        user_type = "educator"  # Normalize to single type
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        submit = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit:
            # Validation
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            elif password != confirm_password:
                st.error("Passwords do not match")
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
        age_group = st.selectbox("Age Group", ["3-6", "6-9", "9-12", "12-15"], 
                                 format_func=lambda x: {
                                     "3-6": "Early Years (3-6)",
                                     "6-9": "Lower Primary (6-9)", 
                                     "9-12": "Upper Primary (9-12)",
                                     "12-15": "Adolescent (12-15)"
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
                            st.success(f"Student account created successfully for {full_name}!")
                            st.info(f"Username: {username}")
                            st.info("The student can now log in using their username and password.")
                    finally:
                        if db:
                            db.close()

def logout():
    """Log out current user"""
    # Clear all authentication-related session state
    for key in ['user_id', 'user_type', 'user_name', 'user_email', 'username', 
                'educator_id', 'age_group', 'authenticated', 'is_student']:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear messages as well
    if 'messages' in st.session_state:
        st.session_state.messages = []
    
    st.success("You have been logged out successfully!")
    st.rerun()

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
        
        if st.sidebar.button("🚪 Logout"):
            logout()