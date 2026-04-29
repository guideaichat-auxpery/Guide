from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from api.db import get_db, User, Student
from api.deps import get_current_user

router = APIRouter(prefix="/students", tags=["students"])


class CreateStudentRequest(BaseModel):
    username: str
    password: str
    full_name: str
    age_group: Optional[str] = None
    parent_name: Optional[str] = None
    parent_email: Optional[str] = None
    consent_method: Optional[str] = "educator_confirmed"


class UpdateStudentRequest(BaseModel):
    full_name: Optional[str] = None
    age_group: Optional[str] = None
    password: Optional[str] = None


class GrantAccessRequest(BaseModel):
    educator_email: str


def student_to_dict(s: Student, include_educator: bool = False):
    d = {
        "id": s.id,
        "username": s.username,
        "full_name": s.full_name,
        "age_group": s.age_group,
        "educator_id": s.educator_id,
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
    if include_educator and s.educator:
        d["educator_name"] = s.educator.full_name
        d["educator_email"] = s.educator.email
    return d


@router.get("/")
def list_students(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students
    students = get_educator_accessible_students(db, user.id)
    return [student_to_dict(s, include_educator=True) for s in students]


@router.post("/")
def create_student(
    req: CreateStudentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import create_student_with_consent, get_student_by_username

    existing = get_student_by_username(db, req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Guide is currently locked to the adolescent plane (Cycle 4, ages
    # 12-15). Whatever the client sends, students are always created in
    # this age band so downstream curriculum logic stays consistent.
    student = create_student_with_consent(
        db,
        username=req.username,
        password=req.password,
        full_name=req.full_name,
        educator_id=user.id,
        age_group="12-15",
        parent_name=req.parent_name,
        parent_email=req.parent_email,
        consent_method=req.consent_method,
    )
    if not student:
        raise HTTPException(status_code=500, detail="Failed to create student")

    return student_to_dict(student)


@router.get("/{student_id}")
def get_student(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students
    students = get_educator_accessible_students(db, user.id)
    for s in students:
        if s.id == student_id:
            return student_to_dict(s, include_educator=True)
    raise HTTPException(status_code=404, detail="Student not found or access denied")


@router.put("/{student_id}")
@router.patch("/{student_id}")
def update_student(
    student_id: int,
    req: UpdateStudentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.educator_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not your student")

    if req.full_name is not None:
        student.full_name = req.full_name
    # age_group is intentionally ignored — Guide is locked to Cycle 4
    # (12-15) for all students. Force-reset in case earlier records drifted.
    student.age_group = "12-15"
    if req.password is not None:
        import bcrypt
        student.password_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.commit()
    db.refresh(student)
    return student_to_dict(student)


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.educator_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not your student")

    from database import delete_student as db_delete_student
    success = db_delete_student(db, student_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete student")
    return {"success": True}


@router.get("/{student_id}/activities")
def get_student_activities(
    student_id: int,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students, get_student_activities as db_get_activities
    from api.db import ChatConversation

    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    activities = db_get_activities(db, student_id, limit=limit)

    session_ids = list({a.session_id for a in activities if a.session_id})
    convs_by_session: dict = {}
    if session_ids:
        convs = db.query(ChatConversation).filter(
            ChatConversation.session_id.in_(session_ids)
        ).all()
        convs_by_session = {c.session_id: c for c in convs}

    return [
        {
            "id": a.id,
            "activity_type": a.activity_type,
            "prompt_text": a.prompt_text,
            "response_text": a.response_text,
            "session_id": a.session_id,
            "subject": (convs_by_session.get(a.session_id).subject_tag if a.session_id and convs_by_session.get(a.session_id) else None),
            "session_title": (convs_by_session.get(a.session_id).title if a.session_id and convs_by_session.get(a.session_id) else None),
            "interface_type": (convs_by_session.get(a.session_id).interface_type if a.session_id and convs_by_session.get(a.session_id) else None),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]


@router.get("/{student_id}/chat-history")
def get_student_chat_history(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return chat sessions for a student that the requesting educator can access."""
    from database import get_educator_accessible_students, get_user_chat_conversations
    from api.db import ConversationHistory

    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    convs = get_user_chat_conversations(db, student_id=student_id)

    sessions = []
    for c in convs:
        msg_count = db.query(ConversationHistory).filter(
            ConversationHistory.session_id == c.session_id,
            ConversationHistory.interface_type == c.interface_type,
        ).count()
        last = db.query(ConversationHistory).filter(
            ConversationHistory.session_id == c.session_id,
            ConversationHistory.interface_type == c.interface_type,
        ).order_by(ConversationHistory.created_at.desc()).first()
        sessions.append({
            "id": c.session_id,
            "session_id": c.session_id,
            "title": c.title,
            "subject": c.subject_tag,
            "interface_type": c.interface_type,
            "message_count": msg_count,
            "last_message": (last.content[:160] if last and last.content else None),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })
    return sessions


@router.get("/{student_id}/chat-sessions/{session_id}/messages")
def get_student_chat_session_messages(
    student_id: int,
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full thread for a specific student chat session (educator view)."""
    from database import get_educator_accessible_students
    from api.db import ChatConversation, ConversationHistory

    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    conv = db.query(ChatConversation).filter(
        ChatConversation.session_id == session_id,
        ChatConversation.student_id == student_id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Chat session not found for this student")

    history = db.query(ConversationHistory).filter(
        ConversationHistory.session_id == session_id,
        ConversationHistory.interface_type == conv.interface_type,
    ).order_by(ConversationHistory.created_at.asc()).all()

    return {
        "session": {
            "id": conv.session_id,
            "session_id": conv.session_id,
            "title": conv.title,
            "subject": conv.subject_tag,
            "interface_type": conv.interface_type,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        },
        "messages": [
            {
                "id": h.id,
                "role": h.role,
                "content": h.content,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ],
    }


@router.get("/{student_id}/learning-journey")
def get_learning_journey(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students, get_student_learning_journey

    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    return get_student_learning_journey(db, student_id)


@router.post("/{student_id}/grant-access")
def grant_access(
    student_id: int,
    req: GrantAccessRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import grant_educator_access, get_user_by_email

    student = db.query(Student).filter(Student.id == student_id, Student.educator_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not your student")

    target_educator = get_user_by_email(db, req.educator_email)
    if not target_educator:
        raise HTTPException(status_code=404, detail="Educator not found")

    success, error = grant_educator_access(db, target_educator.id, student_id, user.id)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to grant access")

    return {"success": True}


@router.get("/{student_id}/consent")
def get_student_consent(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students
    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    from api.db import ParentalConsentRecord
    consents = db.query(ParentalConsentRecord).filter(
        ParentalConsentRecord.student_id == student_id,
    ).order_by(ParentalConsentRecord.consent_date.desc()).all()
    return [
        {
            "id": c.id,
            "parent_name": c.parent_name,
            "parent_email": c.parent_email,
            "consent_obtained": c.consent_obtained,
            "consent_date": c.consent_date.isoformat() if c.consent_date else None,
            "consent_method": c.consent_method,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
        }
        for c in consents
    ]


@router.get("/{student_id}/safety-alerts")
def get_student_safety_alerts(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_accessible_students
    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    from api.db import SafetyAlert
    alerts = db.query(SafetyAlert).filter(
        SafetyAlert.student_id == student_id,
    ).order_by(SafetyAlert.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "content_snippet": a.content_snippet,
            "severity": getattr(a, "severity", None),
            "is_reviewed": a.is_reviewed,
            "reviewed_by": a.reviewed_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.delete("/{student_id}/revoke-access/{educator_id}")
def revoke_access(
    student_id: int,
    educator_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import revoke_educator_access

    student = db.query(Student).filter(Student.id == student_id, Student.educator_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not your student")

    success, error = revoke_educator_access(db, educator_id, student_id, revoked_by=user.id)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to revoke access")

    return {"success": True}
