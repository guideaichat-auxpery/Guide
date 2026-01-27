import streamlit as st
import logging
import sys

logger = logging.getLogger('auth')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)

from database import (
    get_db, create_user, authenticate_user, authenticate_student, 
    get_user_by_email, get_student_by_username, create_student, 
    check_login_rate_limit, record_login_attempt, clear_login_attempts, 
    create_student_with_consent, create_persistent_session, 
    validate_persistent_session, invalidate_persistent_session,
    invalidate_all_user_sessions
)
import re
import os
import requests
import json
from datetime import datetime, timedelta
import extra_streamlit_components as stx

import stripe_client

SESSION_COOKIE_NAME = "guide_session"
EDUCATOR_SESSION_HOURS = 24
STUDENT_SESSION_HOURS = 8

def get_cookie_manager():
    """Get a cookie manager instance (stored in session_state to persist across reruns)"""
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager

PAYMENTS_SERVICE_URL = os.getenv('PAYMENTS_SERVICE_URL', 'http://localhost:3001')
PAYMENTS_API_SECRET = os.getenv('PAYMENTS_API_SECRET', '')

SUBSCRIPTION_CACHE_TTL = timedelta(seconds=30)


def set_session_cookie(token: str, hours: int = 24):
    """Set a session cookie using CookieManager from extra-streamlit-components"""
    try:
        cookie_manager = get_cookie_manager()
        expires = datetime.utcnow() + timedelta(hours=hours)
        cookie_manager.set(SESSION_COOKIE_NAME, token, expires_at=expires)
        print(f"[SESSION] Cookie set for {hours} hours")
    except Exception as e:
        print(f"[SESSION] Error setting cookie: {str(e)}")


def clear_session_cookie():
    """Clear the session cookie using CookieManager"""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete(SESSION_COOKIE_NAME)
        print("[SESSION] Cookie cleared")
    except Exception as e:
        print(f"[SESSION] Error clearing cookie: {str(e)}")


def restore_session_from_token(token: str):
    """Restore user session from a valid token. Returns True if successful."""
    logger.info("[SESSION RESTORE] Attempting to restore session from token")
    if not token:
        logger.info("[SESSION RESTORE] No token provided")
        return False
    
    db = get_db()
    if not db:
        logger.error("[SESSION RESTORE] Could not get database connection")
        return False
    
    try:
        session_data = validate_persistent_session(db, token)
        if not session_data:
            logger.info("[SESSION RESTORE] Invalid session token")
            return False
        
        user_type = session_data.get('user_type')
        logger.info(f"[SESSION RESTORE] Session data found, user_type={user_type}")
        
        if user_type == 'educator' and session_data.get('user_id'):
            from database import User
            user = db.query(User).filter(User.id == session_data['user_id']).first()
            if user and user.is_active:
                logger.info(f"[SESSION RESTORE] User found: {user.email}, is_admin={user.is_admin}")
                st.session_state.user_id = user.id
                st.session_state.user_type = user.user_type
                st.session_state.user_name = user.full_name
                st.session_state.user_email = user.email
                st.session_state.authenticated = True
                st.session_state.is_student = False
                # CRITICAL: Explicit boolean conversion to handle any type issues
                raw_is_admin = user.is_admin if hasattr(user, 'is_admin') else False
                st.session_state.is_admin = bool(raw_is_admin) if raw_is_admin else False
                st.session_state.user_role = getattr(user, 'role', 'individual')
                st.session_state.school_id = getattr(user, 'school_id', None)
                st.session_state.session_token = token
                
                logger.info(f"[SESSION RESTORE] Session state is_admin set to: {st.session_state.is_admin}")
                
                if st.session_state.is_admin:
                    logger.info("[SESSION RESTORE] ADMIN PATH - setting admin subscription status")
                    st.session_state.subscription_verified = True
                    st.session_state.subscription_active = True
                    st.session_state.subscription_status = 'admin'
                    st.session_state.subscription_plan = 'admin'
                else:
                    # Check if this is a school educator - use school subscription
                    if st.session_state.get('school_id') and st.session_state.get('user_role') in ('school_admin', 'school_educator'):
                        from database import get_school_by_id, is_school_subscription_active
                        school = get_school_by_id(db, st.session_state.school_id)
                        if school and is_school_subscription_active(school):
                            st.session_state.subscription_verified = True
                            st.session_state.subscription_active = True
                            st.session_state.subscription_status = school.subscription_status or 'active'
                            st.session_state.subscription_plan = 'school'
                        else:
                            st.session_state.subscription_verified = True
                            st.session_state.subscription_active = False
                            st.session_state.subscription_status = 'inactive'
                            st.session_state.subscription_plan = 'school'
                    else:
                        # First check database for subscription status (fast, reliable)
                        db_result = stripe_client.get_subscription_from_db(user.id)
                        if db_result.get('isActive'):
                            # Database confirms active subscription - trust it
                            st.session_state.subscription_verified = True
                            st.session_state.subscription_active = True
                            st.session_state.subscription_plan = db_result.get('plan', 'monthly')
                            st.session_state.subscription_status = db_result.get('status', 'active')
                        else:
                            # Try to sync with Stripe (may fail if Stripe is down)
                            stripe_result = stripe_client.sync_subscription_to_db(user.id, user.email)
                            if stripe_result and stripe_result.get('status') != 'error':
                                st.session_state.subscription_verified = True
                                st.session_state.subscription_active = stripe_result.get('isActive', False)
                                st.session_state.subscription_plan = stripe_result.get('plan')
                                st.session_state.subscription_status = stripe_result.get('status', 'none')
                            else:
                                # Stripe failed and no active subscription in DB
                                st.session_state.subscription_verified = False
                                st.session_state.subscription_active = True
                                st.session_state.subscription_status = 'grace'
                
                print(f"[SESSION] Restored educator session for {user.email}")
                return True
        
        elif user_type == 'student' and session_data.get('student_id'):
            from database import Student
            student = db.query(Student).filter(Student.id == session_data['student_id']).first()
            if student and student.is_active:
                st.session_state.user_id = student.id
                st.session_state.user_type = 'student'
                st.session_state.user_name = student.full_name
                st.session_state.authenticated = True
                st.session_state.is_student = True
                st.session_state.student_id = student.id
                st.session_state.student_username = student.username
                st.session_state.student_year_level = student.year_level
                st.session_state.session_token = token
                
                print(f"[SESSION] Restored student session for {student.username}")
                return True
        
        return False
    except Exception as e:
        print(f"[SESSION] Error restoring session: {str(e)}")
        return False
    finally:
        db.close()


def get_session_cookie():
    """Get session token from cookie using CookieManager"""
    try:
        cookie_manager = get_cookie_manager()
        return cookie_manager.get(SESSION_COOKIE_NAME)
    except Exception as e:
        print(f"[SESSION] Error reading cookie: {str(e)}")
        return None


def check_and_restore_session():
    """Check for existing session token and restore if valid.
    Should be called at app startup before showing login page.
    Returns True if session was restored."""
    
    if st.session_state.get('authenticated'):
        return True
    
    if st.session_state.get('session_restore_attempted'):
        return False
    
    # Read session token directly from cookie using CookieManager
    token = get_session_cookie()
    
    if token:
        st.session_state.session_restore_attempted = True
        
        if restore_session_from_token(token):
            print(f"[SESSION] Session restored from cookie")
            return True
        else:
            # Invalid token, clear the cookie
            print(f"[SESSION] Invalid token, clearing cookie")
            clear_session_cookie()
    
    return False


def create_login_session(user_id=None, student_id=None, user_type='educator'):
    """Create a persistent session after successful login and set cookie immediately."""
    db = get_db()
    if not db:
        return None
    
    try:
        duration = EDUCATOR_SESSION_HOURS if user_type == 'educator' else STUDENT_SESSION_HOURS
        token = create_persistent_session(
            db, 
            user_id=user_id, 
            student_id=student_id, 
            user_type=user_type,
            duration_hours=duration
        )
        
        if token:
            st.session_state.session_token = token
            # Set cookie with exact duration in hours
            set_session_cookie(token, hours=duration)
            print(f"[SESSION] Created persistent session for {user_type}, token set in cookie")
        
        return token
    except Exception as e:
        print(f"[SESSION] Error creating session: {str(e)}")
        return None
    finally:
        db.close()


def logout_with_session_cleanup():
    """Logout user and invalidate their persistent session"""
    token = st.session_state.get('session_token')
    
    if token:
        db = get_db()
        if db:
            try:
                invalidate_persistent_session(db, token)
            finally:
                db.close()
    
    clear_session_cookie()
    
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_api_headers():
    """Get headers for authenticated API calls to payments service (for webhook/token operations)"""
    return {'X-API-Secret': PAYMENTS_API_SECRET, 'Content-Type': 'application/json'}


