import logging
from dataclasses import dataclass
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import get_settings

logger = logging.getLogger(__name__)

HYDE_SYSTEM_PROMPT = """You are a helpful assistant. Given a user question, write a short passage that would 
be the ideal answer to the question. Write in the style of a formal document or textbook.
The passage should be 3-5 sentences long. Do not include phrases like "the document states" 
or "according to the text." Just produce the answer passage directly."""


@dataclass
class HyDEResult:
    original_query: str
    hypothetical_answer: str
    retrieval_embedding: list[float]
    used_hyde: bool


class HyDEService:
    def __init__(self):
        self._llm: ChatOpenAI | None = None
        self._embeddings: OpenAIEmbeddings | None = None

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            settings = get_settings()
            self._llm = ChatOpenAI(
                model=settings.hyde_model,
                api_key=settings.openai_api_key,
                temperature=settings.hyde_temperature,
                max_tokens=settings.hyde_max_tokens,
            )
        return self._llm

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            settings = get_settings()
            self._embeddings = OpenAIEmbeddings(
                model=settings.openai_text_embedding_model,
                api_key=settings.openai_api_key,
            )
        return self._embeddings

    def generate_hypothetical_answer(self, query: str) -> str:
        response = self.llm.invoke([
            {"role": "system", "content": HYDE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ])
        return response.content or ""

    def embed_text(self, text: str) -> list[float]:
        return self.embeddings.embed_query(text)

    def process_query(self, query: str) -> HyDEResult:
        settings = get_settings()

        if not settings.hyde_enabled or not query.strip():
            embedding = self.embed_text(query)
            return HyDEResult(
                original_query=query,
                hypothetical_answer="",
                retrieval_embedding=embedding,
                used_hyde=False,
            )

        try:
            hypothetical = self.generate_hypothetical_answer(query)
            if not hypothetical.strip():
                embedding = self.embed_text(query)
                return HyDEResult(
                    original_query=query,
                    hypothetical_answer="",
                    retrieval_embedding=embedding,
                    used_hyde=False,
                )

            embedding = self.embed_text(hypothetical)
            logger.info(f"HyDE generated hypothetical answer for query: {query[:80]}...")
            return HyDEResult(
                original_query=query,
                hypothetical_answer=hypothetical,
                retrieval_embedding=embedding,
                used_hyde=True,
            )
        except Exception as e:
            logger.warning(f"HyDE generation failed, falling back to raw query: {e}")
            embedding = self.embed_text(query)
            return HyDEResult(
                original_query=query,
                hypothetical_answer="",
                retrieval_embedding=embedding,
                used_hyde=False,
            )


hyde_service = HyDEService()
