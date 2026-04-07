from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from api.db import get_db, User, Student
from api.deps import get_current_user

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/export")
def export_user_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import (
        get_educator_accessible_students,
        get_educator_planning_notes,
        get_educator_great_stories,
        get_user_conversation_history,
    )

    students = get_educator_accessible_students(db, user.id)
    notes = get_educator_planning_notes(db, user.id)
    stories = get_educator_great_stories(db, user.id)
    conversations = get_user_conversation_history(db, user_id=user.id)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "students": [
            {
                "id": s.id,
                "username": s.username,
                "full_name": s.full_name,
                "age_group": s.age_group,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in students
        ],
        "planning_notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
        "great_stories": [
            {
                "id": s.id,
                "title": s.title,
                "theme": s.theme,
                "content": s.content,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in stories
        ],
        "conversations_count": len(conversations) if conversations else 0,
    }


@router.get("/retention-status")
def get_retention_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_data_retention_status
    return get_data_retention_status(db)


@router.get("/audit-logs")
def get_audit_logs(
    student_id: Optional[int] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_audit_logs
    logs = get_educator_audit_logs(db, educator_id=user.id, student_id=student_id, limit=limit)
    return [
        {
            "id": l.id,
            "action_type": l.action_type,
            "target_student_id": l.target_student_id,
            "target_entity": l.target_entity,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/safety-alerts")
def get_safety_alerts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_pending_safety_alerts
    alerts = get_pending_safety_alerts(db, user.id)
    return alerts


@router.post("/safety-alerts/{alert_id}/review")
def review_alert(
    alert_id: int,
    status: str = "reviewed",
    notes: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import review_safety_alert
    success = review_safety_alert(db, alert_id, user.id, status, notes)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to review alert")
    return {"success": True}
