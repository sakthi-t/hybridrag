import json
import re
import logging
from datetime import datetime, timezone
from uuid import uuid4
from langchain_openai import ChatOpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse JSON from eval response: {raw[:200]}")
        return {}


class EvaluationService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> ChatOpenAI:
        if self._client is None:
            settings = get_settings()
            self._client = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0,
                max_tokens=300,
            )
        return self._client

    def evaluate(
        self,
        query: str,
        response: str,
        context_chunks: list[dict] | None = None,
    ) -> dict:
        context_text = self._format_context(context_chunks) if context_chunks else ""
        has_context = bool(context_chunks)

        relevance_prompt = (
            f"Score how well the RESPONSE answers the QUERY below. Be strict but fair.\n\n"
            f"QUERY: {query}\n\n"
            f"RESPONSE: {response}\n\n"
            "Scoring guidelines (use any integer from 0 to 100):\n"
            "- 100: Fully and accurately answers with specific, relevant details. Nothing important missing.\n"
            "- 90: Answers correctly but one minor detail missing or imprecise.\n"
            "- 80: Mostly correct but 1-2 points unclear or slightly off-topic.\n"
            "- 75: Partially correct — addresses the topic but misses key parts of what was asked.\n"
            "- 60: Touches the topic but answer is vague, generic, or misses the core question.\n"
            "- 40: Barely relevant — mentions related concepts but doesn't answer what was asked.\n"
            "- 0: Completely irrelevant, wrong topic, or says it cannot answer / lacks information.\n\n"
            'Return exactly JSON: {"relevance": <int>, "reasoning": "<one sentence>"}'
        )

        if has_context:
            accuracy_prompt = (
                "Verify the RESPONSE against the RETRIEVED CONTEXT below.\n\n"
                f"QUERY: {query}\n\n"
                f"RETRIEVED CONTEXT:\n{context_text}\n\n"
                f"RESPONSE: {response}\n\n"
                "Score THREE dimensions (each an integer 0-100):\n\n"
                "1. citation: How much of the response is verifiable from the context?\n"
                "   - 100: Every factual claim cites or clearly draws from context.\n"
                "   - 75: Most claims supported, minor detail missing from context.\n"
                "   - 0: Response is unsupported or hallucinated.\n\n"
                "2. faithfulness: Does the response stay true to what the context actually says?\n"
                "   - 100: No distortion, no cherry-picking, faithfully represents context.\n"
                "   - 75: Minor distortion or omission, but generally accurate.\n"
                "   - 0: Distorts the context or fabricates claims.\n\n"
                "3. groundedness: Are the claims grounded in specific context passages?\n"
                "   - 100: Every claim tied to a specific piece of context.\n"
                "   - 75: Most claims grounded, some vague or unsupported.\n"
                "   - 0: No grounding, purely speculative.\n\n"
                'Return exactly JSON: {"citation": <int>, "faithfulness": <int>, "groundedness": <int>, "reasoning": "<one sentence>"}'
            )

            try:
                result = self.client.invoke([
                    {"role": "system", "content": "You are an expert evaluator. Return JSON only."},
                    {"role": "user", "content": accuracy_prompt},
                ])
                data = _parse_json(result.content)
                accuracy = {
                    "citation": max(0, min(100, int(data.get("citation", 0)))),
                    "faithfulness": max(0, min(100, int(data.get("faithfulness", 0)))),
                    "groundedness": max(0, min(100, int(data.get("groundedness", 0)))),
                }
            except Exception as e:
                logger.error(f"Accuracy evaluation error: {e}")
                accuracy = {"citation": 0, "faithfulness": 0, "groundedness": 0}
        else:
            accuracy = {"citation": 0, "faithfulness": 0, "groundedness": 0}

        try:
            result = self.client.invoke([
                {"role": "system", "content": "You are an expert evaluator. Return JSON only."},
                {"role": "user", "content": relevance_prompt},
            ])
            data = _parse_json(result.content)
            relevance = max(0, min(100, int(data.get("relevance", 0))))
            relevance_reasoning = data.get("reasoning", "")
        except Exception as e:
            logger.error(f"Relevance evaluation error: {e}")
            relevance = 0
            relevance_reasoning = str(e)

        reasoning_parts = []
        if accuracy.get("citation", 0) is not None:
            reasoning_parts.append(
                f"citation={accuracy['citation']}, faithfulness={accuracy['faithfulness']}, "
                f"groundedness={accuracy['groundedness']}"
            )
        reasoning_parts.append(f"relevance={relevance}: {relevance_reasoning}")

        return {
            "citation": accuracy.get("citation", 0),
            "faithfulness": accuracy.get("faithfulness", 0),
            "groundedness": accuracy.get("groundedness", 0),
            "relevance": relevance,
            "reasoning": "; ".join(reasoning_parts),
        }

    def _format_context(self, chunks: list[dict]) -> str:
        parts = []
        for i, c in enumerate(chunks):
            page = c.get("page", "?")
            text = c.get("text", "")
            parts.append(f"[Source {i + 1} — Page {page}]\n{text}")
        return "\n\n---\n\n".join(parts)

    def save_evaluation(
        self,
        message_id: str,
        scores: dict,
        db_session,
        latency_ms: int = None,
        retrieval_type: str = "vector",
    ):
        from app.models.message_evaluation import MessageEvaluation
        from sqlalchemy import text

        existing = db_session.execute(
            text("SELECT id FROM message_evaluations WHERE message_id = :mid"),
            {"mid": message_id},
        ).fetchone()

        if existing:
            db_session.execute(
                text(
                    """
                    UPDATE message_evaluations
                    SET faithfulness_score = :f, citation_precision_score = :c,
                        groundedness_score = :g, rationale_json = :r,
                        latency_ms = :l, retrieval_type = :rt
                    WHERE message_id = :mid
                """
                ),
                {
                    "f": scores["faithfulness"],
                    "c": scores["citation"],
                    "g": scores["groundedness"],
                    "r": json.dumps({
                        "relevance": scores["relevance"],
                        "reasoning": scores.get("reasoning", ""),
                    }),
                    "l": latency_ms,
                    "rt": retrieval_type,
                    "mid": message_id,
                },
            )
        else:
            eval_record = MessageEvaluation(
                id=uuid4(),
                message_id=message_id,
                faithfulness_score=scores["faithfulness"],
                citation_precision_score=scores["citation"],
                groundedness_score=scores["groundedness"],
                rationale_json={
                    "relevance": scores["relevance"],
                    "reasoning": scores.get("reasoning", ""),
                },
                latency_ms=latency_ms,
                retrieval_type=retrieval_type,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(eval_record)
        db_session.commit()


evaluation_service = EvaluationService()
