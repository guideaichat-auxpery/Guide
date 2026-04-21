from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from api.db import get_db, User, Student
from api.deps import get_current_user, get_current_student, get_current_user_or_student

router = APIRouter(prefix="/tools", tags=["tools"])

PD_EXPERT_EMAILS = ["guideaichat@gmail.com", "ben@hmswairoa.net"]


class ChatRequest(BaseModel):
    message: str
    interface_type: str = "companion"
    session_id: Optional[str] = None
    age_group: Optional[str] = None
    subject: Optional[str] = None
    year_level: Optional[str] = None
    curriculum_type: Optional[str] = "Blended"
    conversation_id: Optional[int] = None


class CompanionChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    age_group: Optional[str] = None
    curriculum_type: Optional[str] = "Blended"
    year_level: Optional[str] = None
    subject: Optional[str] = None
    conversation_id: Optional[int] = None


class ImaginariumChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    age_group: Optional[str] = None
    conversation_id: Optional[int] = None


class PdExpertChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class LessonPlanRequest(BaseModel):
    topic: str
    age_group: str = "9-12"
    planning_type: str = "lesson_plan"
    curriculum_type: str = "Blended"
    year_level: Optional[str] = None
    subject: Optional[str] = None
    duration: Optional[str] = None
    additional_context: Optional[str] = None


class AlignRequest(BaseModel):
    topic: Optional[str] = None
    content: Optional[str] = None
    age_group: str = "9-12"
    year_level: Optional[str] = None
    subject: Optional[str] = None
    duration: Optional[str] = None
    additional_context: Optional[str] = None


class DifferentiateRequest(BaseModel):
    topic: Optional[str] = None
    lesson_description: Optional[str] = None
    class_composition: Optional[str] = None
    focus_area: Optional[str] = None
    age_group: str = "9-12"
    subject: Optional[str] = None
    duration: Optional[str] = None
    additional_context: Optional[str] = None


class GreatStoryRequest(BaseModel):
    theme: str
    age_group: str = "9-12"
    format_style: Optional[str] = None


class CreateConversationRequest(BaseModel):
    interface_type: str = "companion"
    title: Optional[str] = None


class RenameConversationRequest(BaseModel):
    title: str


def _ownership_check(conv, user_id, student_id):
    if user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if student_id and conv.student_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")


def _identity_ids(identity):
    user_id = identity["id"] if identity["type"] == "educator" else None
    student_id = identity["id"] if identity["type"] == "student" else None
    return user_id, student_id


