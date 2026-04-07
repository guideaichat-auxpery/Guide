from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from api.db import get_db, User, Student, PersistentSession

security = HTTPBearer()


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    session = (
        db.query(PersistentSession)
        .filter(
            PersistentSession.token == token,
            PersistentSession.is_active == True,
            PersistentSession.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    session.last_activity = datetime.utcnow()
    db.commit()
    return session


def get_current_user(
    session: PersistentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    if session.user_type == "educator" and session.user_id:
        user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    raise HTTPException(status_code=401, detail="Not an educator session")


def get_current_student(
    session: PersistentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    if session.user_type == "student" and session.student_id:
        student = db.query(Student).filter(Student.id == session.student_id, Student.is_active == True).first()
        if not student:
            raise HTTPException(status_code=401, detail="Student not found or inactive")
        return student
    raise HTTPException(status_code=401, detail="Not a student session")


def get_current_user_or_student(
    session: PersistentSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    if session.user_type == "educator" and session.user_id:
        user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
        if user:
            return {"type": "educator", "user": user, "id": user.id}
    if session.user_type == "student" and session.student_id:
        student = db.query(Student).filter(Student.id == session.student_id, Student.is_active == True).first()
        if student:
            return {"type": "student", "user": student, "id": student.id}
    raise HTTPException(status_code=401, detail="Invalid session")


def require_admin(user: User = Depends(get_current_user)):
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
