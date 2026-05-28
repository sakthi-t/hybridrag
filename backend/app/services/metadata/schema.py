import dataclasses
from datetime import datetime, timezone
from typing import Any


@dataclasses.dataclass
class ChunkMetadata:
    document_id: str
    user_id: str
    workspace_id: str
    chunk_id: str
    filename: str
    file_type: str
    page_number: int
    chunk_index: int
    upload_timestamp: str = ""
    section_title: str = ""
    semantic_topic: str = ""

    def __post_init__(self):
        if not self.upload_timestamp:
            self.upload_timestamp = datetime.now(timezone.utc).isoformat()

    def to_chroma_dict(self) -> dict[str, str | int | float | bool]:
        return {
            "document_id": self.document_id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "chunk_id": self.chunk_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "upload_timestamp": self.upload_timestamp,
            "section_title": self.section_title,
            "semantic_topic": self.semantic_topic,
        }

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChunkMetadata":
        field_names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})
