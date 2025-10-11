import os
import streamlit as st
from database import get_db, get_user_by_email, create_user, record_consent

def check_replit_auth():
    """
    Check if user is authenticated via Replit Auth.
    Returns (is_authenticated, user_info_dict or None)
    """
    # Check for Replit environment variables
    replit_user = os.getenv('REPLIT_USER')
    replit_user_id = os.getenv('REPL_OWNER_ID')
    
    if replit_user and replit_user_id:
        # User is in a Replit environment
        # Create a unique email based on Replit username
        replit_email = f"{replit_user}@replit.user"
        
        return True, {
            'replit_username': replit_user,
            'replit_id': replit_user_id,
            'email': replit_email,
            'full_name': replit_user
        }
    
    return False, None

def authenticate_with_replit():
    """
    Authenticate or auto-create user account using Replit Auth.
    Returns True if authentication successful.
    """
    is_replit_auth, user_info = check_replit_auth()
    
    if not is_replit_auth or not user_info:
        return False
    
    db = get_db()
    if not db:
        st.error("Database connection not available")
        return False
    
    try:
        # Check if user exists
        user = get_user_by_email(db, user_info['email'])
        
        if not user:
            # Auto-create user account for Replit Auth
            user = create_user(
                db=db,
                email=user_info['email'],
                password=os.urandom(32).hex(),  # Random password (won't be used)
                full_name=user_info['full_name'],
                user_type='educator'
            )
            
            # Record consent for Replit Auth users
            record_consent(db, user_id=user.id, consent_type='data_collection', policy_version="1.0")
            record_consent(db, user_id=user.id, consent_type='overseas_transfer', policy_version="1.0")
            record_consent(db, user_id=user.id, consent_type='privacy_policy', policy_version="1.0")
            
            st.success(f"✨ Welcome to Guide, {user_info['full_name']}! Your account has been created automatically via Replit Auth.")
        
        # Set session state
        st.session_state.user_id = user.id
        st.session_state.user_type = user.user_type
        st.session_state.user_name = user.full_name
        st.session_state.user_email = user.email
        st.session_state.authenticated = True
        st.session_state.is_student = False
        st.session_state.replit_auth = True
        st.session_state.replit_username = user_info['replit_username']
        
        return True
        
    except Exception as e:
        st.error(f"Error during Replit Auth: {str(e)}")
        return False
    finally:
        db.close()

def show_replit_auth_status():
    """Display Replit Auth status in sidebar"""
    if st.session_state.get('replit_auth'):
        st.sidebar.success(f"🔐 Authenticated via Replit Auth")
        st.sidebar.caption(f"@{st.session_state.get('replit_username', 'unknown')}")
