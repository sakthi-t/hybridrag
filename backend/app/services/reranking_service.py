import logging
import cohere
from app.config import get_settings

logger = logging.getLogger(__name__)


class RerankingService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> cohere.ClientV2:
        if self._client is None:
            settings = get_settings()
            if not settings.cohere_api_key:
                logger.warning("COHERE_API_KEY not set — reranking will use original chunk order")
                self._client = None
                raise ValueError("COHERE_API_KEY not configured")
            self._client = cohere.ClientV2(api_key=settings.cohere_api_key)
            logger.info("Cohere reranking client initialized (rerank-english-v3.0)")
        return self._client

    def health_check(self) -> dict:
        settings = get_settings()
        if not settings.cohere_api_key:
            return {"status": "not_configured", "reason": "COHERE_API_KEY not set"}
        try:
            self.client.rerank(
                model="rerank-english-v3.0",
                query="test",
                documents=["test document"],
                top_n=1,
            )
            return {"status": "ok", "model": "rerank-english-v3.0"}
        except Exception as e:
            return {"status": "error", "reason": str(e)[:200]}

    def rerank(self, query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
        if len(chunks) <= top_n:
            return chunks

        documents = [chunk["text"] for chunk in chunks]

        try:
            response = self.client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_n,
            )

            reranked = []
            for result in response.results:
                chunk = chunks[result.index]
                reranked.append({**chunk, "_rerank_score": result.relevance_score})

            logger.info(f"Cohere reranked {len(documents)} chunks, kept top {len(reranked)}")
            return reranked

        except Exception as e:
            logger.error(f"Cohere rerank failed, falling back to original order: {e}")
            return chunks[:top_n]


reranking_service = RerankingService()
