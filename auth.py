import streamlit as st
from database import get_db, create_user, authenticate_user, authenticate_student, get_user_by_email, get_student_by_username, create_student, check_login_rate_limit, record_login_attempt, clear_login_attempts, create_student_with_consent
import re
import requests
import os
from datetime import datetime, timedelta

PAYMENTS_SERVICE_URL = os.getenv('PAYMENTS_SERVICE_URL', 'http://localhost:3001')
PAYMENTS_API_SECRET = os.getenv('PAYMENTS_API_SECRET', '')

# Price IDs - use environment variables for flexibility between sandbox/live
# Set STRIPE_MONTHLY_PRICE_ID and STRIPE_ANNUAL_PRICE_ID in secrets for each environment
MONTHLY_PRICE_ID = os.getenv('STRIPE_MONTHLY_PRICE_ID', 'price_1Sd7RX8PGiRAuUvfzibxCNLV')
ANNUAL_PRICE_ID = os.getenv('STRIPE_ANNUAL_PRICE_ID', 'price_1SeSbY8PGiRAuUvf0xjZmMXK')

SUBSCRIPTION_CACHE_TTL = timedelta(minutes=5)
SUBSCRIPTION_STALE_TTL = timedelta(hours=1)

def get_api_headers():
    """Get headers for authenticated API calls to payments service"""
    return {'X-API-Secret': PAYMENTS_API_SECRET, 'Content-Type': 'application/json'}

