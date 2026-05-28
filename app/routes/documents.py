"""
Routes for document upload and management.
Handles presigned URL generation and upload confirmation.
"""
from flask import Blueprint, request, jsonify, current_app
from app.models import Document, IngestionJob, ActivityLog
from app.extensions import db
from app.services.auth_service import login_required, admin_required, owns_document
from app.services.storage_service import storage_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')
uploads_bp = Blueprint('uploads', __name__, url_prefix='/api/uploads')


# ==================== UPLOAD ROUTES ====================

@uploads_bp.route('/presign', methods=['POST'])
@login_required
def presign_upload():
    """
    Generate presigned URL for direct upload to B2.
    
    Request body:
        {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1048576
        }
    
    Returns:
        {
            "upload_url": "https://...",
            "object_key": "users/123/documents/456/document.pdf"
        }
    """
    try:
        data = request.get_json()
        
        # Validate input
        filename = data.get('filename')
        content_type = data.get('content_type', 'application/pdf')
        size_bytes = data.get('size_bytes')
        
        if not filename:
            return jsonify({'error': 'filename is required'}), 400
        
        if not size_bytes:
            return jsonify({'error': 'size_bytes is required'}), 400
        
        # Validate file size
        max_size = current_app.config['MAX_UPLOAD_MB'] * 1024 * 1024
        if size_bytes > max_size:
            return jsonify({
                'error': f'File size exceeds maximum allowed ({current_app.config["MAX_UPLOAD_MB"]} MB)'
            }), 400
        
        # Validate content type
        if content_type != 'application/pdf':
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Generate temporary doc_id (will be replaced after confirmation)
        import uuid
        temp_doc_id = str(uuid.uuid4())
        
        # Generate object key
        user_id = request.user.id
        object_key = storage_service.generate_object_key(user_id, temp_doc_id, filename)
        
        # Generate presigned URL
        upload_url = storage_service.generate_presigned_upload_url(
            object_key,
            content_type=content_type,
            expires_in=3600  # 1 hour
        )
        
        logger.info(f"Generated presigned URL for user {user_id}: {object_key}")
        
        return jsonify({
            'upload_url': upload_url,
            'object_key': object_key,
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        return jsonify({'error': 'Failed to generate upload URL'}), 500


@documents_bp.route('/confirm', methods=['POST'])
@login_required
def confirm_upload():
    """
    Confirm document upload and create database records.
    
    Request body:
        {
            "object_key": "users/123/documents/456/document.pdf",
            "title": "My Document",
            "scope": "USER_PRIVATE"  // Optional, admin only for GLOBAL/ADMIN_ONLY
        }
    
    Returns:
        {
            "document_id": 123,
            "status": "processing"
        }
    """
    try:
        data = request.get_json()
        
        # Validate input
        object_key = data.get('object_key')
        title = data.get('title')
        scope = data.get('scope', 'USER_PRIVATE')
        
        if not object_key:
            return jsonify({'error': 'object_key is required'}), 400
        
        if not title:
            return jsonify({'error': 'title is required'}), 400
        
        # Validate scope permissions
        user = request.user
        if scope in ['GLOBAL', 'ADMIN_ONLY'] and not user.is_admin():
            return jsonify({'error': 'Only admins can set GLOBAL or ADMIN_ONLY scope'}), 403
        
        # Verify object exists in B2
        if not storage_service.object_exists(object_key):
            return jsonify({'error': 'File not found in storage'}), 404
        
        # Extract filename from object key
        filename = object_key.split('/')[-1]
        
        # Get file size from B2 (if needed, or accept from request)
        # For now, we'll accept it from request or default to 0
        size_bytes = data.get('size_bytes', 0)
        
        # Create document record
        document = Document(
            owner_user_id=user.id,
            title=title,
            original_filename=filename,
            size_bytes=size_bytes,
            b2_object_key=object_key,
            scope=scope
        )
        
        db.session.add(document)
        db.session.flush()  # Get document.id
        
        # Create ingestion job
        job = IngestionJob(
            document_id=document.id,
            status='QUEUED'
        )
        
        db.session.add(job)
        
        # Log the upload activity
        ActivityLog.log_action(
            user_id=user.id,
            action='upload_document',
            target_type='document',
            target_id=document.id,
            metadata={
                'title': title,
                'filename': filename,
                'scope': scope,
                'size_bytes': size_bytes
            }
        )
        
        db.session.commit()
        
        logger.info(f"Document {document.id} confirmed and ingestion job {job.id} created")
        
        return jsonify({
            'document_id': document.id,
            'job_id': job.id,
            'status': 'queued'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error confirming upload: {str(e)}")
        return jsonify({'error': 'Failed to confirm upload'}), 500


# ==================== DOCUMENT MANAGEMENT ROUTES ====================

@documents_bp.route('', methods=['GET'])
@login_required
def list_documents():
    """
    List documents accessible to current user.
    
    Returns:
        {
            "documents": [
                {
                    "id": 123,
                    "title": "My Document",
                    "filename": "document.pdf",
                    "scope": "USER_PRIVATE",
                    "uploaded_at": "2024-01-01T00:00:00",
                    "ingestion_status": "DONE"
                }
            ]
        }
    """
    try:
        user = request.user
        
        # Build query based on user permissions
        if user.is_admin():
            # Admins see everything
            documents = Document.query.filter_by(deleted_at=None).all()
        else:
            # Regular users see GLOBAL and their own USER_PRIVATE docs
            documents = Document.query.filter(
                Document.deleted_at.is_(None),
                db.or_(
                    Document.scope == 'GLOBAL',
                    db.and_(
                        Document.scope == 'USER_PRIVATE',
                        Document.owner_user_id == user.id
                    )
                )
            ).all()
        
        # Format response
        docs_data = []
        for doc in documents:
            # Get latest ingestion job
            latest_job = IngestionJob.query.filter_by(
                document_id=doc.id
            ).order_by(IngestionJob.created_at.desc()).first()
            
            docs_data.append({
                'id': doc.id,
                'title': doc.title,
                'filename': doc.original_filename,
                'scope': doc.scope,
                'uploaded_at': doc.created_at.isoformat() if doc.created_at else None,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'size_bytes': doc.size_bytes,
                'ingestion_status': latest_job.status if latest_job else 'UNKNOWN',
                'owner_user_id': doc.owner_user_id
            })
        
        return jsonify({'documents': docs_data}), 200
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': 'Failed to list documents'}), 500


@documents_bp.route('/activity-log', methods=['GET'])
@login_required
def list_activity_log():
    """List activity logs for current user."""
    try:
        user = request.user
        limit = request.args.get('limit', 100, type=int)

        logs = ActivityLog.query.filter_by(
            actor_user_id=user.id
        ).order_by(ActivityLog.created_at.desc()).limit(limit).all()

        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'action': log.action,
                'resource_type': log.target_type,
                'resource_id': log.target_id,
                'details': log.metadata_json,
                'created_at': log.created_at.isoformat()
            })

        return jsonify({'logs': logs_data}), 200
    except Exception as e:
        logger.error(f"Error listing activity logs: {str(e)}")
        return jsonify({'error': 'Failed to list activity log'}), 500


@documents_bp.route('/<document_id>', methods=['GET'])
@login_required
@owns_document(allow_global=True)
def get_document(document_id):
    """
    Get document details by ID.
    
    Returns:
        {
            "id": 123,
            "title": "My Document",
            "filename": "document.pdf",
            "scope": "USER_PRIVATE",
            "uploaded_at": "2024-01-01T00:00:00",
            "ingestion_status": "DONE",
            "download_url": "https://..."
        }
    """
    try:
        document = request.document
        
        # Generate download URL
        download_url = storage_service.generate_presigned_download_url(
            document.b2_object_key,
            expires_in=3600
        )

        # Get latest ingestion job
        latest_job = IngestionJob.query.filter_by(
            document_id=document.id
        ).order_by(IngestionJob.created_at.desc()).first()

        return jsonify({
            'id': document.id,
            'title': document.title,
            'filename': document.original_filename,
            'b2_object_key': document.b2_object_key,
            'uploaded_at': document.created_at.isoformat() if document.created_at else None,
            'ingestion_status': latest_job.status if latest_job else 'UNKNOWN',
            'ingestion_error': latest_job.error if latest_job and latest_job.error else None,
            'download_url': download_url,
            'owner_user_id': document.owner_user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        return jsonify({'error': 'Failed to get document'}), 500


@documents_bp.route('/<document_id>', methods=['DELETE'])
@login_required
@owns_document(allow_global=True)
def delete_document(document_id):
    """
    Soft-delete a document (admin or owner only).
    
    Returns:
        {
            "message": "Document deleted successfully"
        }
    """
    try:
        user = request.user
        document = request.document
        
        # Soft delete
        document.deleted_at = datetime.utcnow()
        document.deleted_by_user_id = user.id
        
        db.session.commit()
        
        logger.info(f"Document {document.id} deleted by user {user.id}")
        
        return jsonify({'message': 'Document deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': 'Failed to delete document'}), 500
