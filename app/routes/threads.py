"""
Thread routes for managing conversation threads.
Handles thread creation, listing, retrieval, and deletion.
"""
from flask import Blueprint, request, jsonify
from app.models import Thread, Message, Document
from app.extensions import db
from app.services.auth_service import login_required, admin_required, owns_document, owns_thread
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('threads', __name__, url_prefix='/api/threads')


@bp.route('', methods=['POST'])
@login_required
@owns_document(allow_global=True)
def create_thread():
    """
    Create a new conversation thread.
    
    Request body:
        {
            "document_id": 123,
            "title": "Questions about Chapter 5"
        }
    
    Returns:
        {
            "id": 456,
            "document_id": 123,
            "title": "Questions about Chapter 5",
            "created_at": "2024-01-01T00:00:00"
        }
    """
    try:
        data = request.get_json()
        
        # Validate input
        document_id = data.get('document_id')
        title = data.get('title', 'New Thread')
        
        if not document_id:
            return jsonify({'error': 'document_id is required'}), 400
        
        user = request.user
        document = request.document
        
        # Create thread
        thread = Thread(
            user_id=user.id,
            document_id=document_id,
            title=title
        )
        
        db.session.add(thread)
        db.session.commit()
        
        logger.info(f"Created thread {thread.id} for user {user.id} on document {document_id}")
        
        return jsonify({
            'id': thread.id,
            'document_id': thread.document_id,
            'title': thread.title,
            'created_at': thread.created_at.isoformat() if thread.created_at else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating thread: {str(e)}")
        return jsonify({'error': 'Failed to create thread'}), 500


@bp.route('', methods=['GET'])
@login_required
def list_threads():
    """
    List all threads for current user.
    
    Returns:
        {
            "threads": [
                {
                    "id": 456,
                    "document_id": 123,
                    "document_title": "My Document",
                    "title": "Questions about Chapter 5",
                    "message_count": 10,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            ]
        }
    """
    try:
        user = request.user
        
        # Get all non-deleted threads for user
        threads = Thread.query.filter_by(
            user_id=user.id,
            deleted_at=None
        ).order_by(Thread.updated_at.desc()).all()
        
        # Format response
        threads_data = []
        for thread in threads:
            # Get document info
            document = Document.query.get(thread.document_id)
            
            # Count messages
            message_count = Message.query.filter_by(thread_id=thread.id).count()
            
            threads_data.append({
                'id': thread.id,
                'document_id': thread.document_id,
                'document_title': document.title if document else 'Unknown',
                'title': thread.title,
                'message_count': message_count,
                'created_at': thread.created_at.isoformat() if thread.created_at else None,
                'updated_at': thread.updated_at.isoformat() if thread.updated_at else None
            })
        
        return jsonify({'threads': threads_data}), 200
        
    except Exception as e:
        logger.error(f"Error listing threads: {str(e)}")
        return jsonify({'error': 'Failed to list threads'}), 500


@bp.route('/<thread_id>', methods=['GET'])
@login_required
@owns_thread
def get_thread(thread_id):
    """
    Get thread details including message history.
    
    Returns:
        {
            "id": 456,
            "document_id": 123,
            "document_title": "My Document",
            "title": "Questions about Chapter 5",
            "messages": [
                {
                    "id": 789,
                    "role": "user",
                    "content": "What is...",
                    "created_at": "2024-01-01T00:00:00"
                }
            ],
            "created_at": "2024-01-01T00:00:00"
        }
    """
    try:
        thread = request.thread
        
        # Get document info
        document = Document.query.get(thread.document_id)
        
        # Get messages
        messages = Message.query.filter_by(
            thread_id=thread_id
        ).order_by(Message.created_at.asc()).all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.get_text(),
                'citations': msg.get_citations(),
                'images': msg.get_images(),
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            })
        
        return jsonify({
            'id': thread.id,
            'document_id': thread.document_id,
            'document_title': document.title if document else 'Unknown',
            'title': thread.title,
            'messages': messages_data,
            'created_at': thread.created_at.isoformat() if thread.created_at else None,
            'updated_at': thread.updated_at.isoformat() if thread.updated_at else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting thread: {str(e)}")
        return jsonify({'error': 'Failed to get thread'}), 500


@bp.route('/<thread_id>', methods=['DELETE'])
@login_required
@owns_thread
def delete_thread(thread_id):
    """
    Soft-delete a thread.
    
    Returns:
        {
            "message": "Thread deleted successfully"
        }
    """
    try:
        user = request.user
        thread = request.thread
        
        # Soft delete
        thread.deleted_at = datetime.utcnow()
        thread.deleted_by_user_id = user.id
        
        db.session.commit()
        
        logger.info(f"Thread {thread_id} deleted by user {user.id}")
        
        return jsonify({'message': 'Thread deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting thread: {str(e)}")
        return jsonify({'error': 'Failed to delete thread'}), 500
