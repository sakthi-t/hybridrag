"""
RAG (Retrieval Augmented Generation) service.
Handles vector retrieval, context assembly, and LLM chat completion.
"""
import openai
from flask import current_app
from app.services.vector_service import vector_service
from app.services.storage_service import storage_service
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations - retrieval and generation."""
    
    def __init__(self):
        self._openai_client = None
    
    def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            openai.api_key = current_app.config.get('OPENAI_API_KEY')
            self._openai_client = openai
        return self._openai_client
    
    def generate_query_embedding(self, query_text):
        """
        Generate embedding for user query.
        
        Args:
            query_text: User's query text
        
        Returns:
            List of floats (embedding vector)
        """
        try:
            client = self._get_openai_client()
            model = current_app.config.get('OPENAI_TEXT_EMBEDDING_MODEL', 'text-embedding-3-large')
            
            response = client.embeddings.create(
                input=query_text,
                model=model
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Generated query embedding for: {query_text[:50]}...")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise
    
    def retrieve_context(self, query_text, document_id, user_id, top_k=5, top_m=3, is_admin=False):
        """
        Retrieve relevant text chunks and images for a query.
        
        Args:
            query_text: User's query text
            document_id: Document ID to search within
            user_id: User ID for permission filtering
            top_k: Number of text chunks to retrieve
            top_m: Number of images to retrieve
            is_admin: Whether the user is an admin
        
        Returns:
            Dict with 'text_chunks' and 'images' keys
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_query_embedding(query_text)
            
            # Search for text chunks
            text_chunks = vector_service.search_text(
                query_embedding=query_embedding,
                document_id=document_id,
                user_id=user_id,
                top_k=top_k,
                is_admin=is_admin
            )
            
            # Search for images (if enabled)
            images = []
            if current_app.config.get('ENABLE_IMAGE_EMBEDDINGS', False):
                images = vector_service.search_images(
                    query_embedding=query_embedding,
                    document_id=document_id,
                    user_id=user_id,
                    top_m=top_m,
                    is_admin=is_admin
                )
            
            logger.info(f"Retrieved {len(text_chunks)} text chunks and {len(images)} images")
            
            citations = []
            for chunk in text_chunks:
                citations.append({
                    'page': chunk.get('page', 0),
                    'chunk_id': chunk.get('chunk_id'),
                    'document_id': chunk.get('document_id')
                })

            return {
                'text_chunks': text_chunks,
                'images': images,
                'citations': citations
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise
    
    def assemble_prompt(self, query_text, context, message_history=None):
        """
        Assemble prompt for GPT-4o with context and history.
        
        Args:
            query_text: User's current query
            context: Dict with 'text_chunks' and 'images' from retrieve_context
            message_history: Optional list of previous messages
        
        Returns:
            List of messages for OpenAI chat completion
        """
        # System message - text-only scope
        system_message = {
            'role': 'system',
            'content': """You are an expert document Q&A assistant specialized in analyzing and answering questions about documents with high accuracy and thoroughness.

**IMPORTANT SCOPE LIMITATION**: This system only supports TEXT-BASED analysis. Image analysis, chart interpretation, or visual content examination is NOT available. If a user asks about images, diagrams, charts, or visual elements, politely explain that this version of the application only supports text-based document analysis.

Your primary responsibilities:
1. **Context-Based Responses**: All answers MUST be derived exclusively from the provided document text excerpts. Never use external knowledge or make assumptions beyond what's explicitly stated in the context.

2. **Comprehensive Analysis**: 
   - Read through all provided text excerpts carefully before formulating your answer
   - Consider information from multiple excerpts when relevant
   - Synthesize information across different pages if needed to provide a complete answer

3. **Citation and Page References**:
   - ALWAYS cite the page number(s) where you found the information
   - Use format: "According to page X..." or "On page Y, the document states..."
   - When information spans multiple pages, cite all relevant pages

4. **Handling Uncertainty**:
   - If the context doesn't contain enough information to answer the question, explicitly state: "Based on the provided excerpts, I don't have enough information to answer this question."
   - If the answer is partial, acknowledge limitations: "The document provides partial information on page X, but doesn't cover..."
   - Never fabricate or speculate beyond the given context

5. **Response Quality**:
   - Provide detailed, thorough answers when the context supports it
   - Structure longer answers with clear organization (bullet points, numbered lists when appropriate)
   - Extract exact quotes when they directly answer the question, using quotation marks
   - Explain technical terms or concepts if they're defined in the context

6. **Conversational Context**:
   - Maintain awareness of the conversation history
   - Reference previous questions/answers when relevant: "As mentioned earlier..."
   - Ask clarifying questions if the user's query is ambiguous

Remember: Your credibility comes from accuracy and transparency. It's better to admit when information isn't available than to provide uncertain or fabricated answers."""
        }
        
        messages = [system_message]
        
        # Add message history if provided
        if message_history:
            messages.extend(message_history)
        
        # Assemble context
        context_parts = []
        
        # Add text chunks
        if context['text_chunks']:
            context_parts.append("=== RELEVANT TEXT EXCERPTS ===\n")
            for i, chunk in enumerate(context['text_chunks'], 1):
                context_parts.append(f"[Excerpt {i} - Page {chunk['page']}]")
                context_parts.append(chunk['text'])
                context_parts.append("")
        
        # Add image references
        if context['images']:
            context_parts.append("=== RELEVANT IMAGES ===\n")
            for i, img in enumerate(context['images'], 1):
                context_parts.append(f"[Image {i} - Page {img['page']}]")
                context_parts.append(f"Image ID: {img['image_id']}")
                context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        # Create user message with context and query
        user_message = {
            'role': 'user',
            'content': f"{context_text}\n\n=== USER QUESTION ===\n{query_text}"
        }
        
        messages.append(user_message)
        
        return messages
    
    def generate_response(self, messages, stream=False):
        """
        Generate response using GPT-4o.
        
        Args:
            messages: List of messages for chat completion
            stream: Whether to stream the response
        
        Returns:
            If stream=False: Dict with 'content' and 'usage' keys
            If stream=True: Generator yielding response chunks
        """
        try:
            client = self._get_openai_client()
            model = current_app.config.get('OPENAI_MODEL', 'gpt-4o')
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=current_app.config.get('RAG_TEMPERATURE', 0.7),
                max_tokens=current_app.config.get('MAX_COMPLETION_TOKENS', 4000),
                stream=stream
            )
            
            if stream:
                # Return generator for streaming
                return self._stream_response(response)
            else:
                # Return complete response
                content = response.choices[0].message.content
                usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
                
                logger.info(f"Generated response with {usage['total_tokens']} tokens")
                
                return {
                    'content': content,
                    'usage': usage
                }
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def _stream_response(self, response):
        """
        Stream response chunks from OpenAI.
        
        Args:
            response: OpenAI streaming response
        
        Yields:
            Response chunks
        """
        try:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise
    
    def chat(self, query_text, document_id, user_id, message_history=None, stream=False, is_admin=False):
        """
        Complete RAG chat flow: retrieve context, assemble prompt, generate response.
        
        Args:
            query_text: User's query
            document_id: Document ID to query against
            user_id: User ID for permissions
            message_history: Optional previous messages in thread
            stream: Whether to stream response
            is_admin: Whether the user is an admin
        
        Returns:
            If stream=False: Dict with 'response', 'context', 'usage' keys
            If stream=True: Generator yielding response chunks
        """
        try:
            # Step 1: Retrieve context
            context = self.retrieve_context(
                query_text=query_text,
                document_id=document_id,
                user_id=user_id,
                top_k=current_app.config.get('TOP_K_CHUNKS', 5),
                top_m=current_app.config.get('TOP_M_IMAGES', 3),
                is_admin=is_admin
            )

            if not context.get('text_chunks') and not context.get('images'):
                no_context_message = (
                    "Based on the provided excerpts, I don't have enough information to answer this question. "
                    "Please re-ingest the document or select a document with available context."
                )
                if stream:
                    # Return a generator that yields the message, plus context
                    def empty_generator():
                        yield no_context_message
                    return empty_generator(), context
                else:
                    return {
                        'response': no_context_message,
                        'context': context,
                        'usage': None
                    }
            
            # Step 2: Assemble prompt
            messages = self.assemble_prompt(
                query_text=query_text,
                context=context,
                message_history=message_history
            )
            
            # Step 3: Generate response
            if stream:
                # For streaming, we return a generator
                def stream_with_context():
                    for chunk in self.generate_response(messages, stream=True):
                        yield chunk
                
                return stream_with_context(), context
            else:
                # For non-streaming, return complete response
                result = self.generate_response(messages, stream=False)
                
                return {
                    'response': result['content'],
                    'context': context,
                    'usage': result['usage']
                }
        
        except Exception as e:
            logger.error(f"Error in RAG chat: {str(e)}")
            raise


# Global RAG service instance
rag_service = RAGService()
