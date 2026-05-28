import logging
import logging
from typing import Any
import chromadb
from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is None:
            settings = get_settings()
            self._client = chromadb.CloudClient(
                tenant=settings.chroma_tenant,
                database=settings.chroma_database,
                api_key=settings.chroma_api_key,
            )
            logger.info("Initialized Chroma Cloud client")
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            collection_name = get_settings().chroma_collection
            try:
                self._collection = client.get_collection(name=collection_name)
                logger.info(f"Retrieved existing collection: {collection_name}")
            except Exception:
                self._collection = client.create_collection(
                    name=collection_name,
                    metadata={"description": "Hybrid RAG document vectors"},
                )
                logger.info(f"Created new collection: {collection_name}")
        return self._collection

    def upsert_text_chunks(self, document_id, chunks_data, extra_metadata: dict[str, Any] | None = None):
        try:
            collection = self._get_collection()
            batch_size = 100
            total_upserted = 0

            for batch_start in range(0, len(chunks_data), batch_size):
                batch = chunks_data[batch_start : batch_start + batch_size]

                ids = []
                embeddings = []
                documents = []
                metadatas = []

                for chunk in batch:
                    chunk_id = f"{document_id}:{chunk['chunk_id']}"
                    ids.append(chunk_id)
                    embeddings.append(chunk["embedding"])
                    documents.append(chunk["text"])
                    meta = {
                        "document_id": str(document_id),
                        "chunk_id": chunk["chunk_id"],
                        "page_number": chunk.get("page", 0),
                        "page": chunk.get("page", 0),
                        "owner_user_id": chunk.get("owner_user_id", ""),
                        "user_id": chunk.get("owner_user_id", ""),
                        "scope": chunk.get("scope", ""),
                        "type": "text",
                        "workspace_id": "default",
                        "filename": chunk.get("filename", ""),
                        "file_type": chunk.get("file_type", ""),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "upload_timestamp": chunk.get("upload_timestamp", ""),
                        "section_title": chunk.get("section_title", ""),
                        "semantic_topic": chunk.get("semantic_topic", ""),
                    }
                    if extra_metadata:
                        meta.update(extra_metadata)
                    metadatas.append(meta)

                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                total_upserted += len(batch)

            logger.info(f"Upserted {total_upserted} text chunks for document {document_id}")
            return total_upserted
        except Exception as e:
            logger.error(f"Error upserting text chunks: {e}")
            raise

    def upsert_image_embeddings(self, document_id, images_data):
        try:
            collection = self._get_collection()
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for img in images_data:
                img_id = f"{document_id}:img:{img['image_id']}"
                ids.append(img_id)
                embeddings.append(img["embedding"])
                documents.append(f"Image from page {img.get('page', 0)}")
                metadatas.append({
                    "document_id": str(document_id),
                    "image_id": img["image_id"],
                    "page": img.get("page", 0),
                    "image_key": img["image_key"],
                    "owner_user_id": img["owner_user_id"],
                    "scope": img["scope"],
                    "type": "image",
                })

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Upserted {len(ids)} image embeddings for document {document_id}")
            return len(ids)
        except Exception as e:
            logger.error(f"Error upserting image embeddings: {e}")
            raise

    def search_text(self, query_embedding, document_id=None, top_k=5):
        try:
            collection = self._get_collection()
            if document_id:
                where_filter = {
                    "$and": [
                        {"type": "text"},
                        {"document_id": str(document_id)},
                    ]
                }
            else:
                where_filter = {"type": "text"}

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    chunks.append({
                        "chunk_id": metadata["chunk_id"],
                        "document_id": metadata["document_id"],
                        "text": results["documents"][0][i],
                        "page": metadata.get("page", 0),
                        "distance": results["distances"][0][i],
                        "scope": metadata.get("scope"),
                        "owner_user_id": metadata.get("owner_user_id"),
                    })

            logger.info(f"Found {len(chunks)} text chunks for query")
            return chunks
        except Exception as e:
            logger.error(f"Error searching text: {e}")
            raise

    def search_with_metadata_filter(
        self,
        query_embedding: list[float],
        metadata_filter: dict[str, Any],
        top_k: int = 10,
    ) -> list[dict]:
        try:
            collection = self._get_collection()

            if metadata_filter:
                if "$and" in metadata_filter:
                    inner = metadata_filter["$and"]
                    inner.insert(0, {"type": "text"})
                    where_filter = {"$and": inner}
                else:
                    where_filter = {"$and": [{"type": "text"}, metadata_filter]}
            else:
                where_filter = {"type": "text"}

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    chunks.append({
                        "chunk_id": metadata.get("chunk_id", ""),
                        "document_id": metadata.get("document_id", ""),
                        "text": results["documents"][0][i],
                        "page": metadata.get("page", metadata.get("page_number", 0)),
                        "distance": results["distances"][0][i],
                        "scope": metadata.get("scope"),
                        "owner_user_id": metadata.get("owner_user_id"),
                        "user_id": metadata.get("user_id"),
                        "filename": metadata.get("filename"),
                        "file_type": metadata.get("file_type"),
                        "section_title": metadata.get("section_title"),
                        "semantic_topic": metadata.get("semantic_topic"),
                    })

            logger.info(f"Found {len(chunks)} text chunks with metadata filter")
            return chunks
        except Exception as e:
            logger.error(f"Error searching with metadata filter: {e}")
            raise

    def search_images(self, query_embedding, document_id=None, top_m=3):
        try:
            collection = self._get_collection()
            if document_id:
                where_filter = {
                    "$and": [
                        {"type": "image"},
                        {"document_id": str(document_id)},
                    ]
                }
            else:
                where_filter = {"type": "image"}

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_m,
                where=where_filter,
                include=["metadatas", "distances"],
            )

            images = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    images.append({
                        "image_id": metadata["image_id"],
                        "document_id": metadata["document_id"],
                        "image_key": metadata["image_key"],
                        "page": metadata.get("page", 0),
                        "distance": results["distances"][0][i],
                    })

            logger.info(f"Found {len(images)} images for query")
            return images
        except Exception as e:
            logger.error(f"Error searching images: {e}")
            raise

    def delete_by_document(self, document_id):
        try:
            collection = self._get_collection()
            collection.delete(where={"document_id": str(document_id)})
            logger.info(f"Deleted all vectors for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vectors by document: {e}")
            raise

    def delete_by_user(self, user_id):
        try:
            collection = self._get_collection()
            collection.delete(where={"owner_user_id": str(user_id)})
            logger.info(f"Deleted all vectors for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vectors by user: {e}")
            raise

    def has_document_vectors(self, document_id):
        try:
            collection = self._get_collection()
            results = collection.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
                limit=1,
            )
            return bool(results.get("metadatas")) and len(results.get("metadatas", [])) > 0
        except Exception as e:
            logger.error(f"Error checking vectors for document {document_id}: {e}")
            raise

    def get_collection_stats(self):
        try:
            collection = self._get_collection()
            count = collection.count()
            return {
                "total_vectors": count,
                "collection_name": get_settings().chroma_collection,
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise


vector_service = VectorService()
