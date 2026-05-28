from celery import Task
from workers.celery_app import celery_app


class DatabaseTask(Task):
    _db_session = None

    @property
    def db(self):
        if self._db_session is None:
            from app.config import get_settings
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            engine = create_engine(get_settings().database_url, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            self._db_session = SessionLocal()
        return self._db_session

    def after_return(self, *args, **kwargs):
        if self._db_session:
            self._db_session.close()
            self._db_session = None


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3, default_retry_delay=60)
def ingest_document(self, document_id: str, job_id: str):
    from app.models.document import Document
    from app.models.ingestion_job import IngestionJob
    from app.services.ingestion_service import ingestion_service
    from app.services.vector_service import vector_service
    from app.services.metadata.extractor import metadata_extractor
    from app.config import get_settings
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()
    db = self.db

    job = db.query(IngestionJob).filter_by(id=job_id).first()
    if not job:
        logger.error(f"IngestionJob {job_id} not found")
        return

    job.status = "RUNNING"
    job.progress = 0
    if not job.celery_task_id:
        job.celery_task_id = self.request.id
    db.commit()

    try:
        doc = db.query(Document).filter_by(id=document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        job.update_progress(10)
        db.commit()

        pages = ingestion_service.download_and_parse(doc)
        job.update_progress(30)
        db.commit()

        chunks, rejected = ingestion_service.chunk(pages)
        if not chunks:
            raise ValueError("No valid chunks after parsing")
        job.update_progress(50)
        db.commit()

        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            model=settings.openai_text_embedding_model,
            api_key=settings.openai_api_key,
        )
        batch_size = 100
        total_chunks = len(chunks)

        for batch_start in range(0, total_chunks, batch_size):
            batch = chunks[batch_start:batch_start + batch_size]
            texts = [c["text"] for c in batch]

            embedding_vectors = embeddings.embed_documents(texts)

            chunks_data = []
            for i, embedding_vector in enumerate(embedding_vectors):
                chunk = batch[i]
                global_index = batch_start + i
                chunk_meta = chunk
                if "chunk_index" not in chunk_meta or chunk_meta.get("chunk_index") is None:
                    chunk_meta = dict(chunk)
                    chunk_meta["chunk_index"] = global_index

                metadata = metadata_extractor.build_chunk_metadata(
                    chunk=chunk_meta,
                    document=doc,
                    global_index=global_index,
                )

                chunks_data.append({
                    "chunk_id": f"chunk_{global_index}",
                    "text": chunk["text"],
                    "embedding": embedding_vector,
                    "page": chunk.get("page", 0),
                    "owner_user_id": str(doc.owner_user_id),
                    "scope": doc.scope,
                    "chunk_index": global_index,
                    "section_title": metadata.section_title,
                    "semantic_topic": metadata.semantic_topic,
                    "filename": metadata.filename,
                    "file_type": metadata.file_type,
                    "upload_timestamp": metadata.upload_timestamp,
                })

            vector_service.upsert_text_chunks(document_id, chunks_data)

            progress = 50 + int(50 * (batch_start + len(batch)) / max(total_chunks, 1))
            job.update_progress(progress)
            db.commit()

        job.mark_done()
        job.chunk_count = total_chunks
        job.chunks_rejected = rejected
        db.commit()

        logger.info(
            f"Ingestion complete for document {document_id}: "
            f"{total_chunks} chunks, {rejected} rejected"
        )

    except Exception as exc:
        logger.error(f"Ingestion failed for document {document_id}: {exc}")
        job.mark_failed(str(exc))
        db.commit()
        raise self.retry(exc=exc)


@celery_app.task(base=DatabaseTask, bind=True, max_retries=2, default_retry_delay=30)
def analyze_for_recommendation(self, batch_id: str):
    from app.models.upload_batch import UploadBatch
    from app.models.document import Document
    from app.config import get_settings
    import json, logging

    logger = logging.getLogger(__name__)
    db = self.db

    batch = db.query(UploadBatch).filter_by(id=batch_id).first()
    if not batch:
        logger.error(f"UploadBatch {batch_id} not found")
        return

    batch.status = "analyzing"
    db.commit()

    docs = db.query(Document).filter_by(upload_batch_id=batch_id).all()

    file_types = list(set(d.file_type for d in docs))
    total_size = sum(d.size_bytes for d in docs)

    if {"csv"}.intersection(file_types) or total_size < 500_000:
        recommendation = "vector"
        reasoning = "CSV data or small files — vector search optimal"
    else:
        recommendation = "vector"
        reasoning = "Vector RAG — default for narrative documents"

    batch.recommended_retrieval_type = recommendation
    batch.status = "done"
    db.commit()

    logger.info(f"Recommendation for batch {batch_id}: {recommendation} ({reasoning})")
    return {"recommendation": recommendation, "reasoning": reasoning}
