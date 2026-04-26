from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.db import get_db, User, School
from api.deps import get_current_user, get_optional_user

router = APIRouter(prefix="/schools", tags=["schools"])


class CreateSchoolRequest(BaseModel):
    name: str
    contact_email: str
    contact_name: Optional[str] = None
    license_count: int = 10


@router.get("/mine")
def get_my_school(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not getattr(user, "school_id", None):
        return {"school": None}

    from database import get_school_by_id, get_school_educator_count
    school = get_school_by_id(db, user.school_id)
    if not school:
        return {"school": None}

    educator_count = get_school_educator_count(db, school.id)

    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "invite_code": school.invite_code,
            "license_count": school.license_count,
            "educator_count": educator_count,
            "subscription_status": school.subscription_status,
            "contact_email": school.contact_email,
            "contact_name": school.contact_name,
        }
    }


@router.post("/{school_id}/invite-code/rotate")
def rotate_invite_code(
    school_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if getattr(user, "school_id", None) != school_id:
        raise HTTPException(status_code=403, detail="Not a member of this school")
    if getattr(user, "role", "") != "school_admin":
        raise HTTPException(status_code=403, detail="School admin access required")

    from database import rotate_school_invite_code
    school = rotate_school_invite_code(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return {"invite_code": school.invite_code}


@router.get("/{school_id}/educators")
def list_school_educators(
    school_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if getattr(user, "school_id", None) != school_id:
        raise HTTPException(status_code=403, detail="Not a member of this school")
    if getattr(user, "role", "") != "school_admin":
        raise HTTPException(status_code=403, detail="School admin access required")

    from database import get_school_educators
    educators = get_school_educators(db, school_id)
    return [
        {
            "id": e.id,
            "email": e.email,
            "full_name": e.full_name,
            "role": getattr(e, "role", "school_educator"),
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in educators
    ]


@router.delete("/{school_id}/educators/{educator_id}")
def remove_educator(
    school_id: int,
    educator_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if getattr(user, "school_id", None) != school_id:
        raise HTTPException(status_code=403, detail="Not a member of this school")
    if getattr(user, "role", "") != "school_admin":
        raise HTTPException(status_code=403, detail="School admin access required")
    if educator_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    target = db.query(User).filter(User.id == educator_id).first()
    if not target or getattr(target, "school_id", None) != school_id:
        raise HTTPException(status_code=404, detail="Educator not found in this school")

    from database import remove_educator_from_school
    success = remove_educator_from_school(db, educator_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove educator")
    return {"success": True}


@router.post("/join")
def school_join(req: dict, db: Session = Depends(get_db)):
    from api.routes.auth import school_join as auth_school_join, SchoolJoinRequest
    join_req = SchoolJoinRequest(**req)
    return auth_school_join(join_req, db)


@router.post("/setup")
def school_setup(
    req: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    from api.routes.auth import school_setup as auth_school_setup, SchoolSetupRequest
    setup_req = SchoolSetupRequest(**req)
    return auth_school_setup(setup_req, db, current_user)
