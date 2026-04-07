from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from api.db import get_db, User, Student
from api.deps import get_current_user, get_current_student, get_current_user_or_student

router = APIRouter(prefix="/tools", tags=["tools"])


class ChatRequest(BaseModel):
    message: str
    interface_type: str = "companion"
    session_id: Optional[str] = None
    age_group: Optional[str] = None
    subject: Optional[str] = None
    year_level: Optional[str] = None
    curriculum_type: Optional[str] = "Blended"
    conversation_id: Optional[int] = None


class LessonPlanRequest(BaseModel):
    topic: str
    age_group: str = "9-12"
    planning_type: str = "lesson_plan"
    curriculum_type: str = "Blended"
    year_level: Optional[str] = None
    subject: Optional[str] = None


class GreatStoryRequest(BaseModel):
    theme: str
    age_group: str = "9-12"
    format_style: Optional[str] = None


class ConversationListRequest(BaseModel):
    interface_type: str = "companion"


@router.post("/chat")
def chat(
    req: ChatRequest,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api

    is_student = identity["type"] == "student"
    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None

    messages = [{"role": "user", "content": req.message}]

    if req.session_id:
        from database import get_conversation_history
        history = get_conversation_history(db, req.session_id, req.interface_type, limit=20)
        if history:
            prev_messages = [{"role": h.role, "content": h.content} for h in history]
            messages = prev_messages + messages

    result = call_openai_api(
        messages=messages,
        max_tokens=4000,
        is_student=is_student,
        age_group=req.age_group,
        interface_type=req.interface_type,
        curriculum_type=req.curriculum_type,
        year_level=req.year_level,
        subject=req.subject,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate response")

    if req.session_id:
        from database import save_conversation_message
        save_conversation_message(db, req.session_id, req.interface_type, "user", req.message, user_id=user_id, student_id=student_id)
        save_conversation_message(db, req.session_id, req.interface_type, "assistant", result, user_id=user_id, student_id=student_id)

    return {"response": result, "session_id": req.session_id}


@router.post("/lesson-plan")
def generate_lesson_plan(
    req: LessonPlanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api, get_lesson_system_prompt, map_age_to_year_levels

    year_levels = map_age_to_year_levels(req.age_group)
    year_level = req.year_level or year_levels

    messages = [{"role": "user", "content": req.topic}]

    system_prompt = get_lesson_system_prompt(req.age_group, req.planning_type)

    result = call_openai_api(
        messages=messages,
        max_tokens=8000,
        system_prompt=system_prompt,
        is_student=False,
        age_group=req.age_group,
        interface_type="planning",
        curriculum_type=req.curriculum_type,
        year_level=year_level,
        subject=req.subject,
        use_conversation_history=False,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate lesson plan")

    return {"content": result}


@router.post("/great-story")
def generate_great_story(
    req: GreatStoryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api

    messages = [{"role": "user", "content": f"Create a Montessori Great Story about: {req.theme}"}]

    result = call_openai_api(
        messages=messages,
        max_tokens=6000,
        is_student=False,
        age_group=req.age_group,
        interface_type="great_stories",
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate story")

    return {"content": result}


@router.get("/conversations")
def list_conversations(
    interface_type: str = "companion",
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from database import get_user_chat_conversations

    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None

    convs = get_user_chat_conversations(db, user_id=user_id, student_id=student_id, interface_type=interface_type)
    return [
        {
            "id": c.id,
            "title": c.title,
            "session_id": c.session_id,
            "interface_type": c.interface_type,
            "subject_tag": getattr(c, "subject_tag", None),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@router.get("/conversations/{session_id}/messages")
def get_conversation_messages(
    session_id: str,
    interface_type: str = "companion",
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from api.db import ChatConversation
    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None

    conv = db.query(ChatConversation).filter(
        ChatConversation.session_id == session_id,
        ChatConversation.is_active == True,
    ).first()
    if conv:
        if user_id and conv.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if student_id and conv.student_id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")

    from database import get_conversation_history
    history = get_conversation_history(db, session_id, interface_type)
    return [
        {
            "id": h.id,
            "role": h.role,
            "content": h.content,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]


class CreateConversationRequest(BaseModel):
    interface_type: str = "companion"
    title: Optional[str] = None


class RenameConversationRequest(BaseModel):
    title: str


@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from database import create_chat_conversation
    import uuid

    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None
    session_id = str(uuid.uuid4())
    title = req.title or f"New Chat"

    conv = create_chat_conversation(
        db, title=title, session_id=session_id,
        interface_type=req.interface_type, user_id=user_id, student_id=student_id,
    )
    return {
        "id": conv.id,
        "session_id": conv.session_id,
        "title": conv.title,
        "interface_type": conv.interface_type,
    }


@router.put("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    req: RenameConversationRequest,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from api.db import ChatConversation
    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None

    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if student_id and conv.student_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conv.title = req.title
    db.commit()
    return {"success": True}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from api.db import ChatConversation
    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None

    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if student_id and conv.student_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conv.is_active = False
    db.commit()
    return {"success": True}
