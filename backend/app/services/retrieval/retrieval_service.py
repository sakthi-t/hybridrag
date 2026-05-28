import logging
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings
from app.services.vector_service import vector_service
from app.services.retrieval.filter_builder import RetrievalScope, build_metadata_filter

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self._embeddings: OpenAIEmbeddings | None = None

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            settings = get_settings()
            self._embeddings = OpenAIEmbeddings(
                model=settings.openai_text_embedding_model,
                api_key=settings.openai_api_key,
            )
        return self._embeddings

    def embed_query(self, query: str) -> list[float]:
        return self.embeddings.embed_query(query)

    def search(
        self,
        query_embedding: list[float],
        scope: RetrievalScope,
        top_k: int | None = None,
    ) -> list[dict]:
        settings = get_settings()
        k = top_k or settings.top_k_chunks

        metadata_filter = build_metadata_filter(scope)

        results = vector_service.search_with_metadata_filter(
            query_embedding=query_embedding,
            metadata_filter=metadata_filter,
            top_k=k,
        )

        return results

    def search_by_document(
        self,
        query_embedding: list[float],
        document_id: str,
        top_k: int | None = None,
    ) -> list[dict]:
        scope = RetrievalScope(document_ids=[document_id])
        return self.search(query_embedding, scope, top_k)

    def search_by_user(
        self,
        query_embedding: list[float],
        user_id: str,
        workspace_id: str | None = None,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        scope = RetrievalScope(
            user_id=user_id,
            workspace_id=workspace_id,
            document_ids=[document_id] if document_id else [],
        )
        return self.search(query_embedding, scope, top_k)


retrieval_service = RetrievalService()
