from datetime import datetime
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.message import Message as MessageModel
from app.models.message_evaluation import MessageEvaluation
from app.models.thread import Thread as ThreadModel
from app.models.upload_batch import UploadBatch
from app.middleware.clerk_auth import get_current_user
from app.services.vector_service import vector_service
from app.services.storage_service import storage_service

router = APIRouter()
logger = logging.getLogger(__name__)


def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin():
        raise HTTPException(403, "Admin access required")
    return user


@router.get("/users")
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter_by(deleted_at=None).order_by(User.created_at.desc()).all()

    clerk_profiles = _fetch_clerk_profiles([u.clerk_user_id for u in users if u.clerk_user_id])

    result = []
    for u in users:
        clerk = clerk_profiles.get(u.clerk_user_id, {}) if u.clerk_user_id else {}
        result.append({
            "id": str(u.id),
            "email": u.email or clerk.get("email", ""),
            "name": clerk.get("name", ""),
            "role": u.role,
            "created_at": u.created_at.isoformat(),
        })
    return {"users": result}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if str(admin.id) == user_id:
        raise HTTPException(400, "Cannot delete yourself")

    target = db.query(User).filter_by(id=user_id, deleted_at=None).first()
    if not target:
        raise HTTPException(404, "User not found")

    docs = db.query(Document).filter_by(owner_user_id=user_id).all()
    for doc in docs:
        _hard_delete_document(doc, db)

    db.query(UploadBatch).filter_by(user_id=user_id).delete(synchronize_session=False)

    db.delete(target)
    db.commit()

    try:
        vector_service.delete_by_user(user_id)
    except Exception as e:
        logger.warning(f"Failed to delete Chroma vectors for user {user_id}: {e}")

    user_prefix = f"users/{user_id}/"
    try:
        storage_service.delete_objects_by_prefix(user_prefix)
    except Exception as e:
        logger.warning(f"Failed to delete B2 objects for user {user_id}: {e}")

    if target.clerk_user_id:
        try:
            settings = get_settings()
            with httpx.Client(timeout=10) as client:
                client.delete(
                    f"https://api.clerk.com/v1/users/{target.clerk_user_id}",
                    headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                )
                logger.info(f"Deleted Clerk user {target.clerk_user_id}")
        except Exception as e:
            logger.warning(f"Clerk API unreachable for user {target.clerk_user_id}: {e}")

    return {"message": "User and all associated data deleted"}


@router.get("/documents")
def list_all_documents(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).filter_by(deleted_at=None).order_by(Document.created_at.desc()).all()
    result = []
    for doc in docs:
        job = db.query(IngestionJob).filter_by(document_id=doc.id).order_by(
            IngestionJob.created_at.desc()
        ).first()
        result.append({
            "id": str(doc.id),
            "title": doc.title,
            "original_filename": doc.original_filename,
            "file_type": doc.file_type,
            "scope": doc.scope,
            "retrieval_type": doc.retrieval_type,
            "ingestion_status": job.status if job else None,
            "created_at": doc.created_at.isoformat(),
        })
    return {"documents": result, "total": len(result)}


@router.delete("/documents/{document_id}")
def admin_delete_document(
    document_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(id=document_id, deleted_at=None).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    _hard_delete_document(doc, db)
    db.commit()
    return {"message": "Document deleted"}


@router.get("/stats")
def admin_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).filter_by(deleted_at=None).count()
    total_docs = db.query(Document).filter_by(deleted_at=None).count()
    total_jobs = db.query(IngestionJob).count()
    done_jobs = db.query(IngestionJob).filter_by(status="DONE").count()
    failed_jobs = db.query(IngestionJob).filter_by(status="FAILED").count()

    return {
        "total_users": total_users,
        "total_documents": total_docs,
        "ingestion_jobs": {"total": total_jobs, "done": done_jobs, "failed": failed_jobs},
    }


def _hard_delete_document(doc: Document, db: Session) -> None:
    thread_ids = db.query(ThreadModel.id).filter_by(document_id=doc.id).all()
    if thread_ids:
        message_ids = db.query(MessageModel.id).filter(
            MessageModel.thread_id.in_([t[0] for t in thread_ids])
        ).all()
        if message_ids:
            db.query(MessageEvaluation).filter(
                MessageEvaluation.message_id.in_([m[0] for m in message_ids])
            ).delete(synchronize_session=False)
        db.query(MessageModel).filter(
            MessageModel.thread_id.in_([t[0] for t in thread_ids])
        ).delete(synchronize_session=False)
        db.query(ThreadModel).filter(ThreadModel.document_id == doc.id).delete(synchronize_session=False)

    db.query(IngestionJob).filter_by(document_id=doc.id).delete(synchronize_session=False)

    owner_prefix = f"users/{doc.owner_user_id}/documents/{doc.id}/"
    try:
        storage_service.delete_objects_by_prefix(owner_prefix)
    except Exception as e:
        logger.warning(f"Failed to delete B2 objects for document {doc.id}: {e}")

    try:
        vector_service.delete_by_document(doc.id)
    except Exception as e:
        logger.warning(f"Failed to delete Chroma vectors for document {doc.id}: {e}")

    db.delete(doc)


def _fetch_clerk_profiles(clerk_user_ids: list[str]) -> dict[str, dict]:
    if not clerk_user_ids:
        return {}
    settings = get_settings()
    profiles = {}
    try:
        with httpx.Client(timeout=10) as client:
            for cid in clerk_user_ids:
                try:
                    resp = client.get(
                        f"https://api.clerk.com/v1/users/{cid}",
                        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        emails = data.get("email_addresses", [])
                        primary_email = emails[0].get("email_address", "") if emails else ""
                        name_parts = [data.get("first_name", ""), data.get("last_name", "")]
                        name = " ".join(p for p in name_parts if p).strip()
                        profiles[cid] = {"email": primary_email, "name": name or primary_email}
                except Exception:
                    pass
    except Exception:
        pass
    return profiles
