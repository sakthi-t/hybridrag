"""
LLM-as-judge evaluation service for RAG responses.
"""
import json
import logging
import openai
from flask import current_app

logger = logging.getLogger(__name__)


class EvaluationService:
    """Evaluates faithfulness, citation precision, and groundedness."""

    def __init__(self):
        self._openai_client = None

    def _get_openai_client(self):
        if self._openai_client is None:
            openai.api_key = current_app.config.get('OPENAI_API_KEY')
            self._openai_client = openai
        return self._openai_client

    def _build_prompt(self, answer_text, context):
        text_chunks = context.get('text_chunks', [])
        citations = context.get('citations', [])

        excerpts = []
        for i, chunk in enumerate(text_chunks, 1):
            excerpts.append(f"[Excerpt {i} | Page {chunk.get('page', 0)} | Chunk {chunk.get('chunk_id', 'n/a')}]\n{chunk.get('text', '')}")

        prompt = (
            "You are a strict RAG evaluator. Score the assistant answer using ONLY the provided excerpts.\n"
            "Return JSON only with: faithfulness (0-1), citation_precision (0-1), groundedness (0-1), rationale.\n"
            "If the answer is off-topic or not supported by the excerpts, faithfulness and groundedness MUST be low (<=0.2).\n"
            "Definitions:\n"
            "- faithfulness: how well the answer is supported by excerpts.\n"
            "- citation_precision: how many citations actually support their claims.\n"
            "- groundedness: how much of the answer is grounded in excerpts vs. speculation.\n"
            "\n"
            f"EXCERPTS:\n{chr(10).join(excerpts)}\n\n"
            f"ANSWER:\n{answer_text}\n\n"
            f"CITATIONS (if any):\n{json.dumps(citations)}\n"
        )
        return prompt

    def evaluate(self, answer_text, context):
        try:
            client = self._get_openai_client()
            model = current_app.config.get('OPENAI_MODEL', 'gpt-4o')
            prompt = self._build_prompt(answer_text, context)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            faithfulness = float(data.get('faithfulness', 0.0))
            citation_precision = float(data.get('citation_precision', 0.0))
            groundedness = float(data.get('groundedness', 0.0))

            # Heuristic guards when citations/context are missing
            citations = context.get('citations', [])
            text_chunks = context.get('text_chunks', [])
            if not citations:
                # No citations extracted - set citation_precision to 0
                # but trust the LLM judge for faithfulness/groundedness
                citation_precision = 0.0
            if not text_chunks:
                # No context was provided - all scores should be 0
                faithfulness = 0.0
                groundedness = 0.0
                citation_precision = 0.0

            return {
                'faithfulness_score': faithfulness,
                'citation_precision_score': citation_precision,
                'groundedness_score': groundedness,
                'rationale': data.get('rationale', {})
            }
        except Exception as exc:
            logger.error(f"Evaluation failed: {exc}")
            return {
                'faithfulness_score': 0.0,
                'citation_precision_score': 0.0,
                'groundedness_score': 0.0,
                'rationale': {'error': str(exc)}
            }


evaluation_service = EvaluationService()