def check_subscription_status(educator_id):
    """Check if educator has an active subscription (with short cache for responsiveness)
    
    PRIORITY ORDER:
    1. Admin users (is_admin=true in DB) - always get access
    2. School educators - check school subscription
    3. Individual users - check individual subscription
    """
    if not educator_id:
        print("[SUB CHECK] No educator_id provided")
        return {'isActive': False, 'status': 'none'}
    
    # FIRST: Check if user is admin directly from database (bypass all caching)
    db = get_db()
    if db:
        try:
            from database import User
            user = db.query(User).filter(User.id == educator_id).first()
            if user and getattr(user, 'is_admin', False):
                print(f"[SUB CHECK] Admin user {educator_id} detected - granting access")
                st.session_state.is_admin = True
                return {
                    'isActive': True,
                    'status': 'admin',
                    'plan': 'admin',
                    'is_admin': True
                }
        except Exception as e:
            print(f"[SUB CHECK] Error checking admin status: {e}")
        finally:
            db.close()
    
    cache_key = f'subscription_cache_{educator_id}'
    cache_time_key = f'subscription_cache_time_{educator_id}'
    
    cached_data = st.session_state.get(cache_key)
    cached_time = st.session_state.get(cache_time_key)
    
    if cached_data and cached_time:
        age = datetime.now() - cached_time
        if age < SUBSCRIPTION_CACHE_TTL:
            return cached_data
    
    # Check if user is part of a school (school admin or educator)
    school_id = st.session_state.get('school_id')
    user_role = st.session_state.get('user_role', 'individual')
    
    if school_id and user_role in ('school_admin', 'school_educator'):
        # Check school subscription instead of individual
        from database import get_school_by_id, is_school_subscription_active
        db = get_db()
        if db:
            try:
                school = get_school_by_id(db, school_id)
                if school and is_school_subscription_active(school):
                    result = {
                        'isActive': True,
                        'status': school.subscription_status or 'active',
                        'plan': 'school',
                        'school_name': school.name
                    }
                else:
                    result = {'isActive': False, 'status': 'inactive', 'plan': 'school'}
            finally:
                db.close()
        else:
            result = {'isActive': False, 'status': 'error'}
    else:
        # Check individual subscription
        result = stripe_client.get_subscription_from_db(educator_id)
    
    st.session_state[cache_key] = result
    st.session_state[cache_time_key] = datetime.now()
    print(f"[SUB CHECK] educator_id={educator_id}, school_id={school_id}, role={user_role}, result={result}")
    return result

def invalidate_subscription_cache(educator_id=None):
    """Invalidate subscription cache after payment or subscription changes"""
    if educator_id:
        cache_key = f'subscription_cache_{educator_id}'
        cache_time_key = f'subscription_cache_time_{educator_id}'
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        if cache_time_key in st.session_state:
            del st.session_state[cache_time_key]

def sync_subscription_from_stripe(user_id, email):
    """Sync subscription directly from Stripe to database"""
    result = stripe_client.sync_subscription_to_db(user_id, email)
    if result.get('isActive'):
        invalidate_subscription_cache(user_id)
    return result


def create_checkout_url(educator_id, email, plan='monthly'):
    """Create a Stripe checkout session and return URL"""
    return stripe_client.create_checkout_session(educator_id, email, plan)


def create_portal_session(educator_id):
    """Create a Stripe billing portal session"""
    return stripe_client.create_portal_session(educator_id)


def cancel_subscription(educator_id):
    """Cancel subscription at the end of the billing period"""
    result = stripe_client.cancel_subscription(educator_id)
    if result:
        invalidate_subscription_cache(educator_id)
    return result


