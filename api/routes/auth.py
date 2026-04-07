from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import re
import os

from api.db import get_db, User, Student, PersistentSession, School
from api.deps import get_current_session, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

EDUCATOR_SESSION_HOURS = 24
STUDENT_SESSION_HOURS = 8


class LoginRequest(BaseModel):
    email: str
    password: str


class StudentLoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    confirm_password: str
    agree_terms: bool = False


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class SchoolJoinRequest(BaseModel):
    invite_code: str
    email: str
    password: str
    full_name: str
    confirm_password: str
    agree_terms: bool = False


class SchoolSetupRequest(BaseModel):
    setup_token: str
    admin_email: str
    admin_password: str
    admin_name: str
    confirm_password: str


class AdminResetPasswordRequest(BaseModel):
    user_email: str
    new_password: str


class AdminLookupRequest(BaseModel):
    email: str


def validate_email_format(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str):
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"


@router.post("/login")
def login_unified(req: LoginRequest, db: Session = Depends(get_db)):
    from database import authenticate_user, check_login_rate_limit, record_login_attempt, clear_login_attempts, create_persistent_session

    if not validate_email_format(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    is_locked, remaining_seconds, failed_count = check_login_rate_limit(db, req.email)
    if is_locked:
        minutes = remaining_seconds // 60 + 1
        raise HTTPException(status_code=429, detail=f"Account locked. Try again in {minutes} minute(s).")

    user = authenticate_user(db, req.email, req.password)
    if not user:
        record_login_attempt(db, req.email, attempt_type="educator", success=False)
        remaining = 5 - failed_count - 1
        raise HTTPException(status_code=401, detail=f"Invalid email or password. {max(remaining,0)} attempt(s) remaining.")

    clear_login_attempts(db, req.email)

    token = create_persistent_session(db, user_id=user.id, user_type="educator", duration_hours=EDUCATOR_SESSION_HOURS)
    if not token:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type,
            "is_admin": bool(getattr(user, "is_admin", False)),
            "role": getattr(user, "role", "individual"),
            "school_id": getattr(user, "school_id", None),
            "institution_name": getattr(user, "institution_name", None),
        },
    }


@router.post("/login/educator")
def login_educator(req: LoginRequest, db: Session = Depends(get_db)):
    from database import authenticate_user, check_login_rate_limit, record_login_attempt, clear_login_attempts, create_persistent_session

    if not validate_email_format(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    is_locked, remaining_seconds, failed_count = check_login_rate_limit(db, req.email)
    if is_locked:
        minutes = remaining_seconds // 60 + 1
        raise HTTPException(status_code=429, detail=f"Account locked. Try again in {minutes} minute(s).")

    user = authenticate_user(db, req.email, req.password)
    if not user:
        record_login_attempt(db, req.email, attempt_type="educator", success=False)
        remaining = 5 - failed_count - 1
        raise HTTPException(status_code=401, detail=f"Invalid email or password. {max(remaining,0)} attempt(s) remaining.")

    clear_login_attempts(db, req.email)

    token = create_persistent_session(db, user_id=user.id, user_type="educator", duration_hours=EDUCATOR_SESSION_HOURS)
    if not token:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type,
            "is_admin": bool(getattr(user, "is_admin", False)),
            "role": getattr(user, "role", "individual"),
            "school_id": getattr(user, "school_id", None),
            "institution_name": getattr(user, "institution_name", None),
        },
    }


@router.post("/login/student")
def login_student(req: StudentLoginRequest, db: Session = Depends(get_db)):
    from database import authenticate_student, check_login_rate_limit, record_login_attempt, clear_login_attempts, create_persistent_session

    is_locked, remaining_seconds, failed_count = check_login_rate_limit(db, req.username)
    if is_locked:
        minutes = remaining_seconds // 60 + 1
        raise HTTPException(status_code=429, detail=f"Account locked. Try again in {minutes} minute(s).")

    student = authenticate_student(db, req.username, req.password)
    if not student:
        record_login_attempt(db, req.username, attempt_type="student", success=False)
        remaining = 5 - failed_count - 1
        raise HTTPException(status_code=401, detail=f"Invalid username or password. {max(remaining,0)} attempt(s) remaining.")

    clear_login_attempts(db, req.username)

    token = create_persistent_session(db, student_id=student.id, user_type="student", duration_hours=STUDENT_SESSION_HOURS)
    if not token:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return {
        "token": token,
        "user": {
            "id": student.id,
            "username": student.username,
            "full_name": student.full_name,
            "age_group": student.age_group,
            "educator_id": student.educator_id,
            "is_student": True,
        },
    }


