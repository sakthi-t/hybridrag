from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.thread import Thread
from app.models.document import Document
from app.middleware.clerk_auth import get_current_user
from app.schemas.threads import (
    ThreadCreate,
    ThreadUpdate,
    ThreadResponse,
    ThreadListResponse,
    ThreadDetailResponse,
    MessageResponse,
)

router = APIRouter()


@router.post("", response_model=ThreadResponse)
def create_thread(
    body: ThreadCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(id=body.document_id, deleted_at=None).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.can_be_viewed_by(user):
        raise HTTPException(403, "Access denied")

    title = body.title or f"Chat about {doc.title}"
    thread = Thread(
        id=uuid4(),
        user_id=user.id,
        document_id=doc.id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    return ThreadResponse(
        id=str(thread.id),
        document_id=str(thread.document_id) if thread.document_id else None,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        message_count=0,
    )


@router.get("", response_model=ThreadListResponse)
def list_threads(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    threads = (
        db.query(Thread)
        .filter_by(user_id=user.id, deleted_at=None)
        .order_by(Thread.updated_at.desc())
        .all()
    )

    result = []
    for t in threads:
        msg_count = t.messages.filter_by(deleted_at=None).count()
        result.append(ThreadResponse(
            id=str(t.id),
            document_id=str(t.document_id) if t.document_id else None,
            title=t.title,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
            message_count=msg_count,
        ))

    return ThreadListResponse(threads=result, total=len(result))


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = db.query(Thread).filter_by(id=thread_id, deleted_at=None).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if not thread.can_be_accessed_by(user):
        raise HTTPException(403, "Access denied")

    from app.models.message import Message as MessageModel
    from app.models.message_evaluation import MessageEvaluation
    messages = (
        thread.messages.filter_by(deleted_at=None)
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    msg_list = []
    for m in messages:
        evals = list(m.evaluations)
        eval_data = None
        if evals:
            latest = evals[-1]
            rationale = latest.rationale_json or {}
            eval_data = {
                "faithfulness": latest.faithfulness_score,
                "citation": latest.citation_precision_score,
                "groundedness": latest.groundedness_score,
                "relevance": rationale.get("relevance", 0),
                "reasoning": rationale.get("reasoning", ""),
            }
        msg_list.append(MessageResponse(
            id=str(m.id),
            role=m.role,
            text=m.get_text(),
            citations=m.get_citations(),
            images=m.get_images(),
            created_at=m.created_at.isoformat(),
            evaluation=eval_data,
        ))

    return ThreadDetailResponse(
        id=str(thread.id),
        document_id=str(thread.document_id) if thread.document_id else None,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        messages=msg_list,
    )


@router.patch("/{thread_id}", response_model=ThreadResponse)
def update_thread(
    thread_id: str,
    body: ThreadUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = db.query(Thread).filter_by(id=thread_id, deleted_at=None).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if not thread.can_be_accessed_by(user):
        raise HTTPException(403, "Access denied")

    if body.title is not None:
        thread.title = body.title
        thread.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(thread)

    msg_count = thread.messages.filter_by(deleted_at=None).count()

    return ThreadResponse(
        id=str(thread.id),
        document_id=str(thread.document_id) if thread.document_id else None,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        message_count=msg_count,
    )


@router.delete("/{thread_id}")
def delete_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = db.query(Thread).filter_by(id=thread_id, deleted_at=None).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if not thread.can_be_accessed_by(user):
        raise HTTPException(403, "Access denied")

    from app.models.message import Message as MessageModel
    from app.models.message_evaluation import MessageEvaluation

    message_ids = db.query(MessageModel.id).filter_by(thread_id=thread_id).all()
    if message_ids:
        db.query(MessageEvaluation).filter(
            MessageEvaluation.message_id.in_([m[0] for m in message_ids])
        ).delete(synchronize_session=False)

    thread.messages.delete(synchronize_session=False)
    db.delete(thread)
    db.commit()
    return {"message": "Thread deleted"}
