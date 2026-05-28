import re
import logging
from dataclasses import dataclass, field
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextSegment:
    text: str
    start_idx: int
    embedding: list[float] | None = None


@dataclass
class SemanticChunk:
    text: str
    page: int
    chunk_index: int
    section_title: str | None = None
    semantic_topic: str | None = None


class SemanticSplitter:
    def __init__(self):
        settings = get_settings()
        self.max_chunk_size = settings.max_chunk_size
        self.min_chunk_length = settings.min_semantic_chunk_length
        self.chunk_overlap = settings.chunk_overlap
        self.similarity_threshold = settings.semantic_similarity_threshold
        self.enabled = settings.semantic_chunking_enabled
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

    def split(self, pages: list[dict]) -> list[dict]:
        if not self.enabled:
            return self._structural_split(pages)
        return self._semantic_split(pages)

    def _structural_split(self, pages: list[dict]) -> list[dict]:
        chunks: list[dict] = []
        global_idx = 0

        for page in pages:
            page_text = page["text"]
            page_num = page["page"]
            paragraphs = _split_paragraphs(page_text)
            sections = _detect_sections(page_text)

            current_chunk = ""
            current_section = sections[0][0] if sections else None

            for para in paragraphs:
                section_for_para = _find_section_for_paragraph(para, sections, page_text)
                section_changed = section_for_para and section_for_para != current_section

                would_exceed = len(current_chunk) + len(para) + 1 > self.max_chunk_size

                if (section_changed and current_chunk and len(current_chunk) >= self.min_chunk_length) or would_exceed:
                    if current_chunk.strip():
                        chunks.append({
                            "text": current_chunk.strip(),
                            "page": page_num,
                            "chunk_index": global_idx,
                            "section_title": current_section,
                        })
                        global_idx += 1
                    current_chunk = para
                    current_section = section_for_para
                else:
                    current_chunk += (" " if current_chunk else "") + para
                    if section_for_para:
                        current_section = section_for_para

            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "page": page_num,
                    "chunk_index": global_idx,
                    "section_title": current_section,
                })
                global_idx += 1

        return chunks

    def _semantic_split(self, pages: list[dict]) -> list[dict]:
        all_segments: list[tuple[TextSegment, int]] = []
        for page in pages:
            paragraphs = _split_paragraphs(page["text"])
            for para in paragraphs:
                if len(para.strip()) < 15:
                    continue
                all_segments.append((TextSegment(text=para, start_idx=len(all_segments)), page["page"]))

        if len(all_segments) < 2:
            return self._structural_split(pages)

        embeddings = self._embed_segments(all_segments)
        similarities = self._compute_similarities(embeddings)

        return self._assemble_semantic_chunks(all_segments, similarities)

    def _embed_segments(self, segments: list[tuple[TextSegment, int]]) -> list[list[float]]:
        texts = [seg[0].text for seg in segments]
        return self.embeddings.embed_documents(texts)

    def _compute_similarities(self, embeddings: list[list[float]]) -> list[float]:
        similarities: list[float] = []
        for i in range(1, len(embeddings)):
            sim = _cosine_similarity(embeddings[i - 1], embeddings[i])
            similarities.append(sim)
        return similarities

    def _assemble_semantic_chunks(
        self,
        segments: list[tuple[TextSegment, int]],
        similarities: list[float],
    ) -> list[dict]:
        chunks: list[dict] = []
        current_group: list[tuple[str, int]] = []
        current_page: int | None = None
        global_idx = 0

        for i, (seg, page) in enumerate(segments):
            if i > 0 and similarities[i - 1] < self.similarity_threshold:
                group_chunks = self._finalize_group(current_group, current_page, global_idx)
                for gc in group_chunks:
                    gc["chunk_index"] = global_idx
                    chunks.append(gc)
                    global_idx += 1
                current_group = []
                current_page = None

            current_group.append((seg.text, page))
            current_page = page

        group_chunks = self._finalize_group(current_group, current_page, global_idx)
        for gc in group_chunks:
            gc["chunk_index"] = global_idx
            chunks.append(gc)
            global_idx += 1

        return chunks

    def _finalize_group(
        self, group: list[tuple[str, int]], page: int | None, idx: int
    ) -> list[dict]:
        if not group:
            return []
        pages_in_group = set(p for _, p in group)
        primary_page = page or (max(pages_in_group) if pages_in_group else 0)

        chunk_texts = _split_into_chunks(
            [t for t, _ in group], self.max_chunk_size, self.chunk_overlap
        )

        results = []
        for ci, chunk_text in enumerate(chunk_texts):
            if len(chunk_text) < self.min_chunk_length:
                continue
            results.append({
                "text": chunk_text,
                "page": primary_page,
                "chunk_index": idx,
                "section_title": None,
            })
        return results


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n{2,}|\r\n{2,}", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _detect_sections(text: str) -> list[tuple[str, int]]:
    headings = re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
    return [(m.group(2).strip(), m.start()) for m in headings]


def _find_section_for_paragraph(
    para: str, sections: list[tuple[str, int]], full_text: str
) -> str | None:
    if not sections:
        return None
    try:
        para_start = full_text.index(para)
    except ValueError:
        return None
    title = sections[0][0]
    for section_title, section_start in sections:
        if section_start <= para_start:
            title = section_title
        else:
            break
    return title


def _split_into_chunks(parts: list[str], max_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = (current + " " + part).strip() if current else part

        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
                overlap_text = ""
                if len(current) > overlap:
                    tail = current[-overlap:]
                    sentence_break = re.search(r"[.!?]\s+", tail)
                    if sentence_break:
                        overlap_text = tail[sentence_break.end():]
                    else:
                        overlap_text = tail
                current = (overlap_text + " " + part).strip() if overlap_text else part
            else:
                current = part

    if current and len(current) >= 10:
        chunks.append(current)

    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


semantic_splitter = SemanticSplitter()
