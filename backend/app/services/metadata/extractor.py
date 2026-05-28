import re
import logging
from datetime import datetime, timezone
from app.models.document import Document
from .schema import ChunkMetadata

logger = logging.getLogger(__name__)


class MetadataExtractor:
    def build_chunk_metadata(
        self,
        chunk: dict,
        document: Document,
        global_index: int,
    ) -> ChunkMetadata:
        section_title = self._extract_section_title(chunk.get("text", ""))
        semantic_topic = self._infer_topic(chunk.get("text", ""))

        return ChunkMetadata(
            document_id=str(document.id),
            user_id=str(document.owner_user_id),
            workspace_id="default",
            chunk_id=f"chunk_{global_index}",
            filename=document.original_filename or "untitled",
            file_type=document.file_type,
            page_number=chunk.get("page", 0),
            chunk_index=global_index,
            section_title=chunk.get("section_title") or section_title,
            semantic_topic=semantic_topic,
        )

    def _extract_section_title(self, text: str) -> str:
        match = re.search(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
        if match:
            return match.group(2).strip()
        lines = text.strip().split("\n")
        first_line = lines[0].strip()
        if len(first_line) < 120 and not first_line.endswith("."):
            return first_line
        return ""

    def _infer_topic(self, text: str) -> str:
        keywords = {
            "introduction": ["introduction", "overview", "background", "purpose"],
            "methodology": ["method", "methodology", "approach", "procedure", "algorithm"],
            "results": ["result", "finding", "output", "outcome", "performance"],
            "discussion": ["discussion", "analysis", "interpretation", "implication"],
            "conclusion": ["conclusion", "summary", "future work", "recommendation"],
            "configuration": ["config", "setting", "parameter", "environment", "setup"],
            "data": ["data", "dataset", "table", "figure", "chart", "statistic"],
        }
        text_lower = text[:500].lower()
        scores: dict[str, int] = {}
        for topic, terms in keywords.items():
            score = sum(1 for t in terms if t in text_lower)
            if score > 0:
                scores[topic] = score
        if scores:
            return max(scores, key=scores.get)
        return "general"


metadata_extractor = MetadataExtractor()
