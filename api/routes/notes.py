from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.db import get_db, User, PlanningNote, GreatStory
from api.deps import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])


class CreateNoteRequest(BaseModel):
    title: str
    content: str = ""
    chapters: Optional[str] = None
    images: Optional[str] = None
    materials: Optional[str] = None


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    chapters: Optional[str] = None
    images: Optional[str] = None
    materials: Optional[str] = None


class SaveStoryRequest(BaseModel):
    title: str
    theme: str
    content: str
    age_group: Optional[str] = None
    keywords: Optional[str] = None


class UpdateStoryRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    age_group: Optional[str] = None
    keywords: Optional[str] = None


@router.get("/")
@router.get("/planning")
def list_planning_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_planning_notes
    notes = get_educator_planning_notes(db, user.id)
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "chapters": n.chapters,
            "images": n.images,
            "materials": n.materials,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        }
        for n in notes
    ]


@router.post("/")
@router.post("/planning")
def create_planning_note(
    req: CreateNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import create_planning_note as db_create
    note = db_create(db, user.id, req.title, req.content, req.chapters, req.images, req.materials)
    return {
        "id": note.id,
        "title": note.title,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


@router.put("/planning/{note_id}")
@router.patch("/planning/{note_id}")
@router.put("/{note_id}")
@router.patch("/{note_id}")
def update_planning_note(
    note_id: int,
    req: UpdateNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(PlanningNote).filter(PlanningNote.id == note_id, PlanningNote.educator_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    from database import update_planning_note as db_update
    updated = db_update(db, note_id, title=req.title, content=req.content, chapters=req.chapters, images=req.images, materials=req.materials)
    return {"success": True, "id": updated.id if updated else note_id}


@router.delete("/planning/{note_id}")
@router.delete("/{note_id}")
def delete_planning_note(
    note_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = db.query(PlanningNote).filter(PlanningNote.id == note_id, PlanningNote.educator_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    from database import delete_planning_note as db_delete
    db_delete(db, note_id)
    return {"success": True}


@router.get("/stories")
def list_stories(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_educator_great_stories
    stories = get_educator_great_stories(db, user.id)
    return [
        {
            "id": s.id,
            "title": s.title,
            "theme": s.theme,
            "content": s.content,
            "age_group": s.age_group,
            "keywords": s.keywords,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in stories
    ]


@router.post("/stories")
def save_story(
    req: SaveStoryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import create_great_story
    story = create_great_story(db, user.id, req.title, req.theme, req.content, req.age_group, req.keywords)
    return {
        "id": story.id,
        "title": story.title,
        "created_at": story.created_at.isoformat() if story.created_at else None,
    }


@router.put("/stories/{story_id}")
def update_story(
    story_id: int,
    req: UpdateStoryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    story = db.query(GreatStory).filter(GreatStory.id == story_id, GreatStory.educator_id == user.id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    from database import update_great_story
    updated = update_great_story(db, story_id, title=req.title, content=req.content, age_group=req.age_group, keywords=req.keywords)
    return {"success": True, "id": updated.id if updated else story_id}


@router.delete("/stories/{story_id}")
def delete_story(
    story_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    story = db.query(GreatStory).filter(GreatStory.id == story_id, GreatStory.educator_id == user.id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    from database import delete_great_story
    delete_great_story(db, story_id)
    return {"success": True}