def reactivate_subscription(educator_id):
    """Reactivate a subscription that was set to cancel"""
    result = stripe_client.reactivate_subscription(educator_id)
    if result:
        invalidate_subscription_cache(educator_id)
    return result

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
    
    educator_id = st.session_state.get('user_id')
    user_email = st.session_state.get('user_email')
    
    # ADMIN BYPASS: Check database directly for admin status
    if educator_id:
        from database import get_db, User
        db = get_db()
        if db:
            try:
                user = db.query(User).filter(User.id == educator_id).first()
                # CRITICAL: Explicit boolean conversion to handle any type issues
                raw_admin = user.is_admin if (user and hasattr(user, 'is_admin')) else False
                db_is_admin = bool(raw_admin) if raw_admin else False
                
                if user and db_is_admin:
                    # User is admin - grant access and redirect
                    st.session_state.is_admin = True
                    st.session_state.subscription_verified = True
                    st.session_state.subscription_active = True
                    st.session_state.subscription_status = 'admin'
                    st.session_state.subscription_plan = 'admin'
                    st.success("Admin access detected. Redirecting...")
                    st.rerun()
            except Exception as e:
                pass  # Continue to pricing page on error
            finally:
                db.close()
    
    if st.button("🔄 Refresh Subscription Status", key="refresh_sub_btn"):
        invalidate_subscription_cache(educator_id)
        
        # First check if user is admin in database
        if educator_id:
            from database import get_db, User
            db = get_db()
            if db:
                try:
                    user = db.query(User).filter(User.id == educator_id).first()
                    if user and getattr(user, 'is_admin', False):
                        st.session_state.is_admin = True
                        st.session_state.subscription_verified = True
                        st.session_state.subscription_active = True
                        st.session_state.subscription_status = 'admin'
                        st.session_state.subscription_plan = 'admin'
                        st.success("Admin access confirmed! Redirecting...")
                        st.rerun()
                finally:
                    db.close()
        
        if user_email and educator_id:
            sync_result = sync_subscription_from_stripe(educator_id, user_email)
            if sync_result and sync_result.get('isActive'):
                st.success("Subscription found! Refreshing...")
                st.rerun()
            else:
                st.warning("No active subscription found in Stripe. Please complete payment below.")
        st.rerun()
    
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
    
    col1, col2, col3 = st.columns(3)
    
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
                checkout_url = create_checkout_url(educator_id, email, 'monthly')
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
                checkout_url = create_checkout_url(educator_id, email, 'annual')
                if checkout_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to secure checkout...")
                else:
                    st.error("Unable to create checkout session. Please try again.")
    
    with col3:
        st.markdown("""
        <div class="pricing-card" style="border-color: #4A90A4; background: linear-gradient(135deg, #f0f7fa 0%, #e8f4f8 100%);">
            <span class="savings-badge" style="background: #4A90A4;">🏫 Schools</span>
            <h3>School Plan</h3>
            <div class="price-amount" style="font-size: 1.8rem;">15+ Teachers</div>
            <p style="color: #4A90A4; font-weight: 500;">Custom pricing & bulk discount codes</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.link_button("📧 Contact Us", "mailto:guide@auxpery.com.au?subject=School%20Subscription%20Enquiry&body=Hi%2C%0A%0AI%27m%20interested%20in%20a%20school%20subscription%20for%20Guide.%0A%0ASchool%20Name%3A%20%0ANumber%20of%20Teachers%3A%20%0A%0AThank%20you!", use_container_width=True)
    
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

def show_account_settings():
    """Display account settings including subscription management and deactivation"""
    educator_id = st.session_state.get('user_id')
    
    if not educator_id:
        return
    
    # Change Password Section
    st.markdown("### Change Password")
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password", key="current_pwd")
        new_password = st.text_input("New Password (min 12 characters)", type="password", key="new_pwd")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pwd")
        change_pwd_submit = st.form_submit_button("Update Password", use_container_width=True)
        
        if change_pwd_submit:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all password fields")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            else:
                is_valid, msg = validate_password(new_password)
                if not is_valid:
                    st.error(msg)
                else:
                    # Verify current password and update
                    result = change_user_password(educator_id, current_password, new_password)
                    if result['success']:
                        st.success("Password updated successfully!")
                    else:
                        st.error(result['error'])
    
    st.markdown("---")
    
    # Admin Tools Section (only visible to admin users)
    if st.session_state.get('is_admin'):
        st.markdown("### 🔧 Admin Tools")
        has_lookup_result = st.session_state.get('admin_lookup_result') is not None
        with st.expander("User Password Reset", expanded=has_lookup_result):
            st.markdown("Look up a user by email and reset their password.")
            lookup_email = st.text_input("User Email to Reset", key="admin_lookup_email", placeholder="user@example.com")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                lookup_clicked = st.button("Look Up User", key="admin_lookup_btn")
            
            if lookup_clicked:
                if not lookup_email:
                    st.warning("Please enter an email address to look up")
                else:
                    db = get_db()
                    if db:
                        try:
                            from database import User
                            user = db.query(User).filter(User.email == lookup_email).first()
                            if user:
                                st.session_state['admin_lookup_result'] = {
                                    'found': True,
                                    'user_id': user.id,
                                    'name': user.full_name,
                                    'email': user.email,
                                    'created': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown'
                                }
                                st.rerun()
                            else:
                                st.session_state['admin_lookup_result'] = {'found': False, 'email': lookup_email}
                                st.rerun()
                        finally:
                            db.close()
            
            lookup_result = st.session_state.get('admin_lookup_result')
            if lookup_result:
                if lookup_result.get('found'):
                    st.success(f"Found user: **{lookup_result['name']}** ({lookup_result['email']})")
                    st.info(f"Account created: {lookup_result['created']}")
                    
                    new_temp_password = st.text_input("New Password for User", type="password", key="admin_new_pwd")
                    if st.button("Reset User Password", key="admin_reset_btn", type="primary"):
                        if new_temp_password:
                            is_valid, msg = validate_password(new_temp_password)
                            if not is_valid:
                                st.error(msg)
                            else:
                                # Pass the admin's user_id for server-side authorization verification
                                admin_user_id = st.session_state.get('user_id')
                                result = admin_reset_password(lookup_result['user_id'], new_temp_password, admin_user_id=admin_user_id)
                                if result['success']:
                                    st.success(f"Password reset for {lookup_result['email']}. Please send them the new password.")
                                    st.session_state['admin_lookup_result'] = None
                                    st.rerun()
                                else:
                                    st.error(result['error'])
                        else:
                            st.error("Please enter a new password")
                else:
                    searched_email = lookup_result.get('email', 'unknown')
                    st.error(f"No user found with email: {searched_email}")
                    if st.button("Clear", key="admin_clear_lookup"):
                        st.session_state['admin_lookup_result'] = None
                        st.rerun()
        
        st.markdown("---")
    
    sub_status = check_subscription_status(educator_id)
    
    # Admin users don't need subscription display
    if st.session_state.get('is_admin'):
        st.info("👑 Admin account - Full access enabled")
        return
    
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

def change_user_password(user_id, current_password, new_password):
    """Change user's password after verifying current password"""
    import bcrypt
    db = get_db()
    if not db:
        return {'success': False, 'error': 'Database unavailable'}
    
    try:
        from database import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Verify current password
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return {'success': False, 'error': 'Current password is incorrect'}
        
        # Hash and update new password
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password_hash = new_hash
        db.commit()
        return {'success': True}
    except Exception as e:
        db.rollback()
        return {'success': False, 'error': f'Error updating password: {str(e)}'}
    finally:
        db.close()

def admin_reset_password(user_id, new_password, admin_user_id=None):
    """Admin function to reset a user's password.
    
    SECURITY: Verifies caller is an admin before allowing password reset.
    """
    import bcrypt
    db = get_db()
    if not db:
        return {'success': False, 'error': 'Database unavailable'}
    
    try:
        from database import User
        
        # AUTHORIZATION CHECK: Verify the caller is an admin from database (not session)
        if admin_user_id:
            admin_user = db.query(User).filter(User.id == admin_user_id).first()
            if not admin_user or not getattr(admin_user, 'is_admin', False):
                return {'success': False, 'error': 'Unauthorized: Admin privileges required'}
        else:
            # If no admin_user_id provided, check session (backwards compatible but less secure)
            import streamlit as st
            if not st.session_state.get('is_admin'):
                return {'success': False, 'error': 'Unauthorized: Admin privileges required'}
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Hash and update new password
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password_hash = new_hash
        db.commit()
        return {'success': True}
    except Exception as e:
        db.rollback()
        return {'success': False, 'error': f'Error resetting password: {str(e)}'}
    finally:
        db.close()

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

def generate_password_reset_token(user_id: int, email: str) -> str:
    """Generate a secure password reset token and store its hash in the database.
    Returns the plain token to be sent via email."""
    import secrets
    import hashlib
    from sqlalchemy import text
    
    db = get_db()
    if not db:
        return None
    
    try:
        # Generate a secure random token
        token = secrets.token_urlsafe(48)
        
        # Hash the token for secure storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Invalidate any previous tokens for this user
        db.execute(
            text("UPDATE password_reset_tokens SET is_valid = FALSE WHERE user_id = :user_id"),
            {'user_id': user_id}
        )
        
        # Store the hashed token with 1-hour expiry
        expires_at = datetime.utcnow() + timedelta(hours=1)
        db.execute(
            text("""INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                    VALUES (:user_id, :token_hash, :expires_at)"""),
            {'user_id': user_id, 'token_hash': token_hash, 'expires_at': expires_at}
        )
        db.commit()
        
        return token
    except Exception as e:
        db.rollback()
        print(f"Error generating reset token: {e}")
        return None
    finally:
        db.close()

def validate_password_reset_token(token: str) -> dict:
    """Validate a password reset token and return user info if valid."""
    import hashlib
    from sqlalchemy import text
    
    db = get_db()
    if not db:
        return {'valid': False, 'error': 'Database unavailable'}
    
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = db.execute(
            text("""SELECT prt.id, prt.user_id, prt.expires_at, prt.is_valid, u.email, u.full_name
                    FROM password_reset_tokens prt
                    JOIN users u ON prt.user_id = u.id
                    WHERE prt.token_hash = :token_hash"""),
            {'token_hash': token_hash}
        ).fetchone()
        
        if not result:
            return {'valid': False, 'error': 'Invalid or expired reset link'}
        
        token_id, user_id, expires_at, is_valid, email, full_name = result
        
        if not is_valid:
            return {'valid': False, 'error': 'This reset link has already been used'}
        
        if datetime.utcnow() > expires_at:
            return {'valid': False, 'error': 'This reset link has expired. Please request a new one.'}
        
        return {
            'valid': True,
            'token_id': token_id,
            'user_id': user_id,
            'email': email,
            'full_name': full_name
        }
    except Exception as e:
        print(f"Error validating reset token: {e}")
        return {'valid': False, 'error': 'Error validating reset link'}
    finally:
        db.close()

def reset_password_with_token(token: str, new_password: str) -> dict:
    """Reset password using a valid token. Atomic operation to prevent race conditions."""
    import hashlib
    from sqlalchemy import text
    import bcrypt
    
    # Validate the new password first (before DB operations)
    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return {'success': False, 'error': msg}
    
    db = get_db()
    if not db:
        return {'success': False, 'error': 'Database unavailable'}
    
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Atomically validate token and mark as used in one query
        # This prevents race conditions where another request could use the same token
        result = db.execute(
            text("""UPDATE password_reset_tokens 
                    SET is_valid = FALSE, used_at = NOW() 
                    WHERE token_hash = :token_hash 
                    AND is_valid = TRUE 
                    AND expires_at > NOW()
                    RETURNING user_id"""),
            {'token_hash': token_hash}
        ).fetchone()
        
        if not result:
            db.rollback()
            return {'success': False, 'error': 'Invalid, expired, or already used reset link'}
        
        user_id = result[0]
        
        # Update the user's password
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.execute(
            text("UPDATE users SET password_hash = :password_hash WHERE id = :user_id"),
            {'password_hash': new_password_hash, 'user_id': user_id}
        )
        
        db.commit()
        return {'success': True}
    except Exception as e:
        db.rollback()
        print(f"Error resetting password: {e}")
        return {'success': False, 'error': 'Error resetting password'}
    finally:
        db.close()

def send_password_reset_email(email: str, reset_url: str, user_name: str = None) -> bool:
    """Send password reset email via Resend (through payments service)."""
    try:
        response = requests.post(
            f"{PAYMENTS_SERVICE_URL}/api/email/send-password-reset",
            json={'email': email, 'resetUrl': reset_url, 'userName': user_name},
            headers=get_api_headers(),
            timeout=15
        )
        if response.status_code == 200:
            return True
        else:
            print(f"Email send failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False

def show_forgot_password_form():
    """Display forgot password form for educators"""
    import time
    import random
    
    st.markdown('<h2 style="text-align: center; color: #2E8B57;">🔑 Reset Your Password</h2>', unsafe_allow_html=True)
    
    if st.button("← Back to Login"):
        st.session_state.auth_mode = 'login'
        st.rerun()
    
    st.markdown("""
    <p style="text-align: center; margin: 20px 0;">
        Enter your email address and we'll send you a link to reset your password.
    </p>
    """, unsafe_allow_html=True)
    
    with st.form("forgot_password_form"):
        email = st.text_input("Email Address", placeholder="your.email@example.com")
        submit = st.form_submit_button("Send Reset Link", use_container_width=True)
        
        if submit:
            start_time = time.time()
            
            if not email:
                st.error("Please enter your email address")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            else:
                db = get_db()
                rate_limited = False
                user = None
                
                if db:
                    try:
                        # Check rate limiting (max 3 reset requests per 15 minutes per email)
                        reset_identifier = f"reset:{email.lower()}"
                        is_locked, remaining_seconds, attempt_count = check_login_rate_limit(
                            db, reset_identifier, max_attempts=3, lockout_minutes=15
                        )
                        
                        if is_locked:
                            rate_limited = True
                            minutes_remaining = remaining_seconds // 60 + 1
                            st.warning(f"Too many reset requests. Please wait {minutes_remaining} minute(s) before trying again.")
                        else:
                            # Record this reset attempt
                            record_login_attempt(db, reset_identifier, attempt_type='reset', success=False)
                            user = get_user_by_email(db, email)
                    finally:
                        db.close()
                
                if not rate_limited:
                    # Always show success message to prevent email enumeration
                    if user:
                        # Generate token and send email
                        token = generate_password_reset_token(user.id, user.email)
                        if token:
                            base_url = os.getenv('GUIDE_APP_URL', 'https://guide.auxpery.com.au')
                            reset_url = f"{base_url}/?reset_token={token}"
                            send_password_reset_email(user.email, reset_url, user.full_name)
                    
                    # Add consistent timing to prevent timing attacks (ensure 1-2 seconds total)
                    elapsed = time.time() - start_time
                    target_time = 1.0 + random.uniform(0, 0.5)  # 1.0-1.5 seconds
                    if elapsed < target_time:
                        time.sleep(target_time - elapsed)
                    
                    st.success("If an account exists with that email, you'll receive a password reset link shortly. Please check your inbox and spam folder.")
    
    st.markdown("""
    <p style="text-align: center; color: #666; font-size: 0.85rem; margin-top: 20px;">
        Note: Students should ask their educator to reset their password.
    </p>
    """, unsafe_allow_html=True)

def show_reset_password_form(token: str):
    """Display the password reset form after clicking email link"""
    st.markdown('<h2 style="text-align: center; color: #2E8B57;">🔐 Create New Password</h2>', unsafe_allow_html=True)
    
    # Validate the token first
    validation = validate_password_reset_token(token)
    
    if not validation.get('valid'):
        st.error(validation.get('error', 'Invalid reset link'))
        st.markdown("""
        <p style="text-align: center; margin-top: 20px;">
            The password reset link is invalid or has expired.
        </p>
        """, unsafe_allow_html=True)
        if st.button("Request New Reset Link"):
            st.session_state.auth_mode = 'forgot_password'
            st.rerun()
        return
    
    st.markdown(f"""
    <p style="text-align: center; margin: 20px 0;">
        Create a new password for <strong>{validation.get('email')}</strong>
    </p>
    """, unsafe_allow_html=True)
    
    with st.form("reset_password_form"):
        new_password = st.text_input("New Password (min 12 characters)", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Reset Password", use_container_width=True)
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Please fill in both password fields")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                result = reset_password_with_token(token, new_password)
                if result.get('success'):
                    st.success("Your password has been reset successfully! You can now log in with your new password.")
                    st.session_state.auth_mode = 'login'
                    # Clear the reset token from URL and session
                    st.query_params.clear()
                    if 'reset_token' in st.session_state:
                        del st.session_state.reset_token
                    st.rerun()
                else:
                    st.error(result.get('error', 'Failed to reset password'))

def login_page():
    """Display login page for educators and students"""
    
    # Style for tabs and sandy buttons
    st.markdown("""
    <style>
    /* Style login tabs for clear distinction */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 6px;
        justify-content: center;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.9rem;
    }
    /* Sandy colour for secondary buttons */
    button[data-testid="baseButton-secondary"] {
        background: linear-gradient(135deg, #D7C3AA 0%, #C4A882 100%) !important;
        border: 1px solid rgba(166, 123, 91, 0.3) !important;
        color: #5a4a3a !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background: linear-gradient(135deg, #C4A882 0%, #B8956A 100%) !important;
        border-color: rgba(166, 123, 91, 0.5) !important;
    }
    /* Sandy colour for link buttons */
    a[data-testid="baseLinkButton-secondary"] {
        background: linear-gradient(135deg, #D7C3AA 0%, #C4A882 100%) !important;
        border: 1px solid rgba(166, 123, 91, 0.3) !important;
        color: #5a4a3a !important;
    }
    a[data-testid="baseLinkButton-secondary"]:hover {
        background: linear-gradient(135deg, #C4A882 0%, #B8956A 100%) !important;
        border-color: rgba(166, 123, 91, 0.5) !important;
    }
    /* Small forgot password button */
    button[data-testid="baseButton-secondary"] {
        padding: 4px 12px !important;
        font-size: 0.75rem !important;
        min-height: unset !important;
        height: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Use tabs for all options - Educator, Student, Sign Up, Terms
    educator_tab, student_tab, signup_tab, terms_tab = st.tabs(["👩‍🏫 Educator", "🎒 Student", "✨ Sign Up", "📜 Terms"])
    
    with educator_tab:
        with st.form("educator_login"):
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
                            # Store school info for school subscriptions
                            st.session_state.user_role = getattr(user, 'role', 'individual')
                            st.session_state.school_id = getattr(user, 'school_id', None)
                            # Store admin status for bypassing subscription checks
                            # CRITICAL: Explicit boolean conversion to handle any type issues
                            raw_is_admin = user.is_admin if hasattr(user, 'is_admin') else False
                            st.session_state.is_admin = bool(raw_is_admin) if raw_is_admin else False
                            print(f"[AUTH LOGIN] User {user.email} - raw is_admin: {raw_is_admin}, type: {type(raw_is_admin)}, final: {st.session_state.is_admin}")
                            # Clear any existing auth_mode to ensure clean state
                            if 'auth_mode' in st.session_state:
                                del st.session_state['auth_mode']
                            
                            # Admin users bypass subscription checks entirely
                            if st.session_state.is_admin:
                                print(f"[AUTH LOGIN] ADMIN PATH TRIGGERED for {user.email}")
                                st.session_state.subscription_verified = True
                                st.session_state.subscription_active = True
                                st.session_state.subscription_status = 'admin'
                                st.session_state.subscription_plan = 'admin'
                                user_id = user.id
                                user_name = st.session_state.user_name
                                db.close()  # Close db before calling create_login_session
                                db = None
                                create_login_session(user_id=user_id, user_type='educator')
                                st.success(f"Welcome back, {user_name}! (Admin)")
                                st.rerun()
                                return  # Ensure code doesn't continue after rerun
                            
                            # School educators use school subscription
                            if st.session_state.get('school_id') and st.session_state.get('user_role') in ('school_admin', 'school_educator'):
                                from database import get_school_by_id, is_school_subscription_active
                                school = get_school_by_id(db, st.session_state.school_id)
                                if school and is_school_subscription_active(school):
                                    st.session_state.subscription_verified = True
                                    st.session_state.subscription_active = True
                                    st.session_state.subscription_status = school.subscription_status or 'active'
                                    st.session_state.subscription_plan = 'school'
                                else:
                                    st.session_state.subscription_verified = True
                                    st.session_state.subscription_active = False
                                    st.session_state.subscription_status = 'inactive'
                                    st.session_state.subscription_plan = 'school'
                                user_id = user.id
                                user_name = st.session_state.user_name
                                school_name = school.name if school else "your school"
                                db.close()
                                db = None
                                create_login_session(user_id=user_id, user_type='educator')
                                st.success(f"Welcome back, {user_name}! ({school_name})")
                                st.rerun()
                                return
                            
                            # FAILPROOF: Check Stripe directly at login, with graceful fallback
                            stripe_result = sync_subscription_from_stripe(user.id, user.email)
                            invalidate_subscription_cache(user.id)
                            
                            # Handle Stripe errors gracefully - NEVER block on transient failures
                            stripe_status = stripe_result.get('status', 'none') if stripe_result else 'error'
                            
                            if stripe_status == 'error':
                                # Stripe failed - check database for existing subscription
                                print(f"[AUTH] Stripe check failed for {user.email}, checking database...")
                                db_result = stripe_client.get_subscription_from_db(int(user.id))
                                
                                if db_result.get('isActive'):
                                    # Database has confirmed active subscription - trust it!
                                    print(f"[AUTH] Database confirms active subscription for {user.email}")
                                    st.session_state.subscription_verified = True
                                    st.session_state.subscription_active = True
                                    st.session_state.subscription_status = db_result.get('status', 'active')
                                    st.session_state.subscription_plan = db_result.get('plan', 'monthly')
                                else:
                                    # No active subscription in DB, grant grace access
                                    print(f"[AUTH] No active subscription in DB, granting GRACE ACCESS")
                                    st.session_state.subscription_verified = False
                                    st.session_state.subscription_active = True  # GRACE ACCESS
                                    st.session_state.subscription_status = 'grace'
                                    st.session_state.subscription_plan = db_result.get('plan') or 'grace'
                            else:
                                # Successful Stripe response - this is authoritative
                                is_active = stripe_result.get('isActive', False)
                                plan = stripe_result.get('plan')
                                
                                st.session_state.subscription_verified = True  # Confirmed with Stripe
                                st.session_state.subscription_active = is_active
                                st.session_state.subscription_plan = plan
                                st.session_state.subscription_status = stripe_status
                            
                            user_id = user.id
                            user_name = st.session_state.user_name
                            db.close()  # Close db before calling create_login_session
                            db = None  # Mark as closed
                            create_login_session(user_id=user_id, user_type='educator')
                            st.success(f"Welcome back, {user_name}!")
                            st.rerun()
                        else:
                            # Record failed attempt
                            record_login_attempt(db, email, attempt_type='educator', success=False)
                            st.session_state.show_forgot_password = True
                            attempts_remaining = 5 - failed_count - 1
                            if attempts_remaining > 0:
                                st.error(f"Invalid email or password. {attempts_remaining} attempt(s) remaining before lockout.")
                            else:
                                st.error("Invalid email or password. Account will be locked on next failed attempt.")
                    finally:
                        if db:
                            db.close()
        
        # Show forgot password link only after failed login attempt
        if st.session_state.get('show_forgot_password'):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Forgot your password?", key="forgot_pwd_link", type="secondary"):
                    st.session_state.auth_mode = 'forgot_password'
                    st.session_state.show_forgot_password = False
                    st.rerun()
    
    with student_tab:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0; margin-bottom: 15px;">
            <p style="color: #666; font-size: 0.95em;">Students - use the username your teacher gave you</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("student_login"):
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
                            st.session_state.student_id = student.id
                            st.session_state.student_username = student.username
                            st.session_state.student_year_level = getattr(student, 'year_level', None)
                            # Clear any existing auth_mode to prevent educator features from showing
                            if 'auth_mode' in st.session_state:
                                del st.session_state['auth_mode']
                            student_id = student.id
                            student_name = st.session_state.user_name
                            db.close()  # Close db before calling create_login_session
                            db = None  # Mark as closed
                            create_login_session(student_id=student_id, user_type='student')
                            st.success(f"Welcome back, {student_name}!")
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
        
        st.markdown("""
        <div style="text-align: center; margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <p style="color: #666; font-size: 0.9em; margin: 0;">
                Need help? Ask your teacher for your login details.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with signup_tab:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0; margin-bottom: 15px;">
            <p style="color: #666; font-size: 0.95em;">Create your educator account to get started</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("signup_form_inline"):
            full_name = st.text_input("Full Name", placeholder="Your full name")
            email = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password", placeholder="Choose a secure password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            agree_terms = st.checkbox("I agree to the Terms and Conditions")
            
            submit = st.form_submit_button("Create Account", use_container_width=True)
            
            if submit:
                if not all([full_name, email, password, confirm_password]):
                    st.error("Please fill in all fields")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters")
                elif not agree_terms:
                    st.error("Please agree to the Terms and Conditions")
                else:
                    valid_password, password_message = validate_password(password)
                    if not valid_password:
                        st.error(password_message)
                    else:
                        db = get_db()
                        if not db:
                            st.error("Registration is not available. Database connection required.")
                        else:
                            try:
                                existing_user = get_user_by_email(db, email)
                                if existing_user:
                                    st.error("An account with this email already exists")
                                else:
                                    user = create_user(db, email, password, full_name, 'educator')
                                    from database import record_consent
                                    record_consent(db, user_id=user.id, consent_type='data_collection', policy_version="1.0")
                                    record_consent(db, user_id=user.id, consent_type='privacy_policy', policy_version="1.0")
                                    st.success("Account created successfully! Please log in using the Educator tab.")
                            finally:
                                db.close()
    
    with terms_tab:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0; margin-bottom: 15px;">
            <h3 style="color: #2E8B57; margin-bottom: 10px;">Terms and Conditions</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        **Welcome to Guide - Your Cosmic Curriculum Companion**
        
        By using this application, you agree to the following terms:
        
        **1. Educational Use**
        Guide is designed for educational purposes, supporting Montessori and Australian Curriculum V9 aligned learning experiences.
        
        **2. Data Privacy**
        - We comply with the Australian Privacy Act 1988
        - Student data is protected and handled with care
        - Educator data is used only for service provision
        - You can export or delete your data at any time
        
        **3. Student Accounts**
        - Educators are responsible for student accounts they create
        - Guardian consent is required for student accounts
        - Student data is retained according to Australian education requirements
        
        **4. AI-Generated Content**
        - Lesson plans and content are AI-assisted suggestions
        - Educators should review and adapt all generated content
        - Final educational decisions rest with the educator
        
        **5. Subscription Terms**
        - Free trial available for new accounts
        - Subscriptions can be managed through your account settings
        - Refunds handled according to Australian Consumer Law
        
        **6. Acceptable Use**
        - Use the platform for legitimate educational purposes
        - Do not share login credentials
        - Report any concerning content or behaviour
        
        **Contact Us**
        For questions about these terms, contact: guideaichat@gmail.com
        
        *Last updated: January 2026*
        """)

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

def school_join_page(invite_code: str):
    """Display page for educators to join a school via invite link"""
    from database import get_school_by_invite_code, add_educator_to_school, school_has_available_licenses, is_school_subscription_active
    
    db = get_db()
    if not db:
        st.error("Service temporarily unavailable. Please try again later.")
        return
    
    try:
        school = get_school_by_invite_code(db, invite_code)
        
        if not school:
            st.error("Invalid invite link. Please check with your school administrator.")
            st.markdown("---")
            if st.button("Return to Login", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
            return
        
        # Check if school subscription is active
        if not is_school_subscription_active(school):
            st.error("This school's subscription is not active. Please contact your school administrator.")
            if st.button("Return to Login", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
            return
        
        # Check if school has available licenses
        if not school_has_available_licenses(db, school.id):
            st.warning("This school has reached its license limit. Please contact your school administrator to add more seats.")
            if st.button("Return to Login", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
            return
        
        # Show school name and welcome message
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #D7C3AA 0%, #C4A882 100%); border-radius: 12px; margin-bottom: 2rem;">
            <h2 style="color: #5D4E37; margin-bottom: 0.5rem;">🏫 Join {school.name}</h2>
            <p style="color: #6B5B4F;">Create your educator account to get started</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("school_join_form"):
            st.markdown("### Create Your Account")
            full_name = st.text_input("Full Name", placeholder="Your full name")
            email = st.text_input("Email", placeholder="your.email@school.edu")
            password = st.text_input("Password", type="password", help="Minimum 12 characters with uppercase, lowercase, and number")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            agree_terms = st.checkbox("I have read and agree to the Terms and Conditions", value=False)
            
            submit = st.form_submit_button("Join School", use_container_width=True)
            
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
                        # Check if user already exists
                        existing_user = get_user_by_email(db, email)
                        if existing_user:
                            # User exists - verify their password before adding to school
                            authenticated_user = authenticate_user(db, email, password)
                            if not authenticated_user:
                                st.error("An account with this email already exists. Please enter the correct password to join the school, or log in using the link below.")
                            elif existing_user.school_id and existing_user.school_id != school.id:
                                # User belongs to a DIFFERENT school
                                st.error("This account is already associated with another school")
                            elif existing_user.school_id == school.id:
                                # User is already in THIS school - just log them in
                                st.session_state.user_id = existing_user.id
                                st.session_state.user_type = existing_user.user_type
                                st.session_state.user_name = existing_user.full_name
                                st.session_state.user_email = existing_user.email
                                st.session_state.authenticated = True
                                st.session_state.is_student = False
                                st.session_state.school_id = school.id
                                st.session_state.user_role = existing_user.role or 'school_educator'
                                st.success(f"Welcome back to {school.name}!")
                                st.query_params.clear()
                                st.rerun()
                            else:
                                success, error = add_educator_to_school(db, existing_user.id, school.id, 'school_educator')
                                if success:
                                    # Log them in directly since password was verified
                                    st.session_state.user_id = existing_user.id
                                    st.session_state.user_type = existing_user.user_type
                                    st.session_state.user_name = existing_user.full_name
                                    st.session_state.user_email = existing_user.email
                                    st.session_state.authenticated = True
                                    st.session_state.is_student = False
                                    st.session_state.school_id = school.id
                                    st.session_state.user_role = 'school_educator'
                                    st.success(f"Welcome to {school.name}!")
                                    st.query_params.clear()
                                    st.rerun()
                                else:
                                    st.error(error or "Failed to join school. Please try again.")
                        else:
                            # Create new user
                            user = create_user(db, email, password, full_name, 'educator')
                            
                            # Add user to school
                            success, error = add_educator_to_school(db, user.id, school.id, 'school_educator')
                            if success:
                                # Record consent
                                from database import record_consent
                                record_consent(db, user_id=user.id, consent_type='data_collection', policy_version="1.0")
                                record_consent(db, user_id=user.id, consent_type='privacy_policy', policy_version="1.0")
                                
                                st.success(f"Welcome to {school.name}, {full_name}!")
                                
                                # Log in the user
                                st.session_state.user_id = user.id
                                st.session_state.user_type = user.user_type
                                st.session_state.user_name = user.full_name
                                st.session_state.user_email = user.email
                                st.session_state.authenticated = True
                                st.session_state.is_student = False
                                st.session_state.school_id = school.id
                                st.session_state.user_role = 'school_educator'
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.error(error or "Failed to join school. Please try again.")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Already have an account? Log in", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
    finally:
        if db:
            db.close()

def school_setup_page(setup_token: str):
    """Display page for school admin to set up their account after Stripe checkout"""
    import requests
    import os
    
    db = get_db()
    if not db:
        st.error("Service temporarily unavailable. Please try again later.")
        return
    
    # Use internal service URL - works in both dev and production
    payments_base = os.getenv('PAYMENTS_SERVICE_URL', 'http://localhost:3001')
    
    try:
        # Validate the setup token via API
        api_url = f"{payments_base}/api/public/validate-school-token/{setup_token}"
        try:
            response = requests.get(api_url, timeout=10)
            token_data = response.json()
        except Exception as e:
            st.error("Unable to validate your setup token. Please try again later.")
            if st.button("Return to Home", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
            return
        
        if not token_data.get('success'):
            error_msg = token_data.get('error', 'Invalid or expired setup token')
            st.error(error_msg)
            if st.button("Return to Home", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.query_params.clear()
                st.rerun()
            return
        
        pending = token_data.get('data', {})
        email = pending.get('email', '')
        school_name = pending.get('school_name', '')
        seats = pending.get('seats', 5)
        
        # Show welcome header
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #D7C3AA 0%, #C4A882 100%); border-radius: 12px; margin-bottom: 2rem;">
            <h2 style="color: #5D4E37; margin-bottom: 0.5rem;">🏫 Complete Your School Setup</h2>
            <p style="color: #6B5B4F;">Welcome! Let's finish setting up <strong>{school_name}</strong></p>
            <p style="color: #8B7B6B; font-size: 0.9rem;">{seats} educator seats included</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("school_setup_form"):
            st.markdown("### Create Your Admin Account")
            st.info(f"Account email: **{email}**")
            
            full_name = st.text_input("Your Full Name", placeholder="Enter your full name")
            password = st.text_input("Password", type="password", help="Minimum 12 characters with uppercase, lowercase, and number")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            agree_terms = st.checkbox("I have read and agree to the Terms and Conditions", value=False)
            
            submit = st.form_submit_button("Complete Setup", use_container_width=True, type="primary")
            
            if submit:
                # Validation
                if not full_name:
                    st.error("Please enter your full name")
                elif not password or not confirm_password:
                    st.error("Please enter and confirm your password")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif not agree_terms:
                    st.error("Please agree to the Terms and Conditions to continue")
                else:
                    valid_password, password_message = validate_password(password)
                    if not valid_password:
                        st.error(password_message)
                    else:
                        # Complete setup via API
                        try:
                            complete_response = requests.post(
                                f"{payments_base}/api/public/complete-school-setup",
                                json={
                                    "token": setup_token,
                                    "fullName": full_name,
                                    "password": password
                                },
                                timeout=30
                            )
                            result = complete_response.json()
                            
                            if result.get('success'):
                                user_id = result.get('userId')
                                school_id = result.get('schoolId')
                                
                                # Log in the user
                                user = get_user_by_email(db, email)
                                if user:
                                    st.session_state.user_id = user.id
                                    st.session_state.user_type = user.user_type
                                    st.session_state.user_name = user.full_name
                                    st.session_state.user_email = user.email
                                    st.session_state.authenticated = True
                                    st.session_state.is_student = False
                                    st.session_state.school_id = school_id
                                    st.session_state.user_role = 'school_admin'
                                    st.session_state.subscription_active = True
                                    st.session_state.subscription_verified = True
                                    st.session_state.subscription_status = 'active'
                                    st.session_state.subscription_plan = 'school'
                                    
                                    st.success(f"Welcome to Guide, {full_name}! Your school is ready.")
                                    st.query_params.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Account created but login failed. Please try logging in manually.")
                            else:
                                st.error(result.get('error', 'Failed to complete setup. Please try again.'))
                        except Exception as e:
                            st.error(f"Error completing setup: {str(e)}")
        
        st.markdown("---")
        if st.button("Already have an account? Log in", use_container_width=True):
            st.session_state.auth_mode = 'login'
            st.query_params.clear()
            st.rerun()
    finally:
        if db:
            db.close()

def show_school_admin_dashboard():
    """Display school admin dashboard for managing educators and licenses"""
    from database import get_school_by_id, get_school_educators, get_school_educator_count, remove_educator_from_school
    
    if not st.session_state.get('authenticated'):
        st.error("Access denied. Please log in.")
        return
    
    # Check if user is a school admin
    user_role = st.session_state.get('user_role', 'individual')
    school_id = st.session_state.get('school_id')
    
    if user_role != 'school_admin' or not school_id:
        st.error("Access denied. Only school administrators can access this dashboard.")
        return
    
    db = get_db()
    if not db:
        st.error("Service temporarily unavailable.")
        return
    
    try:
        school = get_school_by_id(db, school_id)
        if not school:
            st.error("School not found.")
            return
        
        # Check and display subscription status warning if needed
        from database import is_school_subscription_active
        subscription_active = is_school_subscription_active(school)
        
        if not subscription_active:
            status_text = school.subscription_status or 'inactive'
            if status_text == 'canceled' and school.subscription_end:
                st.warning(f"⚠️ Your school's subscription has been cancelled. Access ended on {school.subscription_end.strftime('%d %B %Y')}. Please renew to continue using Guide.")
            elif status_text == 'past_due':
                st.warning("⚠️ Your school's subscription payment is past due. Please update your payment method to avoid service interruption.")
            else:
                st.warning("⚠️ Your school's subscription is not active. Please contact support or renew your subscription.")
        
        # Header with school info
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #D7C3AA 0%, #C4A882 100%); padding: 2rem; border-radius: 12px; margin-bottom: 2rem;">
            <h2 style="color: #5D4E37; margin-bottom: 0.5rem;">🏫 {school.name}</h2>
            <p style="color: #6B5B4F; margin-bottom: 0;">School Administration Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # License usage metrics
        educator_count = get_school_educator_count(db, school_id)
        license_count = school.license_count or 0
        available_seats = max(0, license_count - educator_count)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Seats", license_count)
        with col2:
            st.metric("Seats Used", educator_count)
        with col3:
            st.metric("Available Seats", available_seats)
        
        st.markdown("---")
        
        # Invite link section
        st.markdown("### 🔗 Invite Educators")
        base_url = os.getenv('GUIDE_APP_URL', 'https://guide.auxpery.com.au')
        invite_url = f"{base_url}/?join={school.invite_code}"
        
        st.markdown(f"""
        <div style="background: #F5F0E8; padding: 1.5rem; border-radius: 8px; border: 1px solid #D7C3AA;">
            <p style="margin-bottom: 0.5rem; color: #5D4E37; font-weight: 600;">Share this link with educators to invite them:</p>
            <code style="background: white; padding: 0.5rem 1rem; border-radius: 4px; display: block; word-break: break-all; font-size: 0.9rem;">{invite_url}</code>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📋 Copy Link", key="copy_invite_link"):
                st.session_state.invite_link_copied = True
                st.rerun()
        
        if st.session_state.get('invite_link_copied'):
            st.success("Link copied! Share it with your educators.")
            st.markdown(f"""
            <script>
            navigator.clipboard.writeText("{invite_url}");
            </script>
            """, unsafe_allow_html=True)
            del st.session_state.invite_link_copied
        
        st.markdown("---")
        
        # Educator list
        st.markdown("### 👥 Educators")
        
        educators = get_school_educators(db, school_id)
        
        if not educators:
            st.info("No educators have joined yet. Share your invite link to get started!")
        else:
            for educator in educators:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    role_badge = "👑 Admin" if educator.role == 'school_admin' else "👩‍🏫 Educator"
                    st.markdown(f"**{educator.full_name}** {role_badge}")
                with col2:
                    st.markdown(f"<span style='color: #6B5B4F;'>{educator.email}</span>", unsafe_allow_html=True)
                with col3:
                    # Don't allow removing the admin themselves
                    if educator.id != st.session_state.get('user_id') and educator.role != 'school_admin':
                        if st.button("Remove", key=f"remove_{educator.id}", type="secondary"):
                            if remove_educator_from_school(db, educator.id):
                                st.success(f"Removed {educator.full_name} from the school.")
                                st.rerun()
                            else:
                                st.error("Failed to remove educator.")
                
                st.markdown("<hr style='margin: 0.5rem 0; border-color: #E8E0D5;'>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Subscription status
        st.markdown("### 💳 Subscription")
        
        status_colors = {
            'active': '#2E8B57',
            'trialing': '#3498db',
            'past_due': '#e67e22',
            'canceled': '#e74c3c',
            'unpaid': '#e74c3c'
        }
        status_color = status_colors.get(school.subscription_status, '#6B5B4F')
        status_display = (school.subscription_status or 'unknown').replace('_', ' ').title()
        
        st.markdown(f"""
        <div style="background: #F5F0E8; padding: 1.5rem; border-radius: 8px;">
            <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: 600;">{status_display}</span></p>
        </div>
        """, unsafe_allow_html=True)
        
        if school.subscription_status == 'active':
            if st.button("Manage Subscription", use_container_width=True):
                portal_url = stripe_client.create_school_portal_session(school_id)
                if portal_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={portal_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to Stripe Customer Portal...")
                else:
                    st.error("Unable to open subscription portal. Please try again later.")
        
        st.markdown("---")
        
        # Account Settings - Email Change
        st.markdown("### ⚙️ Account Settings")
        
        current_email = st.session_state.get('user_email', '')
        st.markdown(f"""
        <div style="background: #F5F0E8; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p style="margin: 0; color: #5D4E37;"><strong>Current Email:</strong> {current_email}</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📧 Change Email Address"):
            st.markdown("Transfer your admin account to a new email address. You'll need to enter your current password to confirm this change.")
            
            with st.form("change_email_form"):
                new_email = st.text_input("New Email Address", placeholder="newemail@school.edu")
                confirm_password = st.text_input("Current Password", type="password", help="Enter your password to confirm this change")
                
                submit_email_change = st.form_submit_button("Update Email", use_container_width=True)
                
                if submit_email_change:
                    if not new_email or not confirm_password:
                        st.error("Please fill in all fields.")
                    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', new_email):
                        st.error("Please enter a valid email address.")
                    elif new_email.lower().strip() == current_email.lower():
                        st.warning("The new email is the same as your current email.")
                    else:
                        # Additional session validation: verify persistent session is active
                        from database import update_user_email, validate_persistent_session
                        user_id = st.session_state.get('user_id')
                        session_token = st.session_state.get('session_token')
                        
                        # Validate session token against database
                        session_valid = False
                        if session_token:
                            validated = validate_persistent_session(db, session_token)
                            if validated and validated.get('user_id') == user_id:
                                session_valid = True
                        
                        if not session_valid:
                            st.error("Session expired. Please log in again.")
                        else:
                            # Pass session user ID for server-side authorisation (role verified from DB)
                            success, message = update_user_email(
                                db, user_id, new_email, confirm_password,
                                session_user_id=user_id
                            )
                            
                            if success:
                                st.success(message)
                                st.session_state.user_email = new_email.lower().strip()
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(message)
        
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
    """Log out current user and invalidate persistent session"""
    logout_with_session_cleanup()
    st.success("You have been logged out successfully!")
    st.rerun()


def export_user_data_gdpr():
    """
    Export all user data in GDPR-compliant JSON format.
    Excludes sensitive fields like password hashes and internal IDs.
    """
    from database import (User, Student, LessonPlan, GreatStory, PlanningNote,
                          ChatConversation, ConversationHistory, EducatorAnalytics,
                          StudentActivity, EducatorAuditLog)
    
    db = get_db()
    if not db:
        return None
    
    try:
        export_data = {
            "export_date": datetime.now().isoformat(),
            "export_type": "GDPR Data Export",
            "data_controller": "Guide by AUXPERY"
        }
        
        if st.session_state.get('is_student'):
            student_id = st.session_state.get('user_id')
            student = db.query(Student).filter(Student.id == student_id).first()
            
            if student:
                export_data["profile"] = {
                    "username": student.username,
                    "full_name": student.full_name,
                    "age_group": student.age_group,
                    "account_created": student.created_at.isoformat() if student.created_at else None,
                    "is_active": student.is_active
                }
                
                activities = db.query(StudentActivity).filter(
                    StudentActivity.student_id == student_id
                ).order_by(StudentActivity.created_at.desc()).all()
                
                export_data["activities"] = [{
                    "type": a.activity_type,
                    "prompt": a.prompt_text,
                    "response": a.response_text,
                    "session_id": a.session_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                } for a in activities]
                
                conversations = db.query(ChatConversation).filter(
                    ChatConversation.student_id == student_id
                ).all()
                
                export_data["conversations"] = []
                for conv in conversations:
                    messages = db.query(ConversationHistory).filter(
                        ConversationHistory.session_id == conv.session_id
                    ).order_by(ConversationHistory.created_at).all()
                    
                    export_data["conversations"].append({
                        "title": conv.title,
                        "subject": conv.subject_tag,
                        "created_at": conv.created_at.isoformat() if conv.created_at else None,
                        "messages": [{
                            "role": m.role,
                            "content": m.content,
                            "created_at": m.created_at.isoformat() if m.created_at else None
                        } for m in messages]
                    })
        else:
            user_id = st.session_state.get('user_id')
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                export_data["profile"] = {
                    "email": user.email,
                    "full_name": user.full_name,
                    "user_type": user.user_type,
                    "institution": user.institution_name,
                    "account_created": user.created_at.isoformat() if user.created_at else None,
                    "is_active": user.is_active
                }
                
                lesson_plans = db.query(LessonPlan).filter(
                    LessonPlan.creator_id == user_id
                ).all()
                
                export_data["lesson_plans"] = [{
                    "title": lp.title,
                    "description": lp.description,
                    "content": lp.content,
                    "curriculum_codes": lp.australian_curriculum_codes,
                    "montessori_principles": lp.montessori_principles,
                    "age_group": lp.age_group,
                    "created_at": lp.created_at.isoformat() if lp.created_at else None,
                    "updated_at": lp.updated_at.isoformat() if lp.updated_at else None
                } for lp in lesson_plans]
                
                stories = db.query(GreatStory).filter(
                    GreatStory.educator_id == user_id
                ).all()
                
                export_data["great_stories"] = [{
                    "title": s.title,
                    "theme": s.theme,
                    "content": s.content,
                    "age_group": s.age_group,
                    "keywords": s.keywords,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                } for s in stories]
                
                notes = db.query(PlanningNote).filter(
                    PlanningNote.educator_id == user_id
                ).all()
                
                export_data["planning_notes"] = [{
                    "title": n.title,
                    "content": n.content,
                    "chapters": n.chapters,
                    "materials": n.materials,
                    "created_at": n.created_at.isoformat() if n.created_at else None
                } for n in notes]
                
                conversations = db.query(ChatConversation).filter(
                    ChatConversation.user_id == user_id
                ).all()
                
                export_data["conversations"] = []
                for conv in conversations:
                    messages = db.query(ConversationHistory).filter(
                        ConversationHistory.session_id == conv.session_id
                    ).order_by(ConversationHistory.created_at).all()
                    
                    export_data["conversations"].append({
                        "title": conv.title,
                        "interface_type": conv.interface_type,
                        "created_at": conv.created_at.isoformat() if conv.created_at else None,
                        "messages": [{
                            "role": m.role,
                            "content": m.content,
                            "created_at": m.created_at.isoformat() if m.created_at else None
                        } for m in messages]
                    })
                
                analytics = db.query(EducatorAnalytics).filter(
                    EducatorAnalytics.user_id == user_id
                ).order_by(EducatorAnalytics.created_at.desc()).limit(500).all()
                
                export_data["usage_analytics"] = [{
                    "interface_type": a.interface_type,
                    "subject": a.subject,
                    "year_level": a.year_level,
                    "prompt": a.prompt_text,
                    "tokens_used": a.tokens_used,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                } for a in analytics]
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    except Exception as e:
        print(f"[GDPR EXPORT ERROR] {e}")
        return None
    finally:
        db.close()

def show_user_info():
    """Display current user information with subscription status and navigation tools"""
    if st.session_state.get('authenticated'):
        # Inject sidebar tool card styling
        st.sidebar.markdown("""
        <style>
        .sidebar-tool-card {
            background: linear-gradient(135deg, rgba(245, 240, 232, 0.9), rgba(235, 228, 216, 0.9));
            border: 1px solid rgba(166, 123, 91, 0.2);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .sidebar-tool-card:hover {
            background: linear-gradient(135deg, rgba(166, 123, 91, 0.15), rgba(184, 149, 106, 0.15));
            border-color: rgba(166, 123, 91, 0.4);
            transform: translateX(2px);
        }
        .sidebar-tool-icon {
            font-size: 1.3rem;
            margin-bottom: 4px;
        }
        .sidebar-tool-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: #4a4a4a;
            margin-bottom: 2px;
        }
        .sidebar-tool-desc {
            font-size: 0.78rem;
            color: #6b6b6b;
            line-height: 1.3;
        }
        .sidebar-section-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #8B7355;
            font-weight: 600;
            margin: 20px 0 12px 0;
            padding-left: 4px;
        }
        .sidebar-user-info {
            background: rgba(166, 123, 91, 0.08);
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 16px;
        }
        .sidebar-user-name {
            font-weight: 600;
            font-size: 0.95rem;
            color: #4a4a4a;
        }
        .sidebar-user-detail {
            font-size: 0.8rem;
            color: #6b6b6b;
            margin-top: 2px;
        }
        
        /* Smaller, sandy-colored sidebar buttons */
        [data-testid="stSidebar"] .stButton > button {
            background: rgba(215, 195, 170, 0.35) !important;
            border: 1px solid rgba(166, 123, 91, 0.25) !important;
            border-radius: 8px !important;
            color: #5a5a5a !important;
            font-size: 0.82rem !important;
            padding: 8px 12px !important;
            min-height: 36px !important;
            transition: all 0.15s ease !important;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(195, 165, 130, 0.45) !important;
            border-color: rgba(166, 123, 91, 0.4) !important;
            transform: translateX(1px);
        }
        
        /* Primary button styling (Dashboard Home) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: rgba(166, 123, 91, 0.7) !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 500 !important;
        }
        
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: rgba(166, 123, 91, 0.85) !important;
        }
        
        /* Reduce spacing between buttons and make them narrower */
        [data-testid="stSidebar"] .stButton {
            margin-bottom: 4px !important;
            padding: 0 12px !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            max-width: 85% !important;
            margin: 0 auto !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if st.session_state.get('is_student'):
            # Student user info
            st.sidebar.markdown(f"""
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">👤 {st.session_state.user_name}</div>
                <div class="sidebar-user-detail">@{st.session_state.username}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Educator user info with subscription badge
            sub_status = st.session_state.get('subscription_status', 'none')
            plan_badge = ""
            if st.session_state.get('subscription_active'):
                plan = (st.session_state.get('subscription_plan') or 'monthly').capitalize()
                if sub_status == 'grace':
                    plan_badge = f"<span style='font-size: 0.75rem; color: #B8956A;'>⏳ {plan}</span>"
                else:
                    plan_badge = f"<span style='font-size: 0.75rem; color: #5B8A72;'>✓ {plan}</span>"
            else:
                plan_badge = "<span style='font-size: 0.75rem; color: #999;'>Free</span>"
            
            st.sidebar.markdown(f"""
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">👤 {st.session_state.user_name}</div>
                <div class="sidebar-user-detail">{st.session_state.user_email}</div>
                <div style="margin-top: 6px;">{plan_badge}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Dashboard Home button at the top
            if st.sidebar.button("🏠 Dashboard Home", key="sb_home", use_container_width=True, type="primary"):
                st.session_state.auth_mode = "dashboard_home"
                st.rerun()
            
            # Navigation tools for educators
            st.sidebar.markdown('<div class="sidebar-section-label">Tools</div>', unsafe_allow_html=True)
            
            # Tool cards with beautiful styling
            tools = [
                {"icon": "📚", "title": "Lesson Planning", "desc": "Design learning experiences", "mode": "lesson_planning", "key": "sb_lp"},
                {"icon": "🌱", "title": "Montessori Companion", "desc": "Wisdom and training", "mode": "companion", "key": "sb_comp"},
                {"icon": "📖", "title": "Great Stories", "desc": "Narrative introductions", "mode": "great_stories", "key": "sb_gs"},
                {"icon": "✨", "title": "Imaginarium", "desc": "Creative exploration", "mode": "imaginarium", "key": "sb_img"},
            ]
            
            for tool in tools:
                if st.sidebar.button(
                    f"{tool['icon']} {tool['title']}", 
                    key=tool['key'], 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.auth_mode = tool['mode']
                    st.rerun()
            
            st.sidebar.markdown('<div class="sidebar-section-label">Manage</div>', unsafe_allow_html=True)
            
            manage_tools = [
                {"icon": "👥", "title": "Student Dashboard", "desc": "Track student learning", "mode": "student_dashboard", "key": "sb_sd"},
                {"icon": "📝", "title": "Planning Notes", "desc": "Save lesson plans", "mode": "planning_notes", "key": "sb_pn"},
                {"icon": "👤", "title": "Create Student", "desc": "Add new student", "mode": "create_student", "key": "sb_cs"},
            ]
            
            # Add School Admin button for school admins
            if st.session_state.get('user_role') == 'school_admin':
                manage_tools.insert(0, {"icon": "🏫", "title": "School Admin", "desc": "Manage educators", "mode": "school_admin_dashboard", "key": "sb_school"})
            
            for tool in manage_tools:
                if st.sidebar.button(
                    f"{tool['icon']} {tool['title']}", 
                    key=tool['key'], 
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.auth_mode = tool['mode']
                    st.rerun()
        
        st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.sidebar.divider()
        
        if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
            logout()
        
        # My Data expander
        with st.sidebar.expander("📊 My Data"):
            st.markdown("*View and export your data*")
            if st.button("View Data Dashboard", key="view_data_btn", use_container_width=True):
                st.session_state.auth_mode = "data_access"
                st.rerun()
            
            st.markdown("---")
            st.caption("Export all your data (GDPR compliant):")
            
            if 'gdpr_export_ready' not in st.session_state:
                st.session_state.gdpr_export_ready = False
                st.session_state.gdpr_export_data = None
            
            if not st.session_state.gdpr_export_ready:
                if st.button("📦 Prepare Export", key="gdpr_prepare_btn", use_container_width=True):
                    with st.spinner("Gathering your data..."):
                        export_json = export_user_data_gdpr()
                        if export_json:
                            st.session_state.gdpr_export_data = export_json
                            st.session_state.gdpr_export_ready = True
                            st.rerun()
                        else:
                            st.error("Could not prepare export. Please try again.")
            else:
                export_data = st.session_state.get('gdpr_export_data')
                if export_data:
                    user_type = "student" if st.session_state.get('is_student') else "educator"
                    filename = f"guide_data_export_{user_type}_{datetime.now().strftime('%Y%m%d')}.json"
                    
                    st.download_button(
                        label="📥 Download My Data",
                        data=export_data,
                        file_name=filename,
                        mime="application/json",
                        key="download_gdpr_data",
                        use_container_width=True
                    )
                    st.caption("✅ Export ready!")
                    if st.button("🔄 Refresh Export", key="gdpr_refresh_btn", use_container_width=True):
                        st.session_state.gdpr_export_ready = False
                        st.session_state.gdpr_export_data = None
                        st.rerun()
                else:
                    st.error("Export data not available. Please prepare again.")
        
        # Account Settings expander
        with st.sidebar.expander("⚙️ Account Settings"):
            st.markdown("*Manage your account*")
            if st.button("Open Account Settings", key="open_account_btn", use_container_width=True):
                st.session_state.auth_mode = "account_deletion"
                st.rerun()