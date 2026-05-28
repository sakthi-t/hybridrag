from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    stream: bool = False


class ChatResponse(BaseModel):
    message: str
    message_id: str
    context: dict
    metrics: dict
