import re
from app.config import get_settings


class ChunkingService:
    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.min_chunk_length = settings.min_chunk_length

    def chunk_document(self, pages: list[dict]) -> list[dict]:
        raw_chunks = []
        for page in pages:
            text = self._preprocess(page["text"])
            paragraphs = self._split_paragraphs(text)
            chunks = self._assemble_chunks(paragraphs, page["page"])
            raw_chunks.extend(chunks)
        valid_chunks = [c for c in raw_chunks if self._is_valid_chunk(c)]
        return valid_chunks

    def _preprocess(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^\d{1,3}$", stripped):
                continue
            if len(stripped) < 3 and not stripped.isalpha():
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _split_paragraphs(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n{2,}|\r\n{2,}", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _assemble_chunks(self, paragraphs: list[str], page: int) -> list[dict]:
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 1 <= self.chunk_size:
                current_chunk += (" " if current_chunk else "") + paragraph
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk,
                        "page": page,
                        "chunk_index": chunk_index,
                    })
                    chunk_index += 1
                    overlap = current_chunk[-self.chunk_overlap:]
                    sentence_break = re.search(r"[.!?]\s+", overlap)
                    if sentence_break:
                        overlap = overlap[sentence_break.end():]
                    current_chunk = overlap + " " + paragraph
                else:
                    current_chunk = paragraph

        if current_chunk:
            chunks.append({
                "text": current_chunk,
                "page": page,
                "chunk_index": chunk_index,
            })

        return chunks

    def _is_valid_chunk(self, chunk: dict) -> bool:
        text = chunk["text"].strip()
        if len(text) < self.min_chunk_length:
            return False
        alpha_chars = len(re.findall(r"[a-zA-Z]", text))
        if alpha_chars < len(text) * 0.3:
            return False
        words = text.split()
        if len(words) < 5:
            return False
        return True


chunking_service = ChunkingService()
