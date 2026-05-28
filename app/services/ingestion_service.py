"""
Document ingestion service.
Handles PDF processing, text extraction, image extraction, chunking, and embedding generation.
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import openai
from flask import current_app
from app.models import Document, IngestionJob
from app.extensions import db
from app.services.storage_service import storage_service
from app.services.vector_service import vector_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for processing PDFs and generating embeddings."""
    
    def __init__(self):
        self._openai_client = None
    
    def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            openai.api_key = current_app.config.get('OPENAI_API_KEY')
            self._openai_client = openai
        return self._openai_client
    
    def process_document(self, document_id):
        """
        Process a document: extract text, images, generate embeddings, and store in Chroma.
        
        Args:
            document_id: Document ID to process
        
        Returns:
            Dict with processing statistics
        """
        job = None
        
        try:
            # Get document and job
            document = Document.query.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get or create job
            job = IngestionJob.query.filter(
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_(['QUEUED', 'RUNNING'])
            ).order_by(IngestionJob.created_at.desc()).first()
            
            if not job:
                job = IngestionJob(document_id=document_id, status='QUEUED')
                db.session.add(job)
                db.session.commit()
            
            # Update job status
            job.status = 'RUNNING'
            job.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Starting ingestion for document {document_id}")
            
            # Step 1: Download PDF from B2
            pdf_bytes = storage_service.download_file(document.b2_object_key)
            
            # Step 2: Extract text and images
            text_chunks = []
            images_data = []
            
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Extract text
                text = page.get_text()
                if text.strip():
                    text_chunks.append({
                        'page': page_num + 1,
                        'text': text
                    })
                
                # Extract images if enabled
                if current_app.config.get('ENABLE_IMAGE_EMBEDDINGS', False):
                    image_list = page.get_images()
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            base_image = pdf_doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            
                            # Convert to PIL Image
                            pil_image = Image.open(io.BytesIO(image_bytes))
                            
                            # Save image to B2
                            image_key = storage_service.generate_image_object_key(
                                document.owner_user_id,
                                document_id,
                                page_num + 1,
                                img_index
                            )
                            
                            # Convert PIL Image to bytes
                            img_buffer = io.BytesIO()
                            pil_image.save(img_buffer, format='PNG')
                            img_buffer.seek(0)
                            
                            storage_service.upload_file(
                                img_buffer,
                                image_key,
                                content_type='image/png'
                            )
                            
                            images_data.append({
                                'page': page_num + 1,
                                'image_index': img_index,
                                'image_key': image_key,
                                'image': pil_image
                            })
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract image {img_index} from page {page_num + 1}: {str(e)}")
            
            pdf_doc.close()
            
            logger.info(f"Extracted {len(text_chunks)} text pages and {len(images_data)} images")
            
            # Step 3: Chunk text
            chunked_text = self._chunk_text(text_chunks)
            logger.info(f"Created {len(chunked_text)} text chunks")
            
            # Step 4: Generate text embeddings
            text_embeddings = self._generate_text_embeddings(chunked_text)
            logger.info(f"Generated {len(text_embeddings)} text embeddings")
            
            # Step 5: Generate image embeddings
            image_embeddings = []
            if current_app.config.get('ENABLE_IMAGE_EMBEDDINGS', False) and images_data:
                image_embeddings = self._generate_image_embeddings(images_data)
                logger.info(f"Generated {len(image_embeddings)} image embeddings")
            
            # Step 6: Upsert to Chroma
            if text_embeddings:
                chunks_data = []
                for i, chunk in enumerate(chunked_text):
                    chunks_data.append({
                        'chunk_id': i,
                        'text': chunk['text'],
                        'embedding': text_embeddings[i],
                        'page': chunk['page'],
                        'owner_user_id': document.owner_user_id,
                        'scope': document.scope
                    })
                
                vector_service.upsert_text_chunks(document_id, chunks_data)
            
            if image_embeddings:
                imgs_data = []
                for i, img_data in enumerate(images_data):
                    imgs_data.append({
                        'image_id': f"page_{img_data['page']}_img_{img_data['image_index']}",
                        'embedding': image_embeddings[i],
                        'page': img_data['page'],
                        'image_key': img_data['image_key'],
                        'owner_user_id': document.owner_user_id,
                        'scope': document.scope
                    })
                
                vector_service.upsert_image_embeddings(document_id, imgs_data)
            
            # Step 7: Update job status
            job.status = 'DONE'
            job.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Successfully completed ingestion for document {document_id}")
            
            return {
                'document_id': document_id,
                'text_chunks': len(text_embeddings),
                'images': len(image_embeddings),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
            if job:
                job.status = 'FAILED'
                job.error = str(e)
                job.updated_at = datetime.utcnow()
                db.session.commit()
            
            raise
    
    def _chunk_text(self, text_pages):
        """
        Chunk text with overlap.
        
        Args:
            text_pages: List of dicts with 'page' and 'text' keys
        
        Returns:
            List of dicts with 'page', 'text', and 'chunk_index' keys
        """
        chunk_size = current_app.config.get('CHUNK_SIZE', 1000)
        chunk_overlap = current_app.config.get('CHUNK_OVERLAP', 200)
        
        chunks = []
        
        for page_data in text_pages:
            page_num = page_data['page']
            text = page_data['text']
            
            # Split into chunks
            start = 0
            chunk_index = 0
            
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                
                if chunk_text.strip():
                    chunks.append({
                        'page': page_num,
                        'text': chunk_text,
                        'chunk_index': chunk_index
                    })
                    chunk_index += 1
                
                start = end - chunk_overlap
        
        return chunks
    
    def _generate_text_embeddings(self, chunks):
        """
        Generate embeddings for text chunks using OpenAI.
        
        Args:
            chunks: List of dicts with 'text' key
        
        Returns:
            List of embeddings (list of floats)
        """
        client = self._get_openai_client()
        model = current_app.config.get('OPENAI_TEXT_EMBEDDING_MODEL', 'text-embedding-3-large')
        
        embeddings = []
        
        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [chunk['text'] for chunk in batch]
            
            response = client.embeddings.create(
                input=texts,
                model=model
            )
            
            for item in response.data:
                embeddings.append(item.embedding)
        
        return embeddings
    
    def _generate_image_embeddings(self, images_data):
        """
        Generate embeddings for images using CLIP.
        
        Args:
            images_data: List of dicts with 'image' key (PIL Image)
        
        Returns:
            List of embeddings (list of floats)
        """
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            model_name = current_app.config.get('IMAGE_EMBEDDING_MODEL', 'openai/clip-vit-base-patch32')
            
            # Load CLIP model
            model = CLIPModel.from_pretrained(model_name)
            processor = CLIPProcessor.from_pretrained(model_name)
            
            embeddings = []
            
            for img_data in images_data:
                pil_image = img_data['image']
                
                # Process image
                inputs = processor(images=pil_image, return_tensors="pt")
                
                # Generate embedding
                with torch.no_grad():
                    image_features = model.get_image_features(**inputs)
                
                # Normalize and convert to list
                embedding = image_features[0].numpy().tolist()
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating image embeddings: {str(e)}")
            logger.warning("Skipping image embeddings due to error")
            return []


# Global ingestion service instance
ingestion_service = IngestionService()
