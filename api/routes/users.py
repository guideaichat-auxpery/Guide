from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.db import get_db, User
from api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])


class UpdateEmailRequest(BaseModel):
    new_email: str
    current_password: str


class UpdateInstitutionRequest(BaseModel):
    institution_name: str


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
        "is_admin": bool(getattr(user, "is_admin", False)),
        "role": getattr(user, "role", "individual"),
        "school_id": getattr(user, "school_id", None),
        "institution_name": getattr(user, "institution_name", None),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/me/email")
def update_email(
    req: UpdateEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import update_user_email
    success, message = update_user_email(db, user.id, req.new_email, req.current_password, session_user_id=user.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@router.put("/me/institution")
def update_institution(
    req: UpdateInstitutionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import update_educator_institution, invalidate_educator_profile_cache
    success, auto_enabled = update_educator_institution(db, user.id, req.institution_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update institution")
    invalidate_educator_profile_cache(user.id)
    return {"success": True, "auto_enabled": auto_enabled}


@router.delete("/me")
def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import delete_educator
    success, error = delete_educator(db, user.id)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"success": True, "message": "Account deleted"}


@router.get("/profile")
def get_profile(
    user: User = Depends(get_current_user),
):
    from database import get_cached_educator_profile
    profile = get_cached_educator_profile(user.id)
    return profile or {}
