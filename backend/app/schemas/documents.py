from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class UploadBatchRequest(BaseModel):
    files: list[FileMetadata] = Field(..., min_length=1, max_length=5)


class UploadBatchResponse(BaseModel):
    batch_id: str
    presigned_urls: list[dict]


class ConfirmFileEntry(BaseModel):
    object_key: str
    title: str


class ConfirmBatchRequest(BaseModel):
    batch_id: str
    files: list[ConfirmFileEntry] = Field(..., min_length=1, max_length=5)


class ConfirmBatchResponse(BaseModel):
    status: str
    batch_id: str


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    recommended_retrieval_type: str | None = None
    files: list[dict]


class ConfirmTypeRequest(BaseModel):
    retrieval_type: str = Field(..., pattern="^(vector|graph|hybrid)$")


class DocumentResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    file_type: str
    size_bytes: int
    scope: str
    retrieval_type: str
    created_at: str
    ingestion_status: str | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class IngestionStatusResponse(BaseModel):
    document_id: str
    status: str
    progress: int
    chunk_count: int | None = None
    chunks_rejected: int | None = None
    error: str | None = None
