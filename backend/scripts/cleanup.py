from app import database
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.upload_batch import UploadBatch

database.init_db()
db = database.SessionLocal()

stale_jobs = db.query(IngestionJob).filter(
    IngestionJob.status.in_(["QUEUED", "RUNNING"])
).all()

for job in stale_jobs:
    print(f"Deleting stale job: {job.id} (doc={job.document_id})")
    db.delete(job)

orphan_docs = db.query(Document).filter(
    ~Document.id.in_(db.query(IngestionJob.document_id))
).all()

for doc in orphan_docs:
    print(f"Deleting orphan document: {doc.id} ({doc.title})")
    db.delete(doc)

stale_batches = db.query(UploadBatch).filter(
    UploadBatch.status.in_(["pending", "processing"])
).delete()

db.commit()
db.close()
print(f"Done. {len(stale_jobs)} jobs, {len(orphan_docs)} docs, {stale_batches} batches removed.")
