from datetime import datetime
from uuid import uuid4
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.upload_batch import UploadBatch
from app.models.ingestion_job import IngestionJob
from app.middleware.clerk_auth import get_current_user
from app.services.storage_service import storage_service
from app.services.vector_service import vector_service
from app.config import get_settings
from app.schemas.documents import (
    UploadBatchRequest,
    UploadBatchResponse,
    ConfirmBatchRequest,
    ConfirmBatchResponse,
    BatchStatusResponse,
    ConfirmTypeRequest,
    DocumentListResponse,
    DocumentResponse,
    IngestionStatusResponse,
)

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "text/csv": "csv",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
}


@router.post("/upload-batch", response_model=UploadBatchResponse)
async def create_upload_batch(
    request: UploadBatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(request.files) > settings.max_files_per_upload:
        raise HTTPException(400, f"Maximum {settings.max_files_per_upload} files allowed")

    total_size = sum(f.size_bytes for f in request.files)
    if total_size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"Total size exceeds {settings.max_upload_mb}MB")

    for f in request.files:
        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(400, f"Unsupported file type: {f.content_type}")

    batch = UploadBatch(
        id=uuid4(),
        user_id=user.id,
        total_files=len(request.files),
        total_size_bytes=total_size,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(batch)
    db.flush()

    presigned_urls = []
    for file_meta in request.files:
        doc_id = str(uuid4())
        object_key = f"users/{user.id}/documents/{doc_id}/{file_meta.filename}"
        upload_url = storage_service.generate_presigned_upload_url(
            object_key, content_type=file_meta.content_type
        )
        presigned_urls.append({
            "filename": file_meta.filename,
            "upload_url": upload_url,
            "object_key": object_key,
            "document_id": doc_id,
        })

    db.commit()
    return UploadBatchResponse(batch_id=str(batch.id), presigned_urls=presigned_urls)


@router.post("/confirm-batch", response_model=ConfirmBatchResponse)
async def confirm_upload_batch(
    request: ConfirmBatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from workers.tasks.ingestion import ingest_document, analyze_for_recommendation

    batch = db.query(UploadBatch).filter_by(id=request.batch_id).first()
    if not batch:
        raise HTTPException(404, "Upload batch not found")
    if str(batch.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(403, "Access denied")
    if batch.status != "pending":
        raise HTTPException(400, f"Batch already {batch.status}")

    docs_created = []
    for file_info in request.files:
        doc = Document(
            id=uuid4(),
            owner_user_id=user.id,
            title=file_info.title,
            original_filename=file_info.object_key.rsplit("/", 1)[-1],
            size_bytes=0,
            b2_object_key=file_info.object_key,
            file_type=_detect_file_type(file_info.object_key),
            upload_batch_id=batch.id,
            retrieval_type="vector",
            created_at=datetime.utcnow(),
        )
        job = IngestionJob(
            id=uuid4(),
            document_id=doc.id,
            status="QUEUED",
            progress=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add_all([doc, job])
        db.flush()
        docs_created.append((doc, job))

    batch.status = "processing"
    db.commit()

    for doc, job in docs_created:
        ingest_document.delay(str(doc.id), str(job.id))

    analyze_for_recommendation.delay(str(batch.id))

    return ConfirmBatchResponse(status="processing", batch_id=str(batch.id))


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.query(UploadBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    if str(batch.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(403, "Access denied")

    docs = db.query(Document).filter_by(upload_batch_id=batch_id).all()
    files = []
    for doc in docs:
        job = db.query(IngestionJob).filter_by(document_id=doc.id).order_by(
            IngestionJob.created_at.desc()
        ).first()
        files.append({
            "document_id": str(doc.id),
            "title": doc.title,
            "status": job.status if job else "unknown",
            "progress": job.progress if job else 0,
        })

    return BatchStatusResponse(
        batch_id=str(batch.id),
        status=batch.status,
        recommended_retrieval_type=batch.recommended_retrieval_type,
        files=files,
    )


@router.post("/batch/{batch_id}/confirm-type")
async def confirm_retrieval_type(
    batch_id: str,
    request: ConfirmTypeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.query(UploadBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    if str(batch.user_id) != str(user.id):
        raise HTTPException(403, "Access denied")

    batch.user_confirmed_type = request.retrieval_type
    docs = db.query(Document).filter_by(upload_batch_id=batch_id).all()
    for doc in docs:
        doc.retrieval_type = request.retrieval_type
    db.commit()

    return {"status": "confirmed", "type": request.retrieval_type}


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).filter(
        Document.deleted_at.is_(None),
        Document.owner_user_id == user.id,
    ).order_by(Document.created_at.desc()).all()

    result = []
    for doc in docs:
        job = db.query(IngestionJob).filter_by(document_id=doc.id).order_by(
            IngestionJob.created_at.desc()
        ).first()
        result.append(DocumentResponse(
            id=str(doc.id),
            title=doc.title,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            size_bytes=doc.size_bytes,
            scope=doc.scope,
            retrieval_type=doc.retrieval_type,
            created_at=doc.created_at.isoformat(),
            ingestion_status=job.status if job else None,
        ))

    return DocumentListResponse(documents=result, total=len(result))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(id=document_id, deleted_at=None).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.can_be_viewed_by(user):
        raise HTTPException(403, "Access denied")

    job = db.query(IngestionJob).filter_by(document_id=doc.id).order_by(
        IngestionJob.created_at.desc()
    ).first()

    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        size_bytes=doc.size_bytes,
        scope=doc.scope,
        retrieval_type=doc.retrieval_type,
        created_at=doc.created_at.isoformat(),
        ingestion_status=job.status if job else None,
    )


@router.get("/{document_id}/ingestion-status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(id=document_id, deleted_at=None).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.can_be_viewed_by(user):
        raise HTTPException(403, "Access denied")

    job = db.query(IngestionJob).filter_by(document_id=document_id).order_by(
        IngestionJob.created_at.desc()
    ).first()
    if not job:
        raise HTTPException(404, "No ingestion job found")

    return IngestionStatusResponse(
        document_id=str(doc.id),
        status=job.status,
        progress=job.progress,
        chunk_count=job.chunk_count,
        chunks_rejected=job.chunks_rejected,
        error=job.error,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter_by(id=document_id, deleted_at=None).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if str(doc.owner_user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(403, "Access denied")

    from app.models.message import Message as MessageModel
    from app.models.message_evaluation import MessageEvaluation
    from app.models.thread import Thread as ThreadModel

    thread_ids = db.query(ThreadModel.id).filter_by(document_id=document_id).all()
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
        db.query(ThreadModel).filter(ThreadModel.document_id == document_id).delete(synchronize_session=False)

    db.query(IngestionJob).filter_by(document_id=document_id).delete(synchronize_session=False)

    prefix = f"users/{user.id}/documents/{document_id}/"
    try:
        storage_service.delete_objects_by_prefix(prefix)
    except Exception as e:
        logger.warning(f"Failed to delete B2 objects for document {document_id}: {e}")

    try:
        vector_service.delete_by_document(document_id)
    except Exception as e:
        logger.warning(f"Failed to delete Chroma vectors for document {document_id}: {e}")

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


def _detect_file_type(object_key: str) -> str:
    lower = object_key.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".md"):
        return "md"
    if lower.endswith(".txt"):
        return "txt"
    return "pdf"
