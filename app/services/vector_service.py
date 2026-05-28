"""
Vector database service using Chroma Cloud.
Handles vector storage, retrieval, and management for RAG operations.
"""
import chromadb
from flask import current_app
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class VectorService:
    """Service for Chroma Cloud vector database operations."""
    
    def __init__(self):
        self._client = None
        self._collection = None
    
    def _get_client(self):
        """Get or create Chroma client."""
        if self._client is None:
            config = current_app.config
            
            # Use CloudClient for Chroma Cloud
            self._client = chromadb.CloudClient(
                tenant=config.get('CHROMA_TENANT'),
                database=config.get('CHROMA_DATABASE'),
                api_key=config.get('CHROMA_API_KEY')
            )
            
            logger.info("Initialized Chroma Cloud client")
        
        return self._client
    
    def _get_collection(self):
        """Get or create the vector collection."""
        if self._collection is None:
            client = self._get_client()
            collection_name = current_app.config.get('CHROMA_COLLECTION')
            
            try:
                # Try to get existing collection
                self._collection = client.get_collection(name=collection_name)
                logger.info(f"Retrieved existing collection: {collection_name}")
            except Exception:
                # Create new collection if it doesn't exist
                self._collection = client.create_collection(
                    name=collection_name,
                    metadata={"description": "RAG Threads document vectors"}
                )
                logger.info(f"Created new collection: {collection_name}")
        
        return self._collection
    
    def upsert_text_chunks(self, document_id, chunks_data):
        """
        Insert or update text chunk embeddings.
        
        Args:
            document_id: Document ID
            chunks_data: List of dicts with keys:
                - chunk_id: Unique chunk identifier
                - text: Chunk text content
                - embedding: Vector embedding (list of floats)
                - page: Page number
                - owner_user_id: Document owner ID
                - scope: Document scope (GLOBAL/USER_PRIVATE/ADMIN_ONLY)
        
        Returns:
            Number of chunks upserted
        """
        try:
            collection = self._get_collection()
            
            # Process in batches of 100 to avoid Chroma limits
            batch_size = 100
            total_upserted = 0
            
            for batch_start in range(0, len(chunks_data), batch_size):
                batch = chunks_data[batch_start:batch_start + batch_size]
                
                ids = []
                embeddings = []
                documents = []
                metadatas = []
                
                for chunk in batch:
                    chunk_id = f"{document_id}:{chunk['chunk_id']}"
                    ids.append(chunk_id)
                    embeddings.append(chunk['embedding'])
                    documents.append(chunk['text'])
                    metadatas.append({
                        'document_id': document_id,
                        'chunk_id': chunk['chunk_id'],
                        'page': chunk.get('page', 0),
                        'owner_user_id': chunk['owner_user_id'],
                        'scope': chunk['scope'],
                        'type': 'text'
                    })
                
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                
                total_upserted += len(batch)
                logger.info(f"Upserted batch {batch_start // batch_size + 1}: {len(batch)} chunks")
            
            logger.info(f"Upserted {total_upserted} text chunks for document {document_id}")
            return total_upserted
            
        except Exception as e:
            logger.error(f"Error upserting text chunks: {str(e)}")
            raise
    
    def upsert_image_embeddings(self, document_id, images_data):
        """
        Insert or update image embeddings.
        
        Args:
            document_id: Document ID
            images_data: List of dicts with keys:
                - image_id: Unique image identifier
                - embedding: Vector embedding (list of floats)
                - page: Page number
                - image_key: B2 object key for the image
                - owner_user_id: Document owner ID
                - scope: Document scope
        
        Returns:
            Number of images upserted
        """
        try:
            collection = self._get_collection()
            
            ids = []
            embeddings = []
            documents = []  # Empty for images
            metadatas = []
            
            for img in images_data:
                img_id = f"{document_id}:img:{img['image_id']}"
                ids.append(img_id)
                embeddings.append(img['embedding'])
                documents.append(f"Image from page {img.get('page', 0)}")
                metadatas.append({
                    'document_id': document_id,
                    'image_id': img['image_id'],
                    'page': img.get('page', 0),
                    'image_key': img['image_key'],
                    'owner_user_id': img['owner_user_id'],
                    'scope': img['scope'],
                    'type': 'image'
                })
            
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Upserted {len(ids)} image embeddings for document {document_id}")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Error upserting image embeddings: {str(e)}")
            raise
    
    def search_text(self, query_embedding, document_id=None, user_id=None, top_k=5, is_admin=False):
        """
        Search for similar text chunks.
        
        Args:
            query_embedding: Query vector embedding
            document_id: Optional document ID to filter by
            user_id: User ID for permission filtering
            top_k: Number of results to return
            is_admin: Whether the user is an admin
        
        Returns:
            List of dicts with chunk data and similarity scores
        """
        try:
            collection = self._get_collection()
            
            # Build metadata filter
            # Chroma requires $and operator for multiple conditions
            if document_id:
                where_filter = {
                    "$and": [
                        {"type": "text"},
                        {"document_id": document_id}
                    ]
                }
            else:
                where_filter = {"type": "text"}
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            chunks = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    metadata = results['metadatas'][0][i]
                    
                    # Apply permission filtering
                    if not self._can_access(metadata, user_id, is_admin):
                        continue
                    
                    chunks.append({
                        'chunk_id': metadata['chunk_id'],
                        'document_id': metadata['document_id'],
                        'text': results['documents'][0][i],
                        'page': metadata.get('page', 0),
                        'distance': results['distances'][0][i]
                    })
            
            logger.info(f"Found {len(chunks)} text chunks for query")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching text: {str(e)}")
            raise
    
    def search_images(self, query_embedding, document_id=None, user_id=None, top_m=3, is_admin=False):
        """
        Search for similar images.
        
        Args:
            query_embedding: Query vector embedding
            document_id: Optional document ID to filter by
            user_id: User ID for permission filtering
            top_m: Number of results to return
            is_admin: Whether the user is an admin
        
        Returns:
            List of dicts with image data and similarity scores
        """
        try:
            collection = self._get_collection()
            
            # Build metadata filter
            # Chroma requires $and operator for multiple conditions
            if document_id:
                where_filter = {
                    "$and": [
                        {"type": "image"},
                        {"document_id": document_id}
                    ]
                }
            else:
                where_filter = {"type": "image"}
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_m,
                where=where_filter,
                include=['metadatas', 'distances']
            )
            
            # Process results
            images = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    metadata = results['metadatas'][0][i]
                    
                    # Apply permission filtering
                    if not self._can_access(metadata, user_id, is_admin):
                        continue
                    
                    images.append({
                        'image_id': metadata['image_id'],
                        'document_id': metadata['document_id'],
                        'image_key': metadata['image_key'],
                        'page': metadata.get('page', 0),
                        'distance': results['distances'][0][i]
                    })
            
            logger.info(f"Found {len(images)} images for query")
            return images
            
        except Exception as e:
            logger.error(f"Error searching images: {str(e)}")
            raise
    
    def delete_by_document(self, document_id):
        """
        Delete all vectors for a specific document.
        
        Args:
            document_id: Document ID
        
        Returns:
            True if successful
        """
        try:
            collection = self._get_collection()
            
            # Delete all vectors with this document_id
            collection.delete(
                where={'document_id': document_id}
            )
            
            logger.info(f"Deleted all vectors for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vectors by document: {str(e)}")
            raise
    
    def delete_by_user(self, user_id):
        """
        Delete all vectors owned by a specific user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            collection = self._get_collection()
            
            # Delete all vectors with this owner_user_id
            collection.delete(
                where={'owner_user_id': user_id}
            )
            
            logger.info(f"Deleted all vectors for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vectors by user: {str(e)}")
            raise
    
    def _can_access(self, metadata, user_id, is_admin=False):
        """
        Check if user can access a chunk based on metadata.
        
        Args:
            metadata: Chunk metadata with scope and owner_user_id
            user_id: User ID requesting access
            is_admin: Whether the user is an admin
        
        Returns:
            True if user can access, False otherwise
        """
        scope = metadata.get('scope')
        owner = metadata.get('owner_user_id')
        
        # GLOBAL documents are accessible to everyone
        if scope == 'GLOBAL':
            return True
        
        # USER_PRIVATE documents are accessible only to owner (or admin)
        if scope == 'USER_PRIVATE':
            return owner == user_id or is_admin
        
        # ADMIN_ONLY documents are accessible only to admins
        if scope == 'ADMIN_ONLY':
            return is_admin
        
        return False
    
    def get_collection_stats(self):
        """
        Get statistics about the vector collection.
        
        Returns:
            Dict with collection stats
        """
        try:
            collection = self._get_collection()
            count = collection.count()
            
            return {
                'total_vectors': count,
                'collection_name': current_app.config.get('CHROMA_COLLECTION')
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise

    def has_document_vectors(self, document_id):
        """
        Check if any vectors exist for a document.

        Args:
            document_id: Document ID

        Returns:
            True if vectors exist, False otherwise
        """
        try:
            collection = self._get_collection()
            results = collection.get(
                where={'document_id': document_id},
                include=['metadatas'],
                limit=1
            )

            return bool(results.get('metadatas')) and len(results.get('metadatas', [])) > 0
        except Exception as e:
            logger.error(f"Error checking vectors for document {document_id}: {str(e)}")
            raise


# Global vector service instance
vector_service = VectorService()
