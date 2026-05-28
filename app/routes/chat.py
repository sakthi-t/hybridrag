"""
Chat routes for RAG-powered conversations.
Handles message sending with RAG retrieval and streaming responses.
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.models import Thread, Message, Document, MessageEvaluation
from app.extensions import db
from app.services.auth_service import login_required, owns_thread, owns_document
from app.services.rag_service import rag_service
from app.services.evaluation_service import evaluation_service
from datetime import datetime
import re
import json
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('chat', __name__, url_prefix='/api')


@bp.route('/threads/<thread_id>/chat', methods=['POST'])
@login_required
@owns_thread
def send_message(thread_id):
    """
    Send a message in a thread and get RAG-powered response.
    
    Request body:
        {
            "message": "What is the main topic?",
            "stream": false  // Optional, default false
        }
    
    Returns (non-streaming):
        {
            "message_id": 123,
            "response": "The main topic is...",
            "context": {
                "text_chunks": [...],
                "images": [...]
            }
        }
    
    Returns (streaming):
        Server-Sent Events stream with response chunks
    """
    try:
        data = request.get_json()
        
        # Validate input
        message_text = data.get('message')
        stream_response = data.get('stream', False)
        
        if not message_text:
            return jsonify({'error': 'message is required'}), 400
        
        user = request.user
        user_id = user.id
        is_admin = user.is_admin()  # Capture as boolean before generator
        thread = request.thread
        document_id = thread.document_id

        # Get document
        document = Document.query.get(thread.document_id)

        if not document or document.deleted_at:
            return jsonify({'error': 'Document not found'}), 404
        
        # Get message history for context
        previous_messages = Message.query.filter_by(
            thread_id=thread_id
        ).order_by(Message.created_at.asc()).limit(10).all()
        
        message_history = []
        for msg in previous_messages:
            message_history.append({
                'role': msg.role,
                'content': msg.get_text()
            })
        
        # Store user message
        user_message = Message(
            thread_id=thread_id,
            role='user'
        )
        user_message.set_content(message_text)
        db.session.add(user_message)
        db.session.flush()
        db.session.commit()
        
        # Handle streaming vs non-streaming
        if stream_response:
            # Streaming response using SSE
            def generate():
                try:
                    # Get RAG response generator and context
                    response_generator, context = rag_service.chat(
                        query_text=message_text,
                        document_id=document_id,
                        user_id=user_id,
                        message_history=message_history,
                        stream=True,
                        is_admin=is_admin
                    )
                    
                    # Send context first
                    yield f"data: {json.dumps({'type': 'context', 'context': context})}\n\n"
                    
                    # Collect response for storage
                    full_response = []
                    
                    # Stream response chunks
                    for chunk in response_generator:
                        full_response.append(chunk)
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    
                    response_text = ''.join(full_response)
                    # Extract citations from response text (e.g., "Page 14", "Pages 4 and 7")
                    cited_pages = set()
                    # Match "Page X" or "Pages X"
                    for match in re.finditer(r"(?i)\bpages?\s+(\d+)", response_text):
                        cited_pages.add(int(match.group(1)))
                    # Match additional page numbers after "and" or comma (e.g., "Pages 4 and 7", "pages 1, 2, 3")
                    for match in re.finditer(r"(?i)\bpages?\s+[\d,\s]+(?:and\s+)?(\d+)", response_text):
                        cited_pages.add(int(match.group(1)))
                    # Also extract all numbers following "page" patterns
                    for match in re.finditer(r"(?i)\bpages?\s+([\d,\s]+(?:and\s+\d+)?)", response_text):
                        nums = re.findall(r"\d+", match.group(1))
                        for n in nums:
                            cited_pages.add(int(n))
                    extracted_citations = []
                    if cited_pages:
                        for chunk in context.get('text_chunks', []):
                            if chunk.get('page') in cited_pages:
                                extracted_citations.append({
                                    'page': chunk.get('page', 0),
                                    'chunk_id': chunk.get('chunk_id'),
                                    'document_id': chunk.get('document_id')
                                })
                    context['citations'] = extracted_citations

                    # Store assistant message
                    assistant_message = Message(
                        thread_id=thread_id,
                        role='assistant'
                    )
                    assistant_message.set_content(response_text, citations=context.get('citations'))
                    db.session.add(assistant_message)

                    # Update thread timestamp
                    db.session.query(Thread).filter_by(id=thread_id).update({
                        'updated_at': datetime.utcnow()
                    })
                    db.session.commit()

                    # Evaluate response
                    evaluation = evaluation_service.evaluate(response_text, context)

                    # Persist evaluation (best-effort)
                    try:
                        evaluation_row = MessageEvaluation(
                            message_id=assistant_message.id,
                            faithfulness_score=evaluation['faithfulness_score'],
                            citation_precision_score=evaluation['citation_precision_score'],
                            groundedness_score=evaluation['groundedness_score'],
                            rationale_json=evaluation.get('rationale')
                        )
                        db.session.add(evaluation_row)
                        db.session.commit()
                    except Exception as eval_error:
                        logger.error(f"Failed to persist evaluation: {eval_error}")
                        db.session.rollback()

                    # Send metrics
                    metrics = {
                        'retrieved_text_chunks': len(context.get('text_chunks', [])),
                        'retrieved_images': len(context.get('images', [])),
                        'faithfulness_score': evaluation['faithfulness_score'],
                        'citation_precision_score': evaluation['citation_precision_score'],
                        'groundedness_score': evaluation['groundedness_score']
                    }
                    yield f"data: {json.dumps({'type': 'metrics', 'metrics': metrics})}\n\n"

                    # Send completion
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in streaming chat: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                    db.session.rollback()
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        else:
            # Non-streaming response
            try:
                # Get RAG response
                result = rag_service.chat(
                    query_text=message_text,
                    document_id=document_id,
                    user_id=user_id,
                    message_history=message_history,
                    stream=False,
                    is_admin=is_admin
                )
                
                # Store assistant message
                assistant_message = Message(
                    thread_id=thread_id,
                    role='assistant'
                )
                response_text = result['response']
                # Extract citations from response text (e.g., "Page 14", "Pages 4 and 7")
                cited_pages = set()
                # Match "Page X" or "Pages X"
                for match in re.finditer(r"(?i)\bpages?\s+(\d+)", response_text):
                    cited_pages.add(int(match.group(1)))
                # Match additional page numbers after "and" or comma (e.g., "Pages 4 and 7", "pages 1, 2, 3")
                for match in re.finditer(r"(?i)\bpages?\s+[\d,\s]+(?:and\s+)?(\d+)", response_text):
                    cited_pages.add(int(match.group(1)))
                # Also extract all numbers following "page" patterns
                for match in re.finditer(r"(?i)\bpages?\s+([\d,\s]+(?:and\s+\d+)?)", response_text):
                    nums = re.findall(r"\d+", match.group(1))
                    for n in nums:
                        cited_pages.add(int(n))
                extracted_citations = []
                if cited_pages:
                    for chunk in result['context'].get('text_chunks', []):
                        if chunk.get('page') in cited_pages:
                            extracted_citations.append({
                                'page': chunk.get('page', 0),
                                'chunk_id': chunk.get('chunk_id'),
                                'document_id': chunk.get('document_id')
                            })
                result['context']['citations'] = extracted_citations

                assistant_message.set_content(response_text, citations=result['context'].get('citations'))
                db.session.add(assistant_message)

                # Update thread timestamp
                db.session.query(Thread).filter_by(id=thread_id).update({
                    'updated_at': datetime.utcnow()
                })
                db.session.commit()

                evaluation = evaluation_service.evaluate(response_text, result['context'])
                try:
                    evaluation_row = MessageEvaluation(
                        message_id=assistant_message.id,
                        faithfulness_score=evaluation['faithfulness_score'],
                        citation_precision_score=evaluation['citation_precision_score'],
                        groundedness_score=evaluation['groundedness_score'],
                        rationale_json=evaluation.get('rationale')
                    )
                    db.session.add(evaluation_row)
                    db.session.commit()
                except Exception as eval_error:
                    logger.error(f"Failed to persist evaluation: {eval_error}")
                    db.session.rollback()
                
                logger.info(f"Chat message sent in thread {thread_id}")
                
                metrics = {
                    'retrieved_text_chunks': len(result['context'].get('text_chunks', [])),
                    'retrieved_images': len(result['context'].get('images', [])),
                    'faithfulness_score': evaluation['faithfulness_score'],
                    'citation_precision_score': evaluation['citation_precision_score'],
                    'groundedness_score': evaluation['groundedness_score']
                }
                return jsonify({
                    'message_id': user_message.id,
                    'response_id': assistant_message.id,
                    'response': result['response'],
                    'context': result['context'],
                    'usage': result.get('usage'),
                    'metrics': metrics
                }), 200
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in chat: {str(e)}")
                return jsonify({'error': 'Failed to generate response'}), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500


@bp.route('/chat', methods=['POST'])
@login_required
@owns_document(allow_global=True)
def quick_chat():
    """
    Quick chat without creating a thread (for testing).
    
    Request body:
        {
            "document_id": 123,
            "message": "What is this about?"
        }
    
    Returns:
        {
            "response": "This document is about...",
            "context": {...}
        }
    """
    try:
        data = request.get_json()
        
        # Validate input
        document_id = data.get('document_id')
        message_text = data.get('message')
        
        if not document_id or not message_text:
            return jsonify({'error': 'document_id and message are required'}), 400
        
        user = request.user
        user_id = user.id
        is_admin = user.is_admin()  # Capture as boolean before any session changes
        document = request.document
        
        # Get RAG response (no history)
        result = rag_service.chat(
            query_text=message_text,
            document_id=document_id,
            user_id=user_id,
            message_history=None,
            stream=False,
            is_admin=is_admin
        )

        evaluation = evaluation_service.evaluate(result['response'], result['context'])
        metrics = {
            'retrieved_text_chunks': len(result['context'].get('text_chunks', [])),
            'retrieved_images': len(result['context'].get('images', [])),
            'faithfulness_score': evaluation['faithfulness_score'],
            'citation_precision_score': evaluation['citation_precision_score'],
            'groundedness_score': evaluation['groundedness_score']
        }
        
        logger.info(f"Quick chat on document {document_id} by user {user.id}")
        
        return jsonify({
            'response': result['response'],
            'context': result['context'],
            'usage': result.get('usage'),
            'metrics': metrics
        }), 200
        
    except Exception as e:
        logger.error(f"Error in quick chat: {str(e)}")
        return jsonify({'error': 'Failed to generate response'}), 500
