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

    student = create_student_with_consent(
        db,
        username=req.username,
        password=req.password,
        full_name=req.full_name,
        educator_id=user.id,
        age_group=req.age_group,
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

    students = get_educator_accessible_students(db, user.id)
    if not any(s.id == student_id for s in students):
        raise HTTPException(status_code=404, detail="Student not found or access denied")

    activities = db_get_activities(db, student_id, limit=limit)
    return [
        {
            "id": a.id,
            "activity_type": a.activity_type,
            "prompt_text": a.prompt_text,
            "response_text": a.response_text,
            "session_id": a.session_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]


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
