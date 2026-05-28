import json
import time
import logging
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.services.vector_service import vector_service
from app.services.reranking_service import reranking_service
from app.services.hyde.hyde_service import hyde_service
from app.services.retrieval.retrieval_service import retrieval_service
from app.services.retrieval.filter_builder import RetrievalScope

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert document assistant. Answer questions using the retrieved context.
Always cite sources by referencing page numbers when available.
If the context does not contain enough information to answer, say so clearly.
Be concise, accurate, and helpful."""


class RAGService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> ChatOpenAI:
        if self._client is None:
            settings = get_settings()
            self._client = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=settings.rag_temperature,
                max_tokens=settings.max_completion_tokens,
            )
        return self._client

    def embed_query(self, query: str) -> list[float]:
        return retrieval_service.embed_query(query)

    def retrieve(
        self,
        query: str,
        document_id: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> dict:
        settings = get_settings()

        hyde_result = hyde_service.process_query(query)

        scope = RetrievalScope(
            user_id=user_id,
            workspace_id=workspace_id,
            document_ids=[document_id],
        )

        raw_chunks = retrieval_service.search(
            query_embedding=hyde_result.retrieval_embedding,
            scope=scope,
            top_k=settings.top_k_chunks,
        )

        if not raw_chunks:
            return {"chunks": [], "hyde_used": hyde_result.used_hyde}

        reranked = reranking_service.rerank(
            query=query,
            chunks=raw_chunks,
            top_n=settings.rerank_top_n,
        )

        return {
            "chunks": reranked,
            "hyde_used": hyde_result.used_hyde,
        }

    def _format_chunks(self, chunks: list[dict]) -> str:
        parts = []
        for i, c in enumerate(chunks):
            page = c.get("page", "?")
            parts.append(f"[Chunk {i + 1} — Page {page}]\n{c['text']}")
        return "\n\n---\n\n".join(parts)

    def chat(
        self,
        query: str,
        document_id: str,
        message_history: list[dict] | None = None,
        user_id: str | None = None,
    ) -> dict:
        start = time.time()

        result = self.retrieve(query, document_id, user_id=user_id)
        chunks = result["chunks"]
        context_text = self._format_chunks(chunks)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if message_history:
            messages.extend(message_history)

        messages.append({
            "role": "user",
            "content": f"{context_text}\n\n=== USER QUESTION ===\n{query}",
        })

        response = self.client.invoke(messages)

        latency_ms = int((time.time() - start) * 1000)

        citations = [
            {"page": c.get("page"), "text": c["text"][:100]}
            for c in chunks
        ]

        return {
            "message": response.content,
            "context": {"chunks": citations},
            "metrics": {
                "latency_ms": latency_ms,
                "chunks_retrieved": len(chunks),
                "hyde_used": result["hyde_used"],
            },
        }

    def chat_stream(
        self,
        query: str,
        document_id: str,
        message_history: list[dict] | None = None,
        user_id: str | None = None,
    ):
        start = time.time()

        result = self.retrieve(query, document_id, user_id=user_id)
        chunks = result["chunks"]
        context_text = self._format_chunks(chunks)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if message_history:
            messages.extend(message_history)

        messages.append({
            "role": "user",
            "content": f"{context_text}\n\n=== USER QUESTION ===\n{query}",
        })

        stream = self.client.stream(messages)

        return stream, chunks, start, result["hyde_used"]


rag_service = RAGService()
