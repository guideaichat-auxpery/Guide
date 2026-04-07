from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx

from api.db import get_db, User
from api.deps import get_current_user, get_current_user_or_student

router = APIRouter(prefix="/adaptive", tags=["adaptive"])

ADAPTIVE_SERVER = "http://localhost:3000"


class AdaptiveGenerateRequest(BaseModel):
    prompt: str
    subject: Optional[str] = None
    age_group: Optional[str] = None
    interface_type: Optional[str] = None


class AdaptiveMessageRequest(BaseModel):
    message: str
    subject: Optional[str] = None
    age_group: Optional[str] = None


class AdaptiveFeedbackRequest(BaseModel):
    session_id: str
    rating: int
    comment: Optional[str] = None


class TrendingRecordRequest(BaseModel):
    keyword: str
    subject: Optional[str] = None


@router.post("/generate")
async def adaptive_generate(
    req: AdaptiveGenerateRequest,
    identity: dict = Depends(get_current_user_or_student),
):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{ADAPTIVE_SERVER}/api/generate", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Adaptive learning server unavailable")


@router.post("/message")
async def adaptive_message(
    req: AdaptiveMessageRequest,
    identity: dict = Depends(get_current_user_or_student),
):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{ADAPTIVE_SERVER}/api/message", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Adaptive learning server unavailable")


@router.post("/feedback")
async def adaptive_feedback(
    req: AdaptiveFeedbackRequest,
    identity: dict = Depends(get_current_user_or_student),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ADAPTIVE_SERVER}/api/feedback", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Adaptive learning server unavailable")


@router.post("/trending/record")
async def trending_record(
    req: TrendingRecordRequest,
    user: User = Depends(get_current_user),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ADAPTIVE_SERVER}/api/trending/record", json=req.model_dump())
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Adaptive learning server unavailable")


@router.get("/weights/{subject}")
async def get_weights(
    subject: str,
    user: User = Depends(get_current_user),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ADAPTIVE_SERVER}/api/weights/{subject}")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Adaptive learning server unavailable")


@router.get("/health")
async def adaptive_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ADAPTIVE_SERVER}/health")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError:
        return {"status": "unavailable"}
