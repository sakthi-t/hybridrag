"""
Cleanup Neon Postgres - Delete all data for fresh Phase 7 start
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User, Document, Thread, Message, IngestionJob, ActivityLog

app = create_app()

print("\n" + "="*60)
print("  CLEANUP NEON POSTGRES")
print("="*60)

with app.app_context():
    try:
        # Delete in order (respect foreign keys)
        print("\n1. Deleting messages...")
        msg_count = Message.query.delete()
        print(f"   Deleted {msg_count} messages")
        
        print("\n2. Deleting threads...")
        thread_count = Thread.query.delete()
        print(f"   Deleted {thread_count} threads")
        
        print("\n3. Deleting ingestion jobs...")
        job_count = IngestionJob.query.delete()
        print(f"   Deleted {job_count} ingestion jobs")
        
        print("\n4. Deleting documents...")
        doc_count = Document.query.delete()
        print(f"   Deleted {doc_count} documents")
        
        print("\n5. Deleting activity logs...")
        log_count = ActivityLog.query.delete()
        print(f"   Deleted {log_count} activity logs")
        
        print("\n6. Deleting users...")
        user_count = User.query.delete()
        print(f"   Deleted {user_count} users")
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("  DATABASE CLEANUP COMPLETE")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
