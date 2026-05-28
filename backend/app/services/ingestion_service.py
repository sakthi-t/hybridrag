import csv
import io
import re
import fitz
from app.services.storage_service import storage_service
from app.services.chunking.semantic_splitter import semantic_splitter
from app.services.chunking.validators import chunk_validator


class IngestionService:
    def download_and_parse(self, document) -> list[dict]:
        file_bytes = storage_service.download_file(document.b2_object_key)
        return self.parse_document(file_bytes, document.file_type)

    def parse_document(self, file_bytes: bytes, file_type: str) -> list[dict]:
        if file_type == "pdf":
            return _parse_pdf(file_bytes)
        elif file_type == "csv":
            return _parse_csv(file_bytes)
        elif file_type == "txt":
            return _parse_txt(file_bytes)
        elif file_type == "md" or file_type == "markdown":
            return _parse_markdown(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def chunk(self, pages: list[dict]) -> list[dict]:
        raw_chunks = semantic_splitter.split(pages)
        valid_chunks, rejected = chunk_validator.filter_chunks(raw_chunks)
        return valid_chunks, rejected


def _parse_pdf(file_bytes: bytes) -> list[dict]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if text.strip():
            pages.append({"page": page_num + 1, "text": text})
    doc.close()
    return pages


def _parse_csv(file_bytes: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(file_bytes.decode("utf-8")))
    rows = list(reader)
    page_size = 50
    pages = []
    for i in range(0, len(rows), page_size):
        batch = rows[i:i + page_size]
        text_parts = []
        for row in batch:
            text_parts.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
        pages.append({
            "page": (i // page_size) + 1,
            "text": "\n".join(text_parts),
        })
    return pages


def _parse_txt(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8")
    page_size = 3000
    pages = []
    for i in range(0, len(text), page_size):
        chunk = text[i:i + page_size]
        if chunk.strip():
            pages.append({"page": (i // page_size) + 1, "text": chunk})
    return pages


def _parse_markdown(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8")
    sections = re.split(r"\n(?=# )", text)
    pages = []
    for i, section in enumerate(sections):
        if section.strip():
            pages.append({"page": i + 1, "text": section})
    return pages


ingestion_service = IngestionService()
