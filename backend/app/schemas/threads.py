from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    document_id: str
    title: str | None = None


class ThreadUpdate(BaseModel):
    title: str | None = None


class ThreadResponse(BaseModel):
    id: str
    document_id: str | None
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

    model_config = {"from_attributes": True}


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]
    total: int


class ThreadDetailResponse(BaseModel):
    id: str
    document_id: str | None
    title: str
    created_at: str
    updated_at: str
    messages: list["MessageResponse"]

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    text: str
    citations: list = []
    images: list = []
    created_at: str
    evaluation: dict | None = None

    model_config = {"from_attributes": True}