@router.post("/chat")
def chat(
    req: ChatRequest,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api

    is_student = identity["type"] == "student"
    user_id, student_id = _identity_ids(identity)

    messages = [{"role": "user", "content": req.message}]

    if req.session_id:
        from api.db import ChatConversation
        conv = db.query(ChatConversation).filter(
            ChatConversation.session_id == req.session_id,
            ChatConversation.is_active == True,
        ).first()
        if conv:
            _ownership_check(conv, user_id, student_id)

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


@router.post("/companion/chat")
def companion_chat(
    req: CompanionChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api, get_age_appropriate_companion_prompt

    messages = [{"role": "user", "content": req.message}]

    if req.session_id:
        from api.db import ChatConversation
        conv = db.query(ChatConversation).filter(
            ChatConversation.session_id == req.session_id,
            ChatConversation.is_active == True,
        ).first()
        if conv:
            _ownership_check(conv, user.id, None)

        from database import get_conversation_history
        history = get_conversation_history(db, req.session_id, "companion", limit=20)
        if history:
            prev_messages = [{"role": h.role, "content": h.content} for h in history]
            messages = prev_messages + messages

    system_prompt = get_age_appropriate_companion_prompt(req.age_group)

    result = call_openai_api(
        messages=messages,
        max_tokens=4000,
        system_prompt=system_prompt,
        is_student=False,
        age_group=req.age_group,
        interface_type="companion",
        curriculum_type=req.curriculum_type,
        year_level=req.year_level,
        subject=req.subject,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate response")

    if req.session_id:
        from database import save_conversation_message
        save_conversation_message(db, req.session_id, "companion", "user", req.message, user_id=user.id)
        save_conversation_message(db, req.session_id, "companion", "assistant", result, user_id=user.id)

    return {"response": result, "session_id": req.session_id}


@router.post("/imaginarium/chat")
def imaginarium_chat(
    req: ImaginariumChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api

    messages = [{"role": "user", "content": req.message}]

    if req.session_id:
        from api.db import ChatConversation
        conv = db.query(ChatConversation).filter(
            ChatConversation.session_id == req.session_id,
            ChatConversation.is_active == True,
        ).first()
        if conv:
            _ownership_check(conv, user.id, None)

        from database import get_conversation_history
        history = get_conversation_history(db, req.session_id, "imaginarium", limit=20)
        if history:
            prev_messages = [{"role": h.role, "content": h.content} for h in history]
            messages = prev_messages + messages

    result = call_openai_api(
        messages=messages,
        max_tokens=4000,
        is_student=False,
        age_group=req.age_group,
        interface_type="imaginarium",
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate response")

    if req.session_id:
        from database import save_conversation_message
        save_conversation_message(db, req.session_id, "imaginarium", "user", req.message, user_id=user.id)
        save_conversation_message(db, req.session_id, "imaginarium", "assistant", result, user_id=user.id)

    return {"response": result, "session_id": req.session_id}


@router.post("/pd-expert/chat")
def pd_expert_chat(
    req: PdExpertChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.email not in PD_EXPERT_EMAILS:
        raise HTTPException(status_code=403, detail="PD Expert access is restricted")

    from utils import call_pd_expert
    import openai
    import os

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    result = call_pd_expert(user.email, req.message, client)

    if not result or not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate PD Expert response"))

    response_text = result.get("response", "")

    if req.session_id:
        from database import save_conversation_message
        save_conversation_message(db, req.session_id, "pd_expert", "user", req.message, user_id=user.id)
        save_conversation_message(db, req.session_id, "pd_expert", "assistant", response_text, user_id=user.id)

    return {"response": response_text, "session_id": req.session_id}


@router.post("/lesson-plan")
def generate_lesson_plan(
    req: LessonPlanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api, get_age_appropriate_lesson_planning_prompt

    # Pass through the user's explicit year level if provided; otherwise leave
    # it as None so call_openai_api can pull curriculum context across the full
    # age-group range (e.g. Year 4–6 for ages 9–12).
    year_level = req.year_level

    prompt_parts = [f"Topic: {req.topic}"]
    if req.subject:
        prompt_parts.append(f"Subject area: {req.subject}")
    if req.duration:
        prompt_parts.append(f"Duration: {req.duration} minutes")
    if req.additional_context:
        prompt_parts.append(f"Additional context:\n{req.additional_context}")
    messages = [{"role": "user", "content": "\n".join(prompt_parts)}]

    system_prompt = get_age_appropriate_lesson_planning_prompt(req.age_group)

    result = call_openai_api(
        messages=messages,
        max_tokens=8000,
        system_prompt=system_prompt,
        is_student=False,
        age_group=req.age_group,
        interface_type="lesson_planning",
        planning_type=req.planning_type,
        curriculum_type=req.curriculum_type,
        year_level=year_level,
        subject=req.subject,
        use_conversation_history=False,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate lesson plan")

    return {"content": result}


@router.post("/align")
def align_lesson_plan(
    req: AlignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api, get_alignment_system_prompt

    system_prompt = get_alignment_system_prompt(req.age_group)
    if req.content:
        user_content = req.content
    else:
        parts = []
        if req.topic:
            parts.append(f"Topic: {req.topic}")
        if req.subject:
            parts.append(f"Subject area: {req.subject}")
        if req.duration:
            parts.append(f"Duration: {req.duration} minutes")
        if req.additional_context:
            parts.append(f"Additional context:\n{req.additional_context}")
        if not parts:
            raise HTTPException(status_code=422, detail="Provide a topic or content to align")
        user_content = "\n".join(parts)
    messages = [{"role": "user", "content": user_content}]

    result = call_openai_api(
        messages=messages,
        max_tokens=6000,
        system_prompt=system_prompt,
        is_student=False,
        age_group=req.age_group,
        interface_type="align",
        year_level=req.year_level,
        subject=req.subject,
        use_conversation_history=False,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate alignment analysis")

    return {"content": result}


@router.post("/differentiate")
def differentiate_lesson_plan(
    req: DifferentiateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from utils import call_openai_api, get_differentiation_system_prompt

    system_prompt = get_differentiation_system_prompt(req.age_group)

    prompt_parts: List[str] = []
    if req.lesson_description:
        prompt_parts.append(req.lesson_description)
    else:
        if req.topic:
            prompt_parts.append(f"Topic: {req.topic}")
        if req.subject:
            prompt_parts.append(f"Subject area: {req.subject}")
        if req.duration:
            prompt_parts.append(f"Duration: {req.duration} minutes")
        if req.additional_context:
            prompt_parts.append(f"Additional context:\n{req.additional_context}")
    if not prompt_parts:
        raise HTTPException(status_code=422, detail="Provide a topic or lesson description to differentiate")
    if req.class_composition:
        prompt_parts.append(f"\nClass Composition: {req.class_composition}")
    if req.focus_area:
        prompt_parts.append(f"\nFocus Area: {req.focus_area}")

    messages = [{"role": "user", "content": "\n".join(prompt_parts)}]

    result = call_openai_api(
        messages=messages,
        max_tokens=6000,
        system_prompt=system_prompt,
        is_student=False,
        age_group=req.age_group,
        interface_type="differentiate",
        use_conversation_history=False,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate differentiation strategies")

    return {"content": result}


@router.post("/great-story")
@router.post("/great-story/generate")
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


@router.get("/great-story")
def list_great_stories(
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


@router.get("/great-story/{story_id}")
def get_great_story(
    story_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from database import get_great_story as db_get
    from api.db import GreatStory
    story = db_get(db, story_id)
    if not story or story.educator_id != user.id:
        raise HTTPException(status_code=404, detail="Story not found")
    return {
        "id": story.id,
        "title": story.title,
        "theme": story.theme,
        "content": story.content,
        "age_group": story.age_group,
        "keywords": story.keywords,
        "created_at": story.created_at.isoformat() if story.created_at else None,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


@router.delete("/great-story/{story_id}")
def delete_great_story_tool(
    story_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from api.db import GreatStory
    story = db.query(GreatStory).filter(GreatStory.id == story_id, GreatStory.educator_id == user.id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    from database import delete_great_story
    delete_great_story(db, story_id)
    return {"success": True}


@router.get("/conversations")
def list_conversations(
    interface_type: str = "companion",
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from database import get_user_chat_conversations

    user_id, student_id = _identity_ids(identity)

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
    user_id, student_id = _identity_ids(identity)

    conv = db.query(ChatConversation).filter(
        ChatConversation.session_id == session_id,
        ChatConversation.is_active == True,
    ).first()
    if conv:
        _ownership_check(conv, user_id, student_id)

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


@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest,
    identity: dict = Depends(get_current_user_or_student),
    db: Session = Depends(get_db),
):
    from database import create_chat_conversation
    import uuid

    user_id, student_id = _identity_ids(identity)
    session_id = str(uuid.uuid4())
    title = req.title or "New Chat"

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
    user_id, student_id = _identity_ids(identity)

    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _ownership_check(conv, user_id, student_id)

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
    user_id, student_id = _identity_ids(identity)

    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _ownership_check(conv, user_id, student_id)

    conv.is_active = False
    db.commit()
    return {"success": True}