def check_subscription_status(educator_id):
    """Check if educator has an active subscription (with fast cache and stale fallback)"""
    cache_key = f'subscription_cache_{educator_id}'
    cache_time_key = f'subscription_cache_time_{educator_id}'
    
    cached_data = st.session_state.get(cache_key)
    cached_time = st.session_state.get(cache_time_key)
    
    if cached_data and cached_time:
        age = datetime.now() - cached_time
        if age < SUBSCRIPTION_CACHE_TTL:
            return cached_data
    
    try:
        response = requests.get(
            f"{PAYMENTS_SERVICE_URL}/api/subscription-status/{educator_id}",
            headers=get_api_headers(),
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                result = data.get('data', {})
                st.session_state[cache_key] = result
                st.session_state[cache_time_key] = datetime.now()
                return result
        result = {'isActive': False, 'status': 'none'}
        st.session_state[cache_key] = result
        st.session_state[cache_time_key] = datetime.now()
        return result
    except Exception as e:
        print(f"Error checking subscription: {e}")
        if cached_data and cached_time:
            age = datetime.now() - cached_time
            if age < SUBSCRIPTION_STALE_TTL:
                return cached_data
        return {'isActive': False, 'status': 'error'}

def invalidate_subscription_cache(educator_id=None):
    """Invalidate subscription cache after payment or subscription changes"""
    if educator_id:
        cache_key = f'subscription_cache_{educator_id}'
        cache_time_key = f'subscription_cache_time_{educator_id}'
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        if cache_time_key in st.session_state:
            del st.session_state[cache_time_key]

def create_checkout_session(price_id, educator_id, email):
    """Create a Stripe checkout session"""
    try:
        print(f"Creating checkout: priceId={price_id}, educatorId={educator_id}, email={email}")
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/create-checkout-session",
            json={'priceId': price_id, 'educatorId': educator_id, 'email': email},
            headers=get_api_headers(),
            timeout=10
        )
        print(f"Checkout response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('url')
            else:
                print(f"Checkout failed: {data.get('error')}")
                return None
        else:
            print(f"Checkout request failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return None

def create_portal_session(educator_id):
    """Create a Stripe billing portal session"""
    try:
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/create-portal-session",
            json={'educatorId': educator_id},
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('url')
        return None
    except Exception as e:
        print(f"Error creating portal session: {e}")
        return None

def cancel_subscription(educator_id):
    """Cancel subscription at the end of the billing period"""
    try:
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/subscription/cancel",
            json={'educatorId': educator_id},
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                invalidate_subscription_cache(educator_id)
                return data.get('data', {})
        return None
    except Exception as e:
        print(f"Error cancelling subscription: {e}")
        return None

def reactivate_subscription(educator_id):
    """Reactivate a subscription that was set to cancel"""
    try:
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/subscription/reactivate",
            json={'educatorId': educator_id},
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                invalidate_subscription_cache(educator_id)
                return data.get('data', {})
        return None
    except Exception as e:
        print(f"Error reactivating subscription: {e}")
        return None

def validate_signup_token(token):
    """Validate a signup token from the marketing site payment flow"""
    try:
        response = requests.get(
            f"{PAYMENTS_SERVICE_URL}/api/public/validate-token/{token}",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
        return None
    except Exception as e:
        print(f"Error validating signup token: {e}")
        return None

def redeem_signup_token(token, user_id, email):
    """Redeem a signup token after user account creation"""
    try:
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/redeem-token",
            json={'token': token, 'userId': user_id, 'email': email},
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
        elif response.status_code == 403:
            print(f"Email mismatch when redeeming token: {response.json().get('error')}")
        return None
    except Exception as e:
        print(f"Error redeeming signup token: {e}")
        return None

def show_pricing_page():
    """Display the subscription pricing page"""
    st.markdown("""
    <style>
    .pricing-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem 0;
    }
    .pricing-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .pricing-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        border: 2px solid #dee2e6;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .pricing-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .pricing-card.recommended {
        border-color: #789A76;
        background: linear-gradient(135deg, #f0f7ef 0%, #e8f5e8 100%);
    }
    .price-amount {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
    }
    .price-period {
        color: #666;
        font-size: 1rem;
    }
    .feature-list {
        text-align: left;
        margin: 1.5rem 0;
    }
    .feature-item {
        padding: 0.5rem 0;
        border-bottom: 1px solid #eee;
    }
    .savings-badge {
        background: #789A76;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="pricing-header">
        <h1>🌱 Start Your Guide Journey</h1>
        <p style="font-size: 1.1rem; color: #666; max-width: 600px; margin: 0 auto;">
            AI-powered Montessori curriculum companion with Australian Curriculum V9 integration. 
            Start your 14-day free trial today.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    educator_id = st.session_state.get('user_id')
    email = st.session_state.get('user_email')
    
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <h3>Monthly</h3>
            <div class="price-amount">$15<span class="price-period">/month</span></div>
            <p style="color: #2E8B57; font-weight: 500;">14-day free trial included</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Start Free Trial", key="monthly_btn", use_container_width=True, type="primary"):
            with st.spinner("Preparing checkout..."):
                checkout_url = create_checkout_session(MONTHLY_PRICE_ID, educator_id, email)
                if checkout_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to secure checkout...")
                else:
                    st.error("Unable to create checkout session. Please try again.")
    
    with col2:
        st.markdown("""
        <div class="pricing-card recommended">
            <span class="savings-badge">💰 2 Months Free</span>
            <h3>Annual</h3>
            <div class="price-amount">$150<span class="price-period">/year</span></div>
            <p style="color: #2E8B57; font-weight: 500;">Best value - save $30/year</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Choose Annual", key="annual_btn", use_container_width=True, type="secondary"):
            with st.spinner("Preparing checkout..."):
                checkout_url = create_checkout_session(ANNUAL_PRICE_ID, educator_id, email)
                if checkout_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to secure checkout...")
                else:
                    st.error("Unable to create checkout session. Please try again.")
    
    st.markdown("---")
    
    st.markdown("""
    ### What's Included
    
    ✅ **AI-Powered Lesson Planning** - Create detailed, age-appropriate lessons in minutes  
    ✅ **Australian Curriculum V9 Integration** - Aligned content descriptors and cross-curricular priorities  
    ✅ **Montessori Philosophy** - Grounded in Cosmic Education principles  
    ✅ **Student Dashboard** - Track student progress and activities  
    ✅ **Great Stories Creator** - Generate engaging narratives for new concepts  
    ✅ **Planning Notes** - Save and organize your lesson plans  
    ✅ **Child Safety Features** - Content monitoring and safety alerts  
    ✅ **Australian Privacy Act Compliant** - Your data is protected  
    """)
    
    st.markdown("""
    ---
    <p style="text-align: center; color: #666; font-size: 0.9rem;">
        Questions? Contact us at <a href="mailto:support@auxpery.com.au">support@auxpery.com.au</a>
    </p>
    """, unsafe_allow_html=True)

def show_billing_portal_button():
    """Show button to access Stripe billing portal"""
    educator_id = st.session_state.get('user_id')
    if st.button("💳 Manage Subscription", key="billing_portal_btn"):
        with st.spinner("Opening billing portal..."):
            portal_url = create_portal_session(educator_id)
            if portal_url:
                st.markdown(f'<meta http-equiv="refresh" content="0;url={portal_url}">', unsafe_allow_html=True)
                st.info("Redirecting to billing portal...")
            else:
                st.error("Unable to open billing portal. Please try again.")

def show_account_settings():
    """Display account settings including subscription management and deactivation"""
    educator_id = st.session_state.get('user_id')
    
    if not educator_id:
        return
    
    sub_status = check_subscription_status(educator_id)
    
    st.markdown("### Subscription")
    
    if sub_status.get('isActive'):
        plan = sub_status.get('plan', 'monthly').capitalize()
        status = sub_status.get('status', 'active').capitalize()
        
        if sub_status.get('cancelAtPeriodEnd'):
            period_end = sub_status.get('currentPeriodEnd')
            if period_end:
                try:
                    end_date = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                    formatted_date = end_date.strftime('%B %d, %Y')
                except:
                    formatted_date = str(period_end)[:10]
            else:
                formatted_date = "the end of your billing period"
            
            st.warning(f"Your subscription is set to cancel on **{formatted_date}**. You'll have access until then.")
            
            if st.button("Undo Cancellation", key="reactivate_btn", type="primary"):
                with st.spinner("Reactivating subscription..."):
                    result = reactivate_subscription(educator_id)
                    if result:
                        st.success("Your subscription has been reactivated!")
                        st.rerun()
                    else:
                        st.error("Unable to reactivate. Please try again or contact support.")
        else:
            st.success(f"**{plan}** plan - {status}")
            
            if st.button("💳 Manage Billing", key="manage_billing_btn"):
                with st.spinner("Opening billing portal..."):
                    portal_url = create_portal_session(educator_id)
                    if portal_url:
                        st.markdown(f'<meta http-equiv="refresh" content="0;url={portal_url}">', unsafe_allow_html=True)
                        st.info("Redirecting to billing portal...")
                    else:
                        st.error("Unable to open billing portal. Please try again.")
    
    st.markdown("---")
    
    with st.expander("Account Actions", expanded=False):
        st.markdown("#### Deactivate Account")
        
        if sub_status.get('cancelAtPeriodEnd'):
            st.info("Your account is already set to deactivate at the end of your billing period.")
        elif sub_status.get('isActive'):
            st.markdown("""
            If you deactivate your account:
            - Your subscription will be cancelled at the end of your current billing period
            - You'll keep full access until then
            - Your data will be preserved and you can reactivate anytime
            """)
            
            confirm_text = st.text_input(
                "Type 'DEACTIVATE' to confirm",
                key="deactivate_confirm",
                placeholder="Type DEACTIVATE"
            )
            
            if st.button("Deactivate Account", key="deactivate_btn", type="secondary"):
                if confirm_text == "DEACTIVATE":
                    with st.spinner("Processing deactivation..."):
                        result = cancel_subscription(educator_id)
                        if result:
                            period_end = result.get('currentPeriodEnd')
                            if period_end:
                                try:
                                    end_date = datetime.fromisoformat(str(period_end).replace('Z', '+00:00'))
                                    formatted_date = end_date.strftime('%B %d, %Y')
                                except:
                                    formatted_date = "the end of your billing period"
                            else:
                                formatted_date = "the end of your billing period"
                            st.success(f"Your account is set to deactivate on {formatted_date}. You can undo this anytime before then.")
                            st.rerun()
                        else:
                            st.error("Unable to process deactivation. Please try again or contact support.")
                else:
                    st.error("Please type 'DEACTIVATE' exactly to confirm.")
        else:
            st.info("No active subscription to cancel.")

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength - requires 12+ chars with complexity"""
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
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
                        # Check rate limiting before authentication
                        is_locked, remaining_seconds, failed_count = check_login_rate_limit(db, email)
                        if is_locked:
                            minutes_remaining = remaining_seconds // 60 + 1
                            st.error(f"Account temporarily locked due to too many failed attempts. Please try again in {minutes_remaining} minute(s).")
                            return
                        
                        user = authenticate_user(db, email, password)
                        if user:
                            # Clear failed attempts on successful login
                            clear_login_attempts(db, email)
                            st.session_state.user_id = user.id
                            st.session_state.user_type = user.user_type
                            st.session_state.user_name = user.full_name
                            st.session_state.user_email = user.email
                            st.session_state.authenticated = True
                            st.session_state.is_student = False
                            # Clear any existing auth_mode to ensure clean state
                            if 'auth_mode' in st.session_state:
                                del st.session_state['auth_mode']
                            st.success(f"Welcome back, {user.full_name}!")
                            st.rerun()
                        else:
                            # Record failed attempt
                            record_login_attempt(db, email, attempt_type='educator', success=False)
                            attempts_remaining = 5 - failed_count - 1
                            if attempts_remaining > 0:
                                st.error(f"Invalid email or password. {attempts_remaining} attempt(s) remaining before lockout.")
                            else:
                                st.error("Invalid email or password. Account will be locked on next failed attempt.")
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
                        # Check rate limiting before authentication
                        is_locked, remaining_seconds, failed_count = check_login_rate_limit(db, username)
                        if is_locked:
                            minutes_remaining = remaining_seconds // 60 + 1
                            st.error(f"Account temporarily locked due to too many failed attempts. Please try again in {minutes_remaining} minute(s).")
                            return
                        
                        student = authenticate_student(db, username, password)
                        if student:
                            # Clear failed attempts on successful login
                            clear_login_attempts(db, username)
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
                            # Record failed attempt
                            record_login_attempt(db, username, attempt_type='student', success=False)
                            attempts_remaining = 5 - failed_count - 1
                            if attempts_remaining > 0:
                                st.error(f"Invalid username or password. {attempts_remaining} attempt(s) remaining before lockout.")
                            else:
                                st.error("Invalid username or password. Account will be locked on next failed attempt.")
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
        password = st.text_input("Password", type="password", help="Minimum 12 characters with uppercase, lowercase, and number")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        agree_terms = st.checkbox("I have read and agree to the Terms and Conditions", value=False)
        
        submit = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit:
            # Validation
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif not agree_terms:
                st.error("Please agree to the Terms and Conditions to continue")
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
        password = st.text_input("Password", type="password", help="Minimum 12 characters with uppercase, lowercase, and number")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        st.markdown("---")
        st.markdown("### Guardian Consent Attestation")
        st.markdown("*Required under Australian Privacy Act 1988 (APP 3)*")
        consent_confirmed = st.checkbox(
            "I confirm that I have obtained parental/guardian consent for this student to use Guide in accordance with my institution's policies and the Guide Privacy Policy.",
            value=False,
            help="You must confirm guardian consent before creating a student account"
        )
        
        submit = st.form_submit_button("Create Student Account", use_container_width=True)
        
        if submit:
            if not consent_confirmed:
                st.error("You must confirm guardian consent before creating a student account")
            elif not all([full_name, username, password, confirm_password]):
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
                            # Create student with consent atomically (APP 3 compliance)
                            # This ensures consent is recorded in the same transaction as account creation
                            consent_text = "I confirm that I have obtained parental/guardian consent for this student to use Guide in accordance with my institution's policies and the Guide Privacy Policy."
                            
                            student, consent = create_student_with_consent(
                                db, 
                                username=username, 
                                password=password, 
                                full_name=full_name, 
                                educator_id=st.session_state.user_id, 
                                age_group=age_group,
                                consent_attestation_text=consent_text
                            )
                            
                            if student and consent:
                                # Record additional privacy consents
                                from database import record_consent
                                record_consent(db, student_id=student.id, consent_type='data_collection', 
                                             granted_by_id=st.session_state.user_id, policy_version="1.0")
                                record_consent(db, student_id=student.id, consent_type='overseas_transfer',
                                             granted_by_id=st.session_state.user_id, policy_version="1.0")
                                
                                st.success(f"Student account created successfully for {full_name}!")
                                st.info(f"Username: {username}")
                                st.info("The student can now log in using their username and password.")
                            else:
                                st.error("Failed to create student account. Please try again.")
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