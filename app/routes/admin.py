"""
Admin routes - user and document management for admins only.
"""
from flask import Blueprint, request, jsonify, current_app
from app.services.auth_service import auth_service, login_required
from app.services.vector_service import vector_service
from app.services.storage_service import storage_service
from app.models import User, Document, Thread, Message, IngestionJob, ActivityLog, MessageEvaluation
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def admin_required(f):
    """Decorator to require admin access."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = auth_service.get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if user.email != admin_email:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    """List all users with stats."""
    try:
        users = User.query.filter(User.deleted_at.is_(None)).all()
        
        users_data = []
        for user in users:
            doc_count = Document.query.filter_by(owner_user_id=user.id).filter(Document.deleted_at.is_(None)).count()
            thread_count = Thread.query.filter_by(user_id=user.id).filter(Thread.deleted_at.is_(None)).count()
            
            users_data.append({
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'docs_count': doc_count,
                'threads_count': thread_count
            })
        
        return jsonify({'users': users_data}), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({'error': 'Failed to list users'}), 500


@bp.route('/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Hard delete a user and all their data (cascade).
    Deletes: documents, threads, messages, B2 files, Chroma vectors.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if user.email == admin_email:
            return jsonify({'error': 'Cannot delete admin user'}), 400
        
        # Get user's documents for cleanup
        documents = Document.query.filter_by(owner_user_id=user_id).all()
        
        # Delete from B2 and Chroma for each document
        for doc in documents:
            try:
                # Delete from Chroma
                vector_service.delete_by_document(doc.id)
                
                # Delete from B2
                if doc.b2_object_key:
                    storage_service.delete_object(doc.b2_object_key)
            except Exception as e:
                logger.warning(f"Error cleaning up document {doc.id}: {str(e)}")
        
        # Delete all messages and evaluations for user's threads
        threads = Thread.query.filter_by(user_id=user_id).all()
        for thread in threads:
            # Delete message evaluations first (foreign key constraint)
            messages = Message.query.filter_by(thread_id=thread.id).all()
            for msg in messages:
                MessageEvaluation.query.filter_by(message_id=msg.id).delete()
            Message.query.filter_by(thread_id=thread.id).delete()
        
        # Delete threads
        Thread.query.filter_by(user_id=user_id).delete()
        
        # Delete ingestion jobs
        for doc in documents:
            IngestionJob.query.filter_by(document_id=doc.id).delete()
        
        # Delete documents
        Document.query.filter_by(owner_user_id=user_id).delete()
        
        # Delete activity logs for user
        ActivityLog.query.filter_by(actor_user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Log activity
        admin_user = auth_service.get_current_user()
        ActivityLog.log_action(
            user_id=admin_user.id,
            action='admin_delete_user',
            target_type='user',
            target_id=user_id,
            metadata={'deleted_email': user.email}
        )
        
        return jsonify({'message': f'User {user.email} and all data deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': 'Failed to delete user'}), 500


@bp.route('/documents', methods=['GET'])
@login_required
@admin_required
def list_all_documents():
    """List all documents (all scopes, all users)."""
    try:
        documents = Document.query.filter(Document.deleted_at.is_(None)).all()
        
        docs_data = []
        for doc in documents:
            owner = User.query.get(doc.owner_user_id)

            # Get latest ingestion job status
            latest_job = IngestionJob.query.filter_by(
                document_id=doc.id
            ).order_by(IngestionJob.created_at.desc()).first()

            docs_data.append({
                'id': doc.id,
                'title': doc.title,
                'original_filename': doc.original_filename,
                'scope': doc.scope if doc.scope else 'USER_PRIVATE',
                'owner_email': owner.email if owner else 'Unknown',
                'owner_id': doc.owner_user_id,
                'size_bytes': doc.size_bytes,
                'created_at': doc.created_at.isoformat(),
                'ingestion_status': latest_job.status if latest_job else 'PENDING'
            })
        
        return jsonify({'documents': docs_data}), 200
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': 'Failed to list documents'}), 500


@bp.route('/documents/<doc_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_document(doc_id):
    """
    Hard delete a document and all related data.
    Deletes: B2 file, Chroma vectors, threads, messages, ingestion jobs.
    """
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        doc_title = doc.title
        
        # Delete from Chroma
        try:
            vector_service.delete_by_document(doc_id)
        except Exception as e:
            logger.warning(f"Error deleting Chroma vectors: {str(e)}")
        
        # Delete from B2
        try:
            if doc.b2_object_key:
                # Delete all objects under the document prefix (pdf + images)
                prefix = f"users/{doc.owner_user_id}/documents/{doc.id}/"
                storage_service.delete_objects_by_prefix(prefix)
                # Delete the original PDF object explicitly as well
                storage_service.delete_object(doc.b2_object_key)
        except Exception as e:
            logger.warning(f"Error deleting B2 object: {str(e)}")
        
        # Delete all threads, messages, and evaluations for this document
        threads = Thread.query.filter_by(document_id=doc_id).all()
        for thread in threads:
            # Delete message evaluations first (foreign key constraint)
            messages = Message.query.filter_by(thread_id=thread.id).all()
            for msg in messages:
                MessageEvaluation.query.filter_by(message_id=msg.id).delete()
            Message.query.filter_by(thread_id=thread.id).delete()
        Thread.query.filter_by(document_id=doc_id).delete()
        
        # Delete ingestion jobs
        IngestionJob.query.filter_by(document_id=doc_id).delete()
        
        # Delete document
        db.session.delete(doc)
        db.session.commit()
        
        # Log activity
        admin_user = auth_service.get_current_user()
        ActivityLog.log_action(
            user_id=admin_user.id,
            action='admin_delete_document',
            target_type='document',
            target_id=doc_id,
            metadata={'deleted_title': doc_title}
        )
        
        return jsonify({'message': f'Document "{doc_title}" deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': 'Failed to delete document'}), 500


@bp.route('/documents/<doc_id>/chunks', methods=['DELETE'])
@login_required
@admin_required
def delete_document_chunks(doc_id):
    """Delete only the Chroma vectors for a document (keep document record)."""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        # Delete from Chroma
        vector_service.delete_by_document(doc_id)
        deleted_count = 'all'  # delete_by_document returns True, not count
        
        # Log activity
        admin_user = auth_service.get_current_user()
        ActivityLog.log_action(
            user_id=admin_user.id,
            action='admin_delete_chunks',
            target_type='document',
            target_id=doc_id,
            metadata={'deleted_vectors': deleted_count}
        )
        
        return jsonify({
            'message': f'Deleted chunks for document "{doc.title}"',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting chunks: {str(e)}")
        return jsonify({'error': 'Failed to delete chunks'}), 500


@bp.route('/documents/<doc_id>/reingest', methods=['POST'])
@login_required
@admin_required
def reingest_document(doc_id):
    """Recreate document chunks if none exist in Chroma."""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'error': 'Document not found'}), 404

        if vector_service.has_document_vectors(doc_id):
            return jsonify({'message': 'Chunks already exist'}), 200

        job = IngestionJob(
            document_id=doc_id,
            status='QUEUED'
        )
        db.session.add(job)
        db.session.commit()

        admin_user = auth_service.get_current_user()
        ActivityLog.log_action(
            user_id=admin_user.id,
            action='admin_reingest_document',
            target_type='document',
            target_id=doc_id,
            metadata={'title': doc.title}
        )
        db.session.commit()

        return jsonify({
            'message': f'Reingestion queued for "{doc.title}"',
            'job_id': job.id
        }), 202

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error reingesting document: {str(e)}")
        return jsonify({'error': 'Failed to reingest document'}), 500


@bp.route('/activity-log', methods=['GET'])
@login_required
@admin_required
def get_activity_log():
    """Get activity log with optional filtering."""
    try:
        # Get query params
        limit = request.args.get('limit', 100, type=int)
        action_filter = request.args.get('action')
        
        query = ActivityLog.query.order_by(ActivityLog.created_at.desc())
        
        if action_filter:
            query = query.filter(ActivityLog.action == action_filter)
        
        logs = query.limit(limit).all()
        
        logs_data = []
        for log in logs:
            user = User.query.get(log.actor_user_id)
            logs_data.append({
                'id': log.id,
                'user_email': user.email if user else 'Deleted User',
                'action': log.action,
                'resource_type': log.target_type,
                'resource_id': log.target_id,
                'details': log.metadata_json,
                'created_at': log.created_at.isoformat()
            })
        
        return jsonify({'logs': logs_data}), 200
        
    except Exception as e:
        logger.error(f"Error getting activity log: {str(e)}")
        return jsonify({'error': 'Failed to get activity log'}), 500
