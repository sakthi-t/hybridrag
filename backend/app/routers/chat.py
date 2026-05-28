import json
import time
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.thread import Thread
from app.models.message import Message
from app.middleware.clerk_auth import get_current_user
from app.services.rag_service import rag_service
from app.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


def _load_history(db: Session, thread_id: str, max_messages: int = 20) -> list[dict]:
    messages = (
        db.query(Message)
        .filter_by(thread_id=thread_id, deleted_at=None)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
        .all()
    )
    messages.reverse()
    return [{"role": m.role, "content": m.get_text()} for m in messages]


@router.post("/threads/{thread_id}/chat", response_model=ChatResponse)
def chat_non_streaming(
    thread_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = db.query(Thread).filter_by(id=thread_id, deleted_at=None).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if not thread.can_be_accessed_by(user):
        raise HTTPException(403, "Access denied")

    history = _load_history(db, thread_id)

    user_msg = Message(
        id=uuid4(),
        thread_id=thread.id,
        role="user",
        content_json={"text": body.message, "citations": [], "images": []},
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)

    result = rag_service.chat(
        query=body.message,
        document_id=str(thread.document_id),
        message_history=history,
        user_id=str(user.id),
    )

    assistant_msg = Message(
        id=uuid4(),
        thread_id=thread.id,
        role="assistant",
        content_json={
            "text": result["message"],
            "citations": result["context"]["chunks"],
            "images": [],
        },
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)

    thread.updated_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        message=result["message"],
        message_id=str(assistant_msg.id),
        context=result["context"],
        metrics=result["metrics"],
    )


@router.post("/threads/{thread_id}/chat/stream")
async def chat_streaming(
    thread_id: str,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = db.query(Thread).filter_by(id=thread_id, deleted_at=None).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if not thread.can_be_accessed_by(user):
        raise HTTPException(403, "Access denied")

    history = _load_history(db, thread_id)

    user_msg = Message(
        id=uuid4(),
        thread_id=thread.id,
        role="user",
        content_json={"text": body.message, "citations": [], "images": []},
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()

    stream, chunks, start_time, hyde_used = rag_service.chat_stream(
        query=body.message,
        document_id=str(thread.document_id),
        message_history=history,
        user_id=str(user.id),
    )

    full_response = ""
    assistant_msg_id = uuid4()
    citations = [{"page": c.get("page"), "text": c["text"]} for c in chunks]

    async def event_generator():
        nonlocal full_response

        yield f"data: {json.dumps({'type': 'context', 'context': {'chunks': citations}})}\n\n"

        try:
            for chunk in stream:
                if chunk.content:
                    content = chunk.content
                    full_response += content
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        latency_ms = int((time.time() - start_time) * 1000)

        # Save assistant message in a new DB session
        from app.database import SessionLocal
        save_db = SessionLocal()
        try:
            assistant_msg = Message(
                id=assistant_msg_id,
                thread_id=thread.id,
                role="assistant",
                content_json={
                    "text": full_response,
                    "citations": citations,
                    "images": [],
                },
                created_at=datetime.utcnow(),
            )
            save_db.add(assistant_msg)
            save_db.query(Thread).filter_by(id=thread.id).update(
                {"updated_at": datetime.utcnow()}
            )
            save_db.commit()
        finally:
            save_db.close()

        yield f"data: {json.dumps({'type': 'metrics', 'metrics': {'latency_ms': latency_ms, 'chunks_retrieved': len(chunks), 'hyde_used': hyde_used}})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_msg_id)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
