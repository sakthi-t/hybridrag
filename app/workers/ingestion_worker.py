"""
Background worker for processing ingestion jobs.
Polls for queued jobs and processes them using the ingestion service.
"""
from apscheduler.schedulers.background import BackgroundScheduler
import os
from flask import current_app
from app.models import IngestionJob
from app.extensions import db
from app.services.ingestion_service import ingestion_service
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def process_queued_jobs():
    """Poll and process queued ingestion jobs with row-level locking."""
    try:
        # Use FOR UPDATE SKIP LOCKED to atomically claim a job
        # This prevents race conditions when multiple workers are running
        from sqlalchemy import text
        
        # Get one queued job with row-level locking
        job = db.session.query(IngestionJob).filter_by(
            status='QUEUED'
        ).with_for_update(skip_locked=True).first()
        
        if not job:
            return
        
        try:
            logger.info(f"Processing job {job.id} for document {job.document_id}")
            # Mark job running while holding the lock
            job.mark_running()
            db.session.commit()

            result = ingestion_service.process_document(job.document_id)
            logger.info(f"Job {job.id} completed: {result}")
            
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {str(e)}")
            try:
                db.session.rollback()
                # Re-fetch the job to mark it failed
                job = IngestionJob.query.get(job.id)
                if job:
                    job.mark_failed(str(e))
                    db.session.commit()
            except Exception:
                db.session.rollback()
        
        db.session.remove()
    
    except Exception as e:
        logger.error(f"Error in process_queued_jobs: {str(e)}")
        db.session.remove()


def start_ingestion_worker(app):
    """
    Start the background ingestion worker.
    
    Args:
        app: Flask application instance
    """
    global scheduler

    # Avoid starting the scheduler twice when Flask reloads in debug mode
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logger.info("Skipping ingestion worker startup in reloader process")
        return
    
    if scheduler is not None:
        logger.warning("Ingestion worker already started")
        return
    
    scheduler = BackgroundScheduler()
    
    # Add job to process queued ingestion jobs every 30 seconds
    scheduler.add_job(
        func=lambda: _run_with_context(app),
        trigger='interval',
        seconds=30,
        id='process_ingestion_jobs',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Ingestion worker started (polling every 30 seconds)")


def stop_ingestion_worker():
    """Stop the background ingestion worker."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Ingestion worker stopped")


def _run_with_context(app):
    """Run queued job processing inside an application context."""
    with app.app_context():
        process_queued_jobs()