@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    from database import create_user, get_user_by_email, record_consent

    if not req.agree_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms and conditions")
    if not validate_email_format(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    valid, msg = validate_password_strength(req.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    existing = get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = create_user(db, req.email, req.password, req.full_name, "educator")
    record_consent(db, user_id=user.id, consent_type="data_collection", policy_version="1.0")
    record_consent(db, user_id=user.id, consent_type="privacy_policy", policy_version="1.0")

    return {"success": True, "user_id": user.id, "message": "Account created successfully"}


@router.post("/logout")
def logout(
    session: PersistentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    from database import invalidate_persistent_session
    invalidate_persistent_session(db, session.token)
    return {"success": True}


@router.get("/session")
def get_session(
    session: PersistentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    if session.user_type == "educator" and session.user_id:
        user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
        if user:
            return {
                "authenticated": True,
                "user_type": "educator",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_admin": bool(getattr(user, "is_admin", False)),
                    "role": getattr(user, "role", "individual"),
                    "school_id": getattr(user, "school_id", None),
                    "institution_name": getattr(user, "institution_name", None),
                },
            }
    elif session.user_type == "student" and session.student_id:
        student = db.query(Student).filter(Student.id == session.student_id, Student.is_active == True).first()
        if student:
            return {
                "authenticated": True,
                "user_type": "student",
                "user": {
                    "id": student.id,
                    "username": student.username,
                    "full_name": student.full_name,
                    "age_group": student.age_group,
                    "educator_id": student.educator_id,
                    "is_student": True,
                },
            }
    raise HTTPException(status_code=401, detail="Invalid session")


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    from database import get_user_by_email, check_login_rate_limit, record_login_attempt
    import time
    import random
    import hashlib
    import secrets

    start = time.time()

    if not validate_email_format(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    reset_id = f"reset:{req.email.lower()}"
    is_locked, remaining, _ = check_login_rate_limit(db, reset_id, max_attempts=3, lockout_minutes=15)
    if is_locked:
        raise HTTPException(status_code=429, detail="Too many reset requests. Please wait before trying again.")

    record_login_attempt(db, reset_id, attempt_type="reset", success=False)

    user = get_user_by_email(db, req.email)
    if user:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        from sqlalchemy import text as sa_text
        db.execute(sa_text("UPDATE password_reset_tokens SET is_valid = FALSE WHERE user_id = :uid"), {"uid": user.id})
        expires = datetime.utcnow() + timedelta(hours=1)
        db.execute(
            sa_text("INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (:uid, :th, :exp)"),
            {"uid": user.id, "th": token_hash, "exp": expires},
        )
        db.commit()

        base_url = os.getenv("GUIDE_APP_URL", "https://guide.auxpery.com.au")
        reset_url = f"{base_url}/?reset_token={token}"
        try:
            import resend
            resend.api_key = os.environ.get("RESEND_API_KEY", "")
            if resend.api_key:
                greeting = f"Hi {user.full_name}," if user.full_name else "Hi,"
                html_body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
                    <h2 style="color:#2E8B57;">Reset Your Password</h2>
                    <p>{greeting}</p>
                    <p>Click below to reset your Guide password.</p>
                    <p style="text-align:center;margin:2rem 0;">
                        <a href="{reset_url}" style="background:#2E8B57;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">Reset Password</a>
                    </p>
                    <p style="color:#666;font-size:0.9rem;">This link expires in 1 hour.</p>
                </div>"""
                resend.Emails.send({
                    "from": "Guide <guide@auxpery.com.au>",
                    "to": [user.email],
                    "subject": "Reset your Guide password",
                    "html": html_body,
                })
        except Exception:
            pass

    elapsed = time.time() - start
    target = 1.0 + random.uniform(0, 0.5)
    if elapsed < target:
        time.sleep(target - elapsed)

    return {"success": True, "message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    import hashlib
    import bcrypt

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    valid, msg = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    from sqlalchemy import text as sa_text

    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    result = db.execute(
        sa_text("""UPDATE password_reset_tokens SET is_valid = FALSE, used_at = NOW()
                   WHERE token_hash = :th AND is_valid = TRUE AND expires_at > NOW()
                   RETURNING user_id"""),
        {"th": token_hash},
    ).fetchone()

    if not result:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used reset link")

    user_id = result[0]
    new_hash = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.execute(sa_text("UPDATE users SET password_hash = :ph WHERE id = :uid"), {"ph": new_hash, "uid": user_id})
    db.commit()

    return {"success": True, "message": "Password reset successfully"}


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import bcrypt

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    valid, msg = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    if not bcrypt.checkpw(req.current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.password_hash = new_hash
    db.commit()

    return {"success": True, "message": "Password updated successfully"}


@router.post("/school-join")
def school_join(req: SchoolJoinRequest, db: Session = Depends(get_db)):
    from database import (
        get_school_by_invite_code, add_educator_to_school,
        school_has_available_licenses, is_school_subscription_active,
        create_user, get_user_by_email, authenticate_user,
        record_consent, create_persistent_session,
    )

    if not req.agree_terms:
        raise HTTPException(status_code=400, detail="You must agree to the terms and conditions")
    if not validate_email_format(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    school = get_school_by_invite_code(db, req.invite_code)
    if not school:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if not is_school_subscription_active(school):
        raise HTTPException(status_code=403, detail="School subscription is not active")
    if not school_has_available_licenses(db, school.id):
        raise HTTPException(status_code=403, detail="School has reached its license limit")

    existing = get_user_by_email(db, req.email)
    if existing:
        authed = authenticate_user(db, req.email, req.password)
        if not authed:
            raise HTTPException(status_code=401, detail="Account exists. Enter correct password to join.")
        if existing.school_id and existing.school_id != school.id:
            raise HTTPException(status_code=409, detail="Account already associated with another school")
        if existing.school_id != school.id:
            success, error = add_educator_to_school(db, existing.id, school.id, "school_educator")
            if not success:
                raise HTTPException(status_code=500, detail=error or "Failed to join school")
        user = existing
    else:
        valid, msg = validate_password_strength(req.password)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)
        user = create_user(db, req.email, req.password, req.full_name, "educator")
        add_educator_to_school(db, user.id, school.id, "school_educator")
        record_consent(db, user_id=user.id, consent_type="data_collection", policy_version="1.0")
        record_consent(db, user_id=user.id, consent_type="privacy_policy", policy_version="1.0")

    token = create_persistent_session(db, user_id=user.id, user_type="educator", duration_hours=EDUCATOR_SESSION_HOURS)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": getattr(user, "role", "school_educator"),
            "school_id": school.id,
            "school_name": school.name,
        },
    }


@router.post("/admin/reset-password")
def admin_reset_password(
    req: AdminResetPasswordRequest,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not getattr(admin, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    valid, msg = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    from database import get_user_by_email
    import bcrypt

    target = get_user_by_email(db, req.user_email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    new_hash = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    target.password_hash = new_hash
    db.commit()

    return {"success": True, "message": f"Password reset for {target.email}"}


@router.post("/admin/lookup")
def admin_lookup_user(
    req: AdminLookupRequest,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not getattr(admin, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from database import get_user_by_email
    target = get_user_by_email(db, req.email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": target.id,
        "email": target.email,
        "full_name": target.full_name,
        "user_type": target.user_type,
        "is_admin": bool(getattr(target, "is_admin", False)),
        "role": getattr(target, "role", "individual"),
        "school_id": getattr(target, "school_id", None),
        "is_active": target.is_active,
        "created_at": target.created_at.isoformat() if target.created_at else None,
    }


@router.post("/school-setup")
def school_setup(req: SchoolSetupRequest, db: Session = Depends(get_db)):
    from database import create_persistent_session
    import hashlib
    from sqlalchemy import text as sa_text

    if not validate_email_format(req.admin_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if req.admin_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    valid, msg = validate_password_strength(req.admin_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    token_hash = hashlib.sha256(req.setup_token.encode()).hexdigest()
    result = db.execute(
        sa_text("""SELECT id FROM school_setup_tokens
                   WHERE token_hash = :th AND is_valid = TRUE AND expires_at > NOW()"""),
        {"th": token_hash},
    ).fetchone()

    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired setup token")

    school_id = result[0]

    db.execute(
        sa_text("UPDATE school_setup_tokens SET is_valid = FALSE, used_at = NOW() WHERE token_hash = :th"),
        {"th": token_hash},
    )

    from database import get_user_by_email, create_user, add_educator_to_school, record_consent

    existing = get_user_by_email(db, req.admin_email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = create_user(db, req.admin_email, req.admin_password, req.admin_name, "educator")
    add_educator_to_school(db, user.id, school_id, "school_admin")
    record_consent(db, user_id=user.id, consent_type="data_collection", policy_version="1.0")
    record_consent(db, user_id=user.id, consent_type="privacy_policy", policy_version="1.0")

    token = create_persistent_session(db, user_id=user.id, user_type="educator", duration_hours=EDUCATOR_SESSION_HOURS)

    school = db.query(School).filter(School.id == school_id).first()

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": "school_admin",
            "school_id": school_id,
            "school_name": school.name if school else None,
        },
    }
